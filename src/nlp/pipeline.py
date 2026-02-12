# pipeline.py - Pipeline completo: Texto → Red IANAE
# Scope: src/nlp/ (Worker-NLP)
# Importa ConceptosLucas de nucleo.py (NO lo modifica)

import hashlib
import json
import os
import numpy as np
from typing import List, Dict, Optional, Tuple

from src.nlp.extractor import ExtractorConceptos


class EmbeddingCacheDisco:
    """
    Cache de embeddings persistido en disco (JSON lines).

    Cada entrada: {"key": sha256(texto+modelo), "embedding": [...], "texto": "..."}
    """

    def __init__(self, ruta: Optional[str] = None, modelo_id: str = "default"):
        self.modelo_id = modelo_id
        self._cache = {}
        if ruta is None:
            ruta = os.path.join(os.path.dirname(__file__), ".embedding_cache.jsonl")
        self.ruta = ruta
        self._cargar()

    def _hash_key(self, texto: str) -> str:
        raw = f"{self.modelo_id}:{texto}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _cargar(self):
        if not os.path.exists(self.ruta):
            return
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if not linea:
                        continue
                    entry = json.loads(linea)
                    self._cache[entry["key"]] = np.array(entry["embedding"])
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    def get(self, texto: str) -> Optional[np.ndarray]:
        key = self._hash_key(texto)
        return self._cache.get(key)

    def put(self, texto: str, embedding: np.ndarray):
        key = self._hash_key(texto)
        if key in self._cache:
            return
        self._cache[key] = embedding
        try:
            with open(self.ruta, "a", encoding="utf-8") as f:
                entry = {"key": key, "embedding": embedding.tolist(), "texto": texto[:100]}
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def __len__(self):
        return len(self._cache)

    def __contains__(self, texto: str) -> bool:
        return self._hash_key(texto) in self._cache


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

    def __init__(self, sistema_ianae=None, dim_vector: int = 15, modo_nlp: str = "auto",
                 cache_disco: bool = False, cache_ruta: Optional[str] = None):
        """
        Args:
            sistema_ianae: instancia de ConceptosLucas (o None para crear nueva)
            dim_vector: dimensión de vectores del sistema IANAE
            modo_nlp: modo del extractor ("auto", "spacy", "transformers", "basico")
            cache_disco: si True, persiste embeddings en disco
            cache_ruta: ruta al archivo de cache (por defecto .embedding_cache.jsonl)
        """
        self.dim_vector = dim_vector
        self.extractor = ExtractorConceptos(modo=modo_nlp)
        self.reductor = ReduccionDimensional(dim_target=dim_vector)
        self.sistema = sistema_ianae
        self._embeddings_cache = {}
        self._cache_disco = None
        if cache_disco:
            modelo_id = self.extractor.modo
            self._cache_disco = EmbeddingCacheDisco(ruta=cache_ruta, modelo_id=modelo_id)

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

        # Paso 2: Generar embeddings (con cache memoria + disco)
        embeddings_originales = {}
        for concepto in conceptos:
            nombre = concepto["nombre"]
            if nombre in self._embeddings_cache:
                embedding = self._embeddings_cache[nombre]
            elif self._cache_disco is not None and nombre in self._cache_disco:
                embedding = self._cache_disco.get(nombre)
                self._embeddings_cache[nombre] = embedding
            else:
                embedding = self.extractor.generar_embedding(nombre)
                self._embeddings_cache[nombre] = embedding
                if self._cache_disco is not None:
                    self._cache_disco.put(nombre, embedding)
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

    def procesar_largo(self, texto: str, max_palabras_chunk: int = 200,
                        solapamiento: int = 30, **kwargs) -> Dict:
        """
        Procesa textos largos dividiéndolos en chunks con solapamiento.

        Cada chunk se procesa individualmente y los conceptos/relaciones se
        fusionan deduplicando por nombre.

        Args:
            texto: texto largo a procesar
            max_palabras_chunk: palabras máximas por chunk
            solapamiento: palabras de solapamiento entre chunks
            **kwargs: pasados a procesar() (max_conceptos, categoria, etc.)

        Returns:
            Dict con resultados fusionados + metadata de chunking
        """
        chunks = self._dividir_chunks(texto, max_palabras_chunk, solapamiento)

        if len(chunks) <= 1:
            resultado = self.procesar(texto, **kwargs)
            resultado["chunks"] = 1
            return resultado

        # Procesar cada chunk
        todos_conceptos = {}  # nombre -> {concepto_dict, relevancia_acumulada}
        todas_relaciones = {}  # (c1, c2) -> peso_max
        todos_embeddings = {}
        todos_vectores = {}

        for chunk in chunks:
            resultado = self.procesar(chunk, **kwargs)

            for concepto in resultado.get("conceptos", []):
                nombre = concepto["nombre"]
                if nombre in todos_conceptos:
                    # Acumular relevancia (max)
                    if concepto["relevancia"] > todos_conceptos[nombre]["relevancia"]:
                        todos_conceptos[nombre] = concepto
                else:
                    todos_conceptos[nombre] = concepto

            for c1, c2, peso in resultado.get("relaciones", []):
                par = tuple(sorted([c1, c2]))
                if par not in todas_relaciones or peso > todas_relaciones[par]:
                    todas_relaciones[par] = peso

            for nombre, emb in resultado.get("embeddings_originales", {}).items():
                if nombre not in todos_embeddings:
                    todos_embeddings[nombre] = emb

            for nombre, vec in resultado.get("vectores_reducidos", {}).items():
                if nombre not in todos_vectores:
                    todos_vectores[nombre] = vec

        # Ordenar conceptos por relevancia
        conceptos_final = sorted(todos_conceptos.values(),
                                 key=lambda c: c["relevancia"], reverse=True)
        max_conceptos = kwargs.get("max_conceptos", 10)
        conceptos_final = conceptos_final[:max_conceptos]

        relaciones_final = [(c1, c2, peso) for (c1, c2), peso in todas_relaciones.items()]
        relaciones_final.sort(key=lambda x: x[2], reverse=True)

        return {
            "conceptos": conceptos_final,
            "relaciones": relaciones_final,
            "embeddings_originales": todos_embeddings,
            "vectores_reducidos": todos_vectores,
            "modo": self.extractor.modo,
            "dim_original": resultado.get("dim_original", 0),
            "dim_reducida": self.dim_vector,
            "chunks": len(chunks)
        }

    @staticmethod
    def _dividir_chunks(texto: str, max_palabras: int = 200,
                        solapamiento: int = 30) -> List[str]:
        """
        Divide texto en chunks de max_palabras con solapamiento.

        Intenta cortar en puntos naturales (., !, ?, \\n).
        """
        palabras = texto.split()
        if len(palabras) <= max_palabras:
            return [texto]

        chunks = []
        inicio = 0
        while inicio < len(palabras):
            fin = min(inicio + max_palabras, len(palabras))

            # Intentar cortar en punto natural (buscar hacia atrás)
            if fin < len(palabras):
                mejor_corte = fin
                for i in range(fin, max(inicio + max_palabras // 2, inicio), -1):
                    palabra = palabras[i - 1]
                    if palabra.endswith(('.', '!', '?', '\n')):
                        mejor_corte = i
                        break
                fin = mejor_corte

            chunk_palabras = palabras[inicio:fin]
            chunks.append(" ".join(chunk_palabras))

            # Avanzar con solapamiento
            inicio = fin - solapamiento
            if inicio >= len(palabras) - solapamiento:
                break

        return chunks

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
