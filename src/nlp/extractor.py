# extractor.py - Extracción de conceptos desde texto natural
# Scope: src/nlp/ (Worker-NLP)
# NO modifica nucleo.py - solo importa ConceptosLucas

import numpy as np
from collections import Counter
from typing import List, Dict, Tuple, Optional


class ExtractorConceptos:
    """
    Extrae conceptos clave de texto en español.

    Estrategia dual:
    - spaCy: tokenización, POS, NER, dependencias (extracción estructural)
    - sentence-transformers: embeddings semánticos (vectorización)

    Fallback: si no hay spaCy/transformers, usa extracción básica con regex+frecuencia.
    """

    def __init__(self, modo: str = "auto"):
        """
        Args:
            modo: "spacy", "transformers", "basico", o "auto" (detecta disponibilidad)
        """
        self.modo = modo
        self.nlp = None
        self.modelo_embeddings = None
        self._inicializar(modo)

    def _inicializar(self, modo: str):
        """Detecta e inicializa las bibliotecas disponibles."""
        if modo == "auto":
            self._intentar_spacy()
            self._intentar_transformers()
            if self.nlp is None and self.modelo_embeddings is None:
                print("[NLP] Modo básico: no se encontró spaCy ni sentence-transformers")
                self.modo = "basico"
            elif self.nlp and self.modelo_embeddings:
                self.modo = "completo"
                print("[NLP] Modo completo: spaCy + sentence-transformers")
            elif self.nlp:
                self.modo = "spacy"
                print("[NLP] Modo spaCy (sin embeddings de transformers)")
            else:
                self.modo = "transformers"
                print("[NLP] Modo transformers (sin análisis estructural spaCy)")
        elif modo == "spacy":
            self._intentar_spacy()
        elif modo == "transformers":
            self._intentar_transformers()

    def _intentar_spacy(self):
        """Intenta cargar spaCy con modelo español."""
        try:
            import spacy
            for modelo in ["es_core_news_md", "es_core_news_sm", "es_core_news_lg"]:
                try:
                    self.nlp = spacy.load(modelo)
                    print(f"[NLP] spaCy cargado: {modelo}")
                    return
                except OSError:
                    continue
            print("[NLP] spaCy instalado pero sin modelo español")
        except ImportError:
            pass

    def _intentar_transformers(self):
        """Intenta cargar sentence-transformers."""
        try:
            from sentence_transformers import SentenceTransformer
            self.modelo_embeddings = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2"
            )
            print("[NLP] sentence-transformers cargado: paraphrase-multilingual-MiniLM-L12-v2")
        except ImportError:
            pass
        except Exception as e:
            print(f"[NLP] Error cargando sentence-transformers: {e}")

    def extraer_conceptos(self, texto: str, max_conceptos: int = 10) -> List[Dict]:
        """
        Extrae conceptos clave del texto.

        Returns:
            Lista de dicts: [{"nombre": str, "relevancia": float, "tipo": str}, ...]
        """
        if self.nlp:
            return self._extraer_con_spacy(texto, max_conceptos)
        return self._extraer_basico(texto, max_conceptos)

    def _extraer_con_spacy(self, texto: str, max_conceptos: int) -> List[Dict]:
        """Extracción avanzada con spaCy: NER + sustantivos + chunks."""
        doc = self.nlp(texto)
        candidatos = Counter()
        tipos = {}

        # 1. Entidades nombradas (peso alto)
        for ent in doc.ents:
            nombre = ent.text.strip()
            if len(nombre) > 1:
                candidatos[nombre] += 3.0
                tipos[nombre] = f"NER:{ent.label_}"

        # 2. Noun chunks (frases nominales)
        for chunk in doc.noun_chunks:
            nombre = chunk.root.lemma_.strip()
            if len(nombre) > 2 and chunk.root.pos_ in ("NOUN", "PROPN"):
                candidatos[nombre] += 2.0
                if nombre not in tipos:
                    tipos[nombre] = f"CHUNK:{chunk.root.pos_}"

        # 3. Sustantivos y verbos relevantes (peso normal)
        for token in doc:
            if token.pos_ in ("NOUN", "PROPN") and len(token.lemma_) > 2:
                if not token.is_stop:
                    candidatos[token.lemma_] += 1.0
                    if token.lemma_ not in tipos:
                        tipos[token.lemma_] = f"POS:{token.pos_}"
            elif token.pos_ == "VERB" and len(token.lemma_) > 3:
                if not token.is_stop:
                    candidatos[token.lemma_] += 0.5
                    if token.lemma_ not in tipos:
                        tipos[token.lemma_] = "POS:VERB"

        # Normalizar relevancias y ordenar
        if not candidatos:
            return []

        max_score = max(candidatos.values())
        resultado = []
        for nombre, score in candidatos.most_common(max_conceptos):
            resultado.append({
                "nombre": nombre.replace(" ", "_"),
                "relevancia": round(score / max_score, 3),
                "tipo": tipos.get(nombre, "desconocido")
            })

        return resultado

    def _extraer_basico(self, texto: str, max_conceptos: int) -> List[Dict]:
        """Extracción básica sin dependencias externas: frecuencia + filtrado."""
        import re

        # Stopwords mínimas del español
        stopwords_es = {
            "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
            "en", "y", "o", "a", "al", "por", "para", "con", "sin", "que", "se",
            "su", "sus", "es", "son", "fue", "ser", "como", "más", "pero", "no",
            "lo", "le", "les", "me", "te", "nos", "esto", "esta", "este", "eso",
            "ese", "esa", "hay", "ya", "muy", "tan", "si", "ni", "entre", "sobre",
            "todo", "cada", "otro", "otra", "otros", "otras", "ha", "han", "desde",
            "hasta", "también", "puede", "pueden", "hace", "hacen", "tiene", "tienen"
        }

        # Tokenizar y filtrar
        tokens = re.findall(r'\b[a-záéíóúñü]{3,}\b', texto.lower())
        tokens_filtrados = [t for t in tokens if t not in stopwords_es]

        # Contar frecuencias
        frecuencias = Counter(tokens_filtrados)

        if not frecuencias:
            return []

        max_freq = max(frecuencias.values())
        resultado = []
        for palabra, freq in frecuencias.most_common(max_conceptos):
            resultado.append({
                "nombre": palabra,
                "relevancia": round(freq / max_freq, 3),
                "tipo": "frecuencia"
            })

        return resultado

    def generar_embedding(self, texto: str) -> np.ndarray:
        """
        Genera embedding para un texto/concepto.

        Returns:
            Vector numpy. Dimensión depende del modelo (384 para MiniLM, 300 para spaCy).
        """
        if self.modelo_embeddings:
            embedding = self.modelo_embeddings.encode(texto)
            return np.array(embedding)

        if self.nlp and self.nlp.vocab.vectors.shape[0] > 0:
            doc = self.nlp(texto)
            return doc.vector

        # Fallback: vector aleatorio con seed determinista
        seed = sum(ord(c) for c in texto)
        rng = np.random.RandomState(seed)
        return rng.normal(0, 1, 15)

    def extraer_relaciones(self, texto: str, conceptos: List[Dict]) -> List[Tuple[str, str, float]]:
        """
        Detecta relaciones entre conceptos extraídos.

        Returns:
            Lista de (concepto1, concepto2, peso) donde peso ∈ [0, 1]
        """
        if self.modelo_embeddings:
            return self._relaciones_por_similitud(conceptos)

        if self.nlp:
            return self._relaciones_por_dependencias(texto, conceptos)

        return self._relaciones_por_coocurrencia(texto, conceptos)

    def _relaciones_por_similitud(self, conceptos: List[Dict]) -> List[Tuple[str, str, float]]:
        """Calcula relaciones usando similitud coseno de embeddings."""
        nombres = [c["nombre"] for c in conceptos]
        if len(nombres) < 2:
            return []

        embeddings = self.modelo_embeddings.encode(nombres)

        # Normalizar para similitud coseno
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings_norm = embeddings / norms

        similitudes = embeddings_norm @ embeddings_norm.T

        relaciones = []
        for i in range(len(nombres)):
            for j in range(i + 1, len(nombres)):
                sim = float(similitudes[i, j])
                # Solo relaciones con similitud significativa
                if sim > 0.2:
                    peso = max(0.1, min(1.0, sim))
                    relaciones.append((nombres[i], nombres[j], round(peso, 3)))

        relaciones.sort(key=lambda x: x[2], reverse=True)
        return relaciones

    def _relaciones_por_dependencias(self, texto: str, conceptos: List[Dict]) -> List[Tuple[str, str, float]]:
        """Detecta relaciones usando árbol de dependencias de spaCy."""
        doc = self.nlp(texto)
        nombres_set = {c["nombre"].lower().replace("_", " ") for c in conceptos}

        relaciones = []
        for sent in doc.sents:
            tokens_relevantes = []
            for token in sent:
                if token.lemma_.lower() in nombres_set or token.text.lower() in nombres_set:
                    tokens_relevantes.append(token)

            # Relaciones entre tokens relevantes en la misma oración
            for i, t1 in enumerate(tokens_relevantes):
                for t2 in tokens_relevantes[i + 1:]:
                    # Distancia en el árbol de dependencias
                    dist = abs(t1.i - t2.i)
                    peso = max(0.1, 1.0 - (dist / 20.0))

                    n1 = t1.lemma_.replace(" ", "_")
                    n2 = t2.lemma_.replace(" ", "_")
                    relaciones.append((n1, n2, round(peso, 3)))

        return relaciones

    def _relaciones_por_coocurrencia(self, texto: str, conceptos: List[Dict]) -> List[Tuple[str, str, float]]:
        """Fallback: relaciones basadas en co-ocurrencia en ventana de texto."""
        nombres = [c["nombre"].lower() for c in conceptos]
        palabras = texto.lower().split()
        ventana = 10

        coocurrencias = Counter()
        for i, palabra in enumerate(palabras):
            for nombre in nombres:
                if nombre in palabra:
                    ventana_texto = palabras[max(0, i - ventana):i + ventana]
                    for otro_nombre in nombres:
                        if otro_nombre != nombre:
                            if any(otro_nombre in p for p in ventana_texto):
                                par = tuple(sorted([nombre, otro_nombre]))
                                coocurrencias[par] += 1

        if not coocurrencias:
            return []

        max_co = max(coocurrencias.values())
        relaciones = []
        for (c1, c2), count in coocurrencias.most_common():
            peso = round(count / max_co, 3)
            if peso > 0.1:
                relaciones.append((c1, c2, peso))

        return relaciones
