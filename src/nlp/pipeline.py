# pipeline.py - Pipeline completo: Texto → Red IANAE
# Scope: src/nlp/ (Worker-NLP)
# Importa ConceptosLucas de nucleo.py (NO lo modifica)

import numpy as np
from typing import List, Dict, Optional, Tuple

from src.nlp.extractor import ExtractorConceptos


class ReduccionDimensional:
    """
    Reduce embeddings de alta dimensión (384/768) a dim_target (15 por defecto).

    Método: PCA incremental con fallback a proyección aleatoria estable.
    """

    def __init__(self, dim_target: int = 15):
        self.dim_target = dim_target
        self._matriz_proyeccion = None
        self._media = None
        self._componentes = None

    def ajustar(self, embeddings: np.ndarray):
        """
        Ajusta la reducción con un conjunto de embeddings.

        Args:
            embeddings: matriz (n_samples, dim_original)
        """
        n_samples, dim_original = embeddings.shape

        if dim_original <= self.dim_target:
            # No necesita reducción, solo padding
            self._matriz_proyeccion = None
            return

        self._media = np.mean(embeddings, axis=0)
        centrado = embeddings - self._media

        if n_samples >= self.dim_target:
            # PCA real
            cov = np.cov(centrado, rowvar=False)
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            # Tomar los dim_target componentes con mayor varianza
            indices = np.argsort(eigenvalues)[::-1][:self.dim_target]
            self._componentes = eigenvectors[:, indices].T
        else:
            # Pocos datos: proyección aleatoria estable (Johnson-Lindenstrauss)
            rng = np.random.RandomState(42)
            self._componentes = rng.normal(0, 1 / np.sqrt(self.dim_target),
                                           (self.dim_target, dim_original))

    def transformar(self, embedding: np.ndarray) -> np.ndarray:
        """
        Reduce un embedding a dim_target dimensiones.

        Args:
            embedding: vector de dim_original

        Returns:
            Vector de dim_target, normalizado
        """
        if len(embedding) == self.dim_target:
            return embedding / (np.linalg.norm(embedding) + 1e-10)

        if len(embedding) < self.dim_target:
            # Padding con ceros
            padded = np.zeros(self.dim_target)
            padded[:len(embedding)] = embedding
            return padded / (np.linalg.norm(padded) + 1e-10)

        if self._componentes is not None:
            centrado = embedding - self._media if self._media is not None else embedding
            reducido = self._componentes @ centrado
        else:
            # Fallback: tomar primeros dim_target componentes
            reducido = embedding[:self.dim_target]

        # Normalizar (ConceptosLucas normaliza internamente, pero es buena práctica)
        norma = np.linalg.norm(reducido)
        if norma > 0:
            reducido = reducido / norma

        return reducido

    def ajustar_y_transformar(self, embeddings: np.ndarray) -> np.ndarray:
        """Ajusta y transforma un batch de embeddings."""
        self.ajustar(embeddings)
        return np.array([self.transformar(e) for e in embeddings])


class PipelineNLP:
    """
    Pipeline completo: Texto → Tokenización → Extracción → Embeddings → Red IANAE

    Uso:
        from core.nucleo import ConceptosLucas
        sistema = ConceptosLucas()
        pipeline = PipelineNLP(sistema)
        resultado = pipeline.procesar("Python es un lenguaje versátil para IA")
    """

    def __init__(self, sistema_ianae=None, dim_vector: int = 15, modo_nlp: str = "auto"):
        """
        Args:
            sistema_ianae: instancia de ConceptosLucas (o None para crear nueva)
            dim_vector: dimensión de vectores del sistema IANAE
            modo_nlp: modo del extractor ("auto", "spacy", "transformers", "basico")
        """
        self.dim_vector = dim_vector
        self.extractor = ExtractorConceptos(modo=modo_nlp)
        self.reductor = ReduccionDimensional(dim_target=dim_vector)
        self.sistema = sistema_ianae
        self._embeddings_cache = {}

    def procesar(self, texto: str, max_conceptos: int = 10,
                 categoria: str = "nlp_extraidos",
                 umbral_relacion: float = 0.2) -> Dict:
        """
        Pipeline completo: texto → conceptos en red IANAE.

        Args:
            texto: texto en español a procesar
            max_conceptos: máximo de conceptos a extraer
            categoria: categoría para los conceptos en el sistema IANAE
            umbral_relacion: peso mínimo para crear relación

        Returns:
            Dict con: conceptos, relaciones, embeddings_originales, vectores_reducidos
        """
        # Paso 1: Extracción de conceptos
        conceptos = self.extractor.extraer_conceptos(texto, max_conceptos)
        if not conceptos:
            return {"conceptos": [], "relaciones": [], "error": "No se extrajeron conceptos"}

        # Paso 2: Generar embeddings (con cache)
        embeddings_originales = {}
        for concepto in conceptos:
            nombre = concepto["nombre"]
            if nombre in self._embeddings_cache:
                embedding = self._embeddings_cache[nombre]
            else:
                embedding = self.extractor.generar_embedding(nombre)
                self._embeddings_cache[nombre] = embedding
            embeddings_originales[nombre] = embedding

        # Paso 3: Reducción dimensional (384/768 → 15)
        nombres = list(embeddings_originales.keys())
        matriz_embeddings = np.array([embeddings_originales[n] for n in nombres])

        if matriz_embeddings.shape[1] != self.dim_vector:
            vectores_reducidos_matriz = self.reductor.ajustar_y_transformar(matriz_embeddings)
        else:
            vectores_reducidos_matriz = matriz_embeddings

        vectores_reducidos = {}
        for i, nombre in enumerate(nombres):
            vectores_reducidos[nombre] = vectores_reducidos_matriz[i]

        # Paso 4: Extraer relaciones
        relaciones = self.extractor.extraer_relaciones(texto, conceptos)
        relaciones_filtradas = [(c1, c2, p) for c1, c2, p in relaciones if p >= umbral_relacion]

        # Paso 5: Inyectar en sistema IANAE (si está disponible)
        if self.sistema is not None:
            self._inyectar_en_sistema(conceptos, vectores_reducidos, relaciones_filtradas, categoria)

        return {
            "conceptos": conceptos,
            "relaciones": relaciones_filtradas,
            "embeddings_originales": {k: v.tolist() for k, v in embeddings_originales.items()},
            "vectores_reducidos": {k: v.tolist() for k, v in vectores_reducidos.items()},
            "modo": self.extractor.modo,
            "dim_original": matriz_embeddings.shape[1],
            "dim_reducida": self.dim_vector
        }

    def _inyectar_en_sistema(self, conceptos: List[Dict], vectores: Dict[str, np.ndarray],
                              relaciones: List[Tuple], categoria: str):
        """Inyecta conceptos y relaciones en ConceptosLucas."""
        # Registrar nueva categoría si no existe
        if hasattr(self.sistema, "categorias") and categoria not in self.sistema.categorias:
            self.sistema.categorias[categoria] = []

        # Añadir conceptos
        for concepto in conceptos:
            nombre = concepto["nombre"]
            if nombre in vectores:
                vector = vectores[nombre]
                # Escalar relevancia como incertidumbre inversa
                incertidumbre = max(0.05, 0.3 * (1 - concepto["relevancia"]))
                self.sistema.añadir_concepto(
                    nombre,
                    atributos=vector,
                    incertidumbre=incertidumbre,
                    categoria=categoria
                )

        # Añadir relaciones
        for c1, c2, peso in relaciones:
            if c1 in self.sistema.conceptos and c2 in self.sistema.conceptos:
                self.sistema.relacionar(c1, c2, fuerza=peso)

    def procesar_batch(self, textos: List[str], **kwargs) -> List[Dict]:
        """Procesa múltiples textos."""
        return [self.procesar(texto, **kwargs) for texto in textos]


# --- Función de demostración ---

def demo():
    """Demostración del pipeline NLP → IANAE."""
    print("=" * 60)
    print("  DEMO: Pipeline NLP → Red IANAE")
    print("=" * 60)

    # Importar ConceptosLucas
    try:
        from core.nucleo import ConceptosLucas, crear_universo_lucas
        sistema = crear_universo_lucas()
        print(f"\n[OK] Sistema IANAE cargado: {len(sistema.conceptos)} conceptos existentes")
    except ImportError:
        print("\n[WARN] No se pudo importar nucleo.py, usando sistema vacío")
        sistema = None

    # Crear pipeline
    pipeline = PipelineNLP(sistema_ianae=sistema)
    print(f"[OK] Pipeline modo: {pipeline.extractor.modo}")

    # Texto de ejemplo
    texto_ejemplo = """
    Lucas está desarrollando un sistema de inteligencia artificial llamado IANAE
    que usa conceptos difusos y pensamiento emergente. El proyecto utiliza Python
    con numpy para los vectores multidimensionales y networkx para el grafo de
    relaciones. La detección de patrones en imágenes de tacógrafos usa OpenCV
    con redes neuronales convolucionales. El sistema de memoria RAG conecta
    con LM Studio para generar respuestas contextuales.
    """

    print(f"\n{'─' * 60}")
    print("TEXTO DE ENTRADA:")
    print(texto_ejemplo.strip())
    print(f"{'─' * 60}")

    # Procesar
    resultado = pipeline.procesar(texto_ejemplo, max_conceptos=8)

    # Mostrar resultados
    print(f"\n📦 CONCEPTOS EXTRAÍDOS ({len(resultado['conceptos'])}):")
    for c in resultado["conceptos"]:
        print(f"  • {c['nombre']:25s}  relevancia={c['relevancia']:.3f}  tipo={c['tipo']}")

    print(f"\n🔗 RELACIONES DETECTADAS ({len(resultado['relaciones'])}):")
    for c1, c2, peso in resultado["relaciones"][:10]:
        print(f"  • {c1} ↔ {c2}  peso={peso:.3f}")

    print(f"\n📐 DIMENSIONES: {resultado['dim_original']} → {resultado['dim_reducida']}")
    print(f"🔧 MODO: {resultado['modo']}")

    # Si hay sistema IANAE, mostrar estado actualizado
    if sistema:
        print(f"\n📊 SISTEMA IANAE ACTUALIZADO:")
        print(f"   Conceptos totales: {len(sistema.conceptos)}")
        print(f"   Aristas totales: {sistema.grafo.number_of_edges()}")

        # Probar activación de un concepto NLP
        conceptos_nlp = [c["nombre"] for c in resultado["conceptos"]]
        if conceptos_nlp:
            print(f"\n🔥 Activando concepto NLP: '{conceptos_nlp[0]}'")
            activacion = sistema.activar(conceptos_nlp[0], pasos=2, temperatura=0.15)
            if activacion:
                activos = [(c, a) for c, a in activacion[-1].items() if a > 0.05]
                activos.sort(key=lambda x: x[1], reverse=True)
                print("   Top conceptos activados:")
                for c, a in activos[:5]:
                    cat = sistema.conceptos[c]["categoria"]
                    print(f"     {c:25s} → {a:.3f}  [{cat}]")

    print(f"\n{'=' * 60}")
    print("  DEMO COMPLETADA")
    print(f"{'=' * 60}")

    return resultado


if __name__ == "__main__":
    demo()
