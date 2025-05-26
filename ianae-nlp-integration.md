# Integración de Procesamiento de Lenguaje Natural (NLP) en IANAE

Este documento detalla el diseño e implementación de mejoras en la interfaz de IANAE con datos de texto, incorporando técnicas modernas de Procesamiento de Lenguaje Natural (NLP). El objetivo es enriquecer la capacidad del sistema para extraer, relacionar y utilizar conceptos a partir de textos.

## 1. Visión General

### 1.1 Estado Actual

Actualmente, IANAE incluye capacidades básicas para procesar texto en el módulo `emergente.py`, principalmente a través del método `cargar_conceptos_desde_texto()`. Este método implementa un enfoque simple:

```python
def cargar_conceptos_desde_texto(self, texto, max_conceptos=30):
    # Preprocesamiento simple
    texto = texto.lower()
    for c in ".,;:!?()[]{}\"'":
        texto = texto.replace(c, ' ')
        
    palabras = texto.split()
    
    # Filtrar palabras comunes (simplificado)
    stop_words = {"el", "la", "los", "las", "un", "una", ...}
    palabras_filtradas = [p for p in palabras if p not in stop_words and len(p) > 3]
    
    # Contar frecuencias y seleccionar las más comunes
    frecuencias = {}
    for p in palabras_filtradas:
        frecuencias[p] = frecuencias.get(p, 0) + 1
        
    palabras_ordenadas = sorted(frecuencias.items(), key=lambda x: x[1], reverse=True)
    conceptos_extraidos = [p for p, f in palabras_ordenadas[:max_conceptos]]
    
    # Crear relaciones basadas en co-ocurrencia en el texto
    # ...
```

Limitaciones identificadas:
1. **Procesamiento léxico básico**: Opera a nivel de palabras sin considerar frases o entidades.
2. **Representación simple**: No aprovecha embeddings modernos para capturar semántica.
3. **Relaciones limitadas**: Solo establece relaciones por co-ocurrencia.
4. **Sin análisis semántico**: No identifica relaciones semánticas como sinonimia, hiponimia, etc.
5. **Monolingüe**: No tiene capacidades multilingües robustas.

### 1.2 Objetivos de la Integración NLP

1. **Mejorar extracción de conceptos**: Identificar entidades, frases clave y conceptos significativos.
2. **Enriquecer representación vectorial**: Utilizar embeddings modernos para representaciones semánticamente ricas.
3. **Identificar relaciones avanzadas**: Detectar relaciones semánticas más allá de la co-ocurrencia.
4. **Añadir capacidades multilingües**: Permitir procesamiento en múltiples idiomas.
5. **Facilitar análisis de documentos completos**: Manejar textos largos manteniendo contexto.

## 2. Arquitectura Propuesta

### 2.1 Nuevo Módulo: `nlp_interface.py`

Se propone crear un nuevo módulo dedicado a la interfaz con NLP, con la siguiente estructura:

```
IANAE/
│
├── nucleo.py           (Existente - Núcleo del sistema)
├── emergente.py        (Existente - Pensamiento emergente)
├── main.py             (Existente - Interfaz de usuario)
├── experimento.py      (Existente - Demostraciones)
│
├── nlp_interface.py    (NUEVO - Interfaz con NLP)
└── embeddings_cache/   (NUEVO - Caché para embeddings)
```

### 2.2 Dependencias Externas

La implementación requerirá bibliotecas modernas de NLP:

```
transformers==4.34.0    # Modelos de lenguaje transformers (BERT, etc.)
spacy==3.7.1            # Procesamiento lingüístico y NER
sentence-transformers==2.2.2  # Embeddings de oraciones optimizados
nltk==3.8.1             # Herramientas lingüísticas adicionales
```

### 2.3 Diagrama de Componentes

```
+--------------------+       +--------------------+
|   nlp_interface.py |<------|   emergente.py     |
| - TextProcessor    |       | - PensamientoEmer. |
| - ConceptExtractor |       |                    |
| - RelationDetector |       |                    |
+--------------------+       +--------------------+
         ^                            |
         |                            |
         v                            v
+--------------------+       +--------------------+
| Bibliotecas NLP    |       |    nucleo.py       |
| - transformers     |       | - ConceptosDifusos |
| - spacy            |       |                    |
| - sentence-transf. |       |                    |
+--------------------+       +--------------------+
```

## 3. Componentes Principales

### 3.1 Clase `TextProcessor`

Responsable del procesamiento básico de texto y gestión de modelos lingüísticos.

```python
class TextProcessor:
    """
    Procesador de texto para IANAE que incorpora modelos NLP modernos
    """
    
    def __init__(self, 
                 language="es",
                 use_gpu=False, 
                 embedding_model="sentence-transformers/distiluse-base-multilingual-cased-v1",
                 spacy_model=None):
        """
        Inicializa el procesador de texto
        
        Args:
            language: Código de idioma principal ('es', 'en', etc.)
            use_gpu: Si se debe usar GPU para aceleración
            embedding_model: Modelo para generar embeddings
            spacy_model: Modelo spaCy a usar (si None, se selecciona según language)
        """
        self.language = language
        self.use_gpu = use_gpu
        
        # Configurar modelo de embedding
        self.embedding_model_name = embedding_model
        self.embedding_model = self._load_embedding_model(embedding_model)
        
        # Configurar modelo spaCy
        if not spacy_model:
            spacy_model = self._get_default_spacy_model(language)
        self.nlp = self._load_spacy_model(spacy_model)
        
        # Cache para embeddings
        self.embedding_cache = {}
        
        # Configuración NLTK
        self._ensure_nltk_resources()
    
    def _load_embedding_model(self, model_name):
        """Carga el modelo de embeddings desde Hugging Face"""
        from sentence_transformers import SentenceTransformer
        
        # Configurar dispositivo de cómputo
        device = "cuda" if self.use_gpu and torch.cuda.is_available() else "cpu"
        
        # Cargar modelo
        model = SentenceTransformer(model_name, device=device)
        return model
    
    def _load_spacy_model(self, model_name):
        """Carga el modelo spaCy especificado"""
        import spacy
        try:
            return spacy.load(model_name)
        except OSError:
            # Modelo no encontrado, descargarlo
            print(f"Modelo spaCy '{model_name}' no encontrado. Descargando...")
            spacy.cli.download(model_name)
            return spacy.load(model_name)
    
    def _get_default_spacy_model(self, language):
        """Obtiene el modelo spaCy por defecto para el idioma"""
        lang_models = {
            "es": "es_core_news_md",
            "en": "en_core_web_md",
            "fr": "fr_core_news_md",
            "de": "de_core_news_md",
            "pt": "pt_core_news_md",
            "it": "it_core_news_md",
            "nl": "nl_core_news_md",
            # Añadir más idiomas según sea necesario
        }
        return lang_models.get(language, "xx_ent_wiki_sm")  # Modelo multilingüe como fallback
    
    def _ensure_nltk_resources(self):
        """Asegura que los recursos NLTK necesarios estén descargados"""
        import nltk
        
        required_resources = [
            ('punkt', 'tokenizers/punkt'),
            ('wordnet', 'corpora/wordnet'),
            ('stopwords', 'corpora/stopwords'),
        ]
        
        for resource, path in required_resources:
            try:
                nltk.data.find(path)
            except LookupError:
                nltk.download(resource)
    
    def preprocess_text(self, text):
        """
        Preprocesa el texto para análisis
        
        Args:
            text: Texto a preprocesar
            
        Returns:
            Documento spaCy procesado
        """
        # Procesar con spaCy
        doc = self.nlp(text)
        return doc
    
    def get_embedding(self, text, use_cache=True):
        """
        Obtiene el embedding de un texto
        
        Args:
            text: Texto para obtener embedding
            use_cache: Si se debe usar caché para textos repetidos
            
        Returns:
            Vector de embedding (numpy array)
        """
        if use_cache and text in self.embedding_cache:
            return self.embedding_cache[text]
        
        # Obtener embedding
        embedding = self.embedding_model.encode(text)
        
        # Guardar en caché si es necesario
        if use_cache:
            self.embedding_cache[text] = embedding
            
        return embedding
    
    def detect_language(self, text):
        """
        Detecta el idioma del texto
        
        Args:
            text: Texto para detectar idioma
            
        Returns:
            Código ISO del idioma detectado (2 caracteres)
        """
        from langdetect import detect
        try:
            return detect(text)
        except:
            return self.language  # Fallback al idioma por defecto
    
    def save_embeddings_cache(self, filepath='embeddings_cache.pkl'):
        """Guarda la caché de embeddings a un archivo"""
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump(self.embedding_cache, f)
    
    def load_embeddings_cache(self, filepath='embeddings_cache.pkl'):
        """Carga la caché de embeddings desde un archivo"""
        import pickle
        try:
            with open(filepath, 'rb') as f:
                self.embedding_cache = pickle.load(f)
            return True
        except FileNotFoundError:
            return False
```

### 3.2 Clase `ConceptExtractor`

Encargada de extraer conceptos significativos de textos.

```python
class ConceptExtractor:
    """
    Extractor de conceptos a partir de texto para IANAE
    """
    
    def __init__(self, text_processor):
        """
        Inicializa el extractor de conceptos
        
        Args:
            text_processor: Instancia de TextProcessor
        """
        self.processor = text_processor
        
        # Cargar stopwords para varios idiomas
        import nltk
        from nltk.corpus import stopwords
        
        self.stopwords = {}
        try:
            for lang in ['spanish', 'english', 'french', 'german', 'portuguese', 'italian']:
                self.stopwords[lang[:2]] = set(stopwords.words(lang))
        except:
            nltk.download('stopwords')
            for lang in ['spanish', 'english', 'french', 'german', 'portuguese', 'italian']:
                self.stopwords[lang[:2]] = set(stopwords.words(lang))
    
    def extract_concepts(self, text, max_concepts=30, min_word_length=3):
        """
        Extrae conceptos de un texto utilizando múltiples métodos
        
        Args:
            text: Texto de donde extraer conceptos
            max_concepts: Número máximo de conceptos a extraer
            min_word_length: Longitud mínima de palabras a considerar
            
        Returns:
            Lista de diccionarios de conceptos con sus propiedades
        """
        # Detectar idioma para usar stopwords adecuadas
        lang = self.processor.detect_language(text)
        current_stopwords = self.stopwords.get(lang, self.stopwords.get('en', set()))
        
        # Preprocesar texto
        doc = self.processor.preprocess_text(text)
        
        # 1. Extraer entidades nombradas
        entities = self._extract_entities(doc)
        
        # 2. Extraer frases clave
        keyphrases = self._extract_keyphrases(doc, current_stopwords, min_word_length)
        
        # 3. Extraer términos por TF-IDF (simulado con frecuencia+filtros)
        terms = self._extract_significant_terms(doc, current_stopwords, min_word_length)
        
        # Combinar y ordenar por relevancia
        all_concepts = {}
        
        # Añadir entidades (mayor prioridad)
        for entity in entities:
            if entity['text'].lower() not in all_concepts:
                all_concepts[entity['text'].lower()] = {
                    'text': entity['text'],
                    'type': entity['type'],
                    'relevance': 0.9 + entity['relevance'],
                    'source': 'entity',
                    'count': entity.get('count', 1)
                }
        
        # Añadir frases clave
        for keyphrase in keyphrases:
            if keyphrase['text'].lower() not in all_concepts:
                all_concepts[keyphrase['text'].lower()] = {
                    'text': keyphrase['text'],
                    'type': 'keyphrase',
                    'relevance': 0.7 + keyphrase['relevance'],
                    'source': 'keyphrase',
                    'count': keyphrase.get('count', 1)
                }
        
        # Añadir términos
        for term in terms:
            if term['text'].lower() not in all_concepts:
                all_concepts[term['text'].lower()] = {
                    'text': term['text'],
                    'type': 'term',
                    'relevance': 0.5 + term['relevance'],
                    'source': 'term',
                    'count': term.get('count', 1)
                }
        
        # Convertir a lista y ordenar por relevancia
        concepts_list = list(all_concepts.values())
        concepts_list.sort(key=lambda x: x['relevance'], reverse=True)
        
        # Limitar al número máximo y asignar embeddings
        top_concepts = concepts_list[:max_concepts]
        self._assign_embeddings(top_concepts)
        
        return top_concepts
    
    def _extract_entities(self, doc):
        """Extrae entidades nombradas del documento"""
        entities = []
        seen_texts = set()
        
        for ent in doc.ents:
            if ent.text not in seen_texts:
                entities.append({
                    'text': ent.text,
                    'type': ent.label_,
                    'relevance': 0.2,  # Base relevance
                    'count': 1
                })
                seen_texts.add(ent.text)
            else:
                # Incrementar conteo para entidades repetidas
                for entity in entities:
                    if entity['text'] == ent.text:
                        entity['count'] += 1
                        entity['relevance'] += 0.05  # Aumentar relevancia
                        break
        
        return entities
    
    def _extract_keyphrases(self, doc, stopwords, min_length):
        """Extrae frases clave usando patrones POS y reglas"""
        import spacy
        
        # Patrones para frases nominales
        noun_chunks = list(doc.noun_chunks)
        keyphrases = []
        seen_texts = set()
        
        for chunk in noun_chunks:
            # Filtrar chunks demasiado cortos o con stopwords
            chunk_text = chunk.text.strip()
            if (len(chunk_text) >= min_length and 
                not all(token.is_stop for token in chunk) and
                not all(token.text.lower() in stopwords for token in chunk)):
                
                # Normalizar y limpiar
                clean_text = ' '.join([token.lemma_ for token in chunk 
                                       if not token.is_punct and len(token.text) >= min_length])
                
                if clean_text and clean_text not in seen_texts:
                    # Calcular relevancia basada en longitud y POS tags
                    relevance = 0.1  # Base
                    relevance += min(0.3, len(chunk) * 0.05)  # Más largo, más relevante (hasta cierto punto)
                    
                    # Bonus por contener sustantivos propios o adjetivos importantes
                    if any(token.pos_ == 'PROPN' for token in chunk):
                        relevance += 0.2
                    if any(token.pos_ == 'ADJ' and not token.is_stop for token in chunk):
                        relevance += 0.1
                    
                    keyphrases.append({
                        'text': clean_text,
                        'type': 'keyphrase',
                        'relevance': relevance,
                        'count': 1
                    })
                    seen_texts.add(clean_text)
                else:
                    # Incrementar conteo para frases repetidas
                    for keyphrase in keyphrases:
                        if keyphrase['text'] == clean_text:
                            keyphrase['count'] += 1
                            keyphrase['relevance'] += 0.03  # Aumentar relevancia
                            break
        
        return keyphrases
    
    def _extract_significant_terms(self, doc, stopwords, min_length):
        """Extrae términos significativos usando frecuencia y POS tags"""
        term_freq = {}
        
        # Contar frecuencias por lema, filtrando por POS y stopwords
        for token in doc:
            if (not token.is_stop and not token.is_punct and 
                len(token.text) >= min_length and
                token.lemma_.lower() not in stopwords and
                token.pos_ in ['NOUN', 'VERB', 'ADJ', 'PROPN']):
                
                lemma = token.lemma_.lower()
                if lemma in term_freq:
                    term_freq[lemma]['count'] += 1
                else:
                    term_freq[lemma] = {
                        'text': token.lemma_,
                        'pos': token.pos_,
                        'count': 1
                    }
        
        # Calcular relevancia basada en frecuencia y POS
        terms = []
        for lemma, data in term_freq.items():
            relevance = min(0.5, data['count'] * 0.05)  # Base por frecuencia, con tope
            
            # Ajustar por POS
            pos_weights = {
                'PROPN': 0.3,  # Nombres propios tienen más peso
                'NOUN': 0.2,   # Sustantivos
                'ADJ': 0.15,   # Adjetivos
                'VERB': 0.1    # Verbos
            }
            relevance += pos_weights.get(data['pos'], 0)
            
            terms.append({
                'text': data['text'],
                'type': 'term',
                'relevance': relevance,
                'count': data['count']
            })
        
        # Ordenar por relevancia
        terms.sort(key=lambda x: x['relevance'], reverse=True)
        return terms
    
    def _assign_embeddings(self, concepts):
        """Asigna embeddings a los conceptos extraídos"""
        for concept in concepts:
            concept['embedding'] = self.processor.get_embedding(concept['text'])
```

### 3.3 Clase `RelationDetector`

Encargada de detectar y evaluar relaciones semánticas entre conceptos.

```python
class RelationDetector:
    """
    Detector de relaciones semánticas entre conceptos para IANAE
    """
    
    def __init__(self, text_processor):
        """
        Inicializa el detector de relaciones
        
        Args:
            text_processor: Instancia de TextProcessor
        """
        self.processor = text_processor
        
        # Umbral de similitud para considerar relación
        self.similarity_threshold = 0.45
        
        # Carga de recursos para relaciones léxicas (WordNet)
        self._init_wordnet_resources()
    
    def _init_wordnet_resources(self):
        """Inicializa recursos de WordNet para relaciones léxicas"""
        import nltk
        from nltk.corpus import wordnet
        
        try:
            wordnet.synsets('test')
        except LookupError:
            nltk.download('wordnet')
            nltk.download('omw-1.4')  # Open Multilingual WordNet
    
    def detect_relationships(self, concepts, text=None, relationship_types=None):
        """
        Detecta relaciones entre conceptos utilizando múltiples métodos
        
        Args:
            concepts: Lista de conceptos (con embeddings)
            text: Texto original (opcional, para co-ocurrencia)
            relationship_types: Tipos de relaciones a detectar (None=todas)
            
        Returns:
            Lista de relaciones detectadas
        """
        if relationship_types is None:
            relationship_types = ['embedding', 'wordnet', 'cooccurrence']
        
        all_relations = []
        
        # 1. Relaciones por similitud de embeddings
        if 'embedding' in relationship_types:
            embedding_relations = self._detect_embedding_relations(concepts)
            all_relations.extend(embedding_relations)
        
        # 2. Relaciones léxicas (WordNet)
        if 'wordnet' in relationship_types:
            wordnet_relations = self._detect_wordnet_relations(concepts)
            all_relations.extend(wordnet_relations)
        
        # 3. Relaciones por co-ocurrencia (si se proporciona texto)
        if 'cooccurrence' in relationship_types and text:
            cooc_relations = self._detect_cooccurrence_relations(concepts, text)
            all_relations.extend(cooc_relations)
        
        # Eliminar duplicados y relaciones de un concepto consigo mismo
        filtered_relations = []
        seen_pairs = set()
        
        for rel in all_relations:
            pair = frozenset([rel['source'], rel['target']])
            if pair not in seen_pairs and rel['source'] != rel['target']:
                filtered_relations.append(rel)
                seen_pairs.add(pair)
        
        # Ordenar por fuerza de relación
        filtered_relations.sort(key=lambda x: x['strength'], reverse=True)
        
        return filtered_relations
    
    def _detect_embedding_relations(self, concepts):
        """Detecta relaciones basadas en similitud de embeddings"""
        relations = []
        
        for i, concept1 in enumerate(concepts):
            for j, concept2 in enumerate(concepts[i+1:], i+1):
                # Calcular similitud coseno entre embeddings
                embedding1 = concept1['embedding']
                embedding2 = concept2['embedding']
                
                if embedding1 is not None and embedding2 is not None:
                    similarity = self._cosine_similarity(embedding1, embedding2)
                    
                    # Considerar relación si supera umbral
                    if similarity > self.similarity_threshold:
                        relations.append({
                            'source': concept1['text'],
                            'target': concept2['text'],
                            'type': 'semantic_similarity',
                            'strength': float(similarity),  # Convertir a float para serialización
                            'method': 'embedding'
                        })
        
        return relations
    
    def _cosine_similarity(self, vec1, vec2):
        """Calcula similitud coseno entre dos vectores"""
        import numpy as np
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0
            
        return dot / (norm1 * norm2)
    
    def _detect_wordnet_relations(self, concepts):
        """Detecta relaciones léxicas usando WordNet"""
        from nltk.corpus import wordnet as wn
        
        relations = []
        
        for i, concept1 in enumerate(concepts):
            for j, concept2 in enumerate(concepts[i+1:], i+1):
                # Buscar synsets para ambos conceptos
                synsets1 = wn.synsets(concept1['text'], lang=self.processor.language)
                synsets2 = wn.synsets(concept2['text'], lang=self.processor.language)
                
                # Si no hay synsets en el idioma actual, intentar en inglés
                if not synsets1:
                    synsets1 = wn.synsets(concept1['text'], lang='eng')
                if not synsets2:
                    synsets2 = wn.synsets(concept2['text'], lang='eng')
                
                # Buscar relaciones si hay synsets
                if synsets1 and synsets2:
                    # Similitud de Wu-Palmer (mide relación taxonómica)
                    max_wup = 0
                    for s1 in synsets1:
                        for s2 in synsets2:
                            try:
                                wup = s1.wup_similarity(s2)
                                if wup and wup > max_wup:
                                    max_wup = wup
                            except:
                                pass
                    
                    if max_wup > 0.7:  # Umbral para considerar relación léxica
                        relation_type = 'related'
                        
                        # Determinar tipo específico de relación
                        if any(s1.hypernyms() for s1 in synsets1 for s2 in synsets2 if s2 in s1.hypernyms()):
                            relation_type = 'hyponym'  # concept1 es un tipo de concept2
                        elif any(s2.hypernyms() for s2 in synsets2 for s1 in synsets1 if s1 in s2.hypernyms()):
                            relation_type = 'hypernym'  # concept2 es un tipo de concept1
                        
                        relations.append({
                            'source': concept1['text'],
                            'target': concept2['text'],
                            'type': relation_type,
                            'strength': float(max_wup),
                            'method': 'wordnet'
                        })
        
        return relations
    
    def _detect_cooccurrence_relations(self, concepts, text):
        """Detecta relaciones por co-ocurrencia en el texto"""
        doc = self.processor.preprocess_text(text)
        tokens = [token.text.lower() for token in doc]
        
        # Crear mapa de conceptos a tokens
        concept_tokens = {}
        for concept in concepts:
            # Normalizar para búsqueda
            concept_text = concept['text'].lower()
            # Considerar múltiples formas (singular/plural, etc.)
            variations = [concept_text]
            if ' ' not in concept_text:  # Solo para términos simples
                variations.extend([concept_text + 's', concept_text + 'es'])
            concept_tokens[concept['text']] = variations
        
        # Ventana de co-ocurrencia
        window_size = 10
        relations = []
        
        # Contar co-ocurrencias
        cooccurrence_counts = {}
        
        for i, token in enumerate(tokens):
            # Encontrar conceptos en esta posición
            matched_concepts = []
            for concept, variations in concept_tokens.items():
                if any(token == var for var in variations):
                    matched_concepts.append(concept)
            
            if matched_concepts:
                # Buscar otros conceptos en la ventana
                window_start = max(0, i - window_size)
                window_end = min(len(tokens), i + window_size + 1)
                
                for j in range(window_start, window_end):
                    if i != j:  # No contar el mismo token
                        token_j = tokens[j]
                        
                        # Encontrar conceptos en posición j
                        for concept_j, variations_j in concept_tokens.items():
                            if any(token_j == var for var in variations_j):
                                for concept_i in matched_concepts:
                                    if concept_i != concept_j:
                                        # Crear par ordenado
                                        pair = tuple(sorted([concept_i, concept_j]))
                                        
                                        # Incrementar contador
                                        if pair in cooccurrence_counts:
                                            cooccurrence_counts[pair] += 1
                                        else:
                                            cooccurrence_counts[pair] = 1
        
        # Normalizar y crear relaciones
        max_count = max(cooccurrence_counts.values()) if cooccurrence_counts else 1
        
        for pair, count in cooccurrence_counts.items():
            # Normalizar fuerza entre 0 y 1
            strength = count / max_count
            
            if strength > 0.2:  # Umbral para considerar co-ocurrencia significativa
                relations.append({
                    'source': pair[0],
                    'target': pair[1],
                    'type': 'cooccurrence',
                    'strength': float(strength),
                    'method': 'cooccurrence',
                    'count': count
                })
        
        return relations
```

### 3.4 Clase `DocumentProcessor`

Encargada de procesar documentos completos y extraer estructuras conceptuales.

```python
class DocumentProcessor:
    """
    Procesador de documentos completos para IANAE
    """
    
    def __init__(self, text_processor, concept_extractor, relation_detector):
        """
        Inicializa el procesador de documentos
        
        Args:
            text_processor: Instancia de TextProcessor
            concept_extractor: Instancia de ConceptExtractor
            relation_detector: Instancia de RelationDetector
        """
        self.processor = text_processor
        self.concept_extractor = concept_extractor
        self.relation_detector = relation_detector
    
    def process_document(self, text, max_concepts=50):
        """
        Procesa un documento completo para extraer conceptos y relaciones
        
        Args:
            text: Texto del documento
            max_concepts: Número máximo de conceptos a extraer
            
        Returns:
            Diccionario con conceptos y relaciones
        """
        # Detectar idioma
        language = self.processor.detect_language(text)
        
        # Dividir en secciones si el documento es largo
        sections = self._split_into_sections(text)
        
        # Extraer conceptos por sección
        section_concepts = []
        for section in sections:
            concepts = self.concept_extractor.extract_concepts(
                section, 
                max_concepts=max(20, max_concepts // len(sections))
            )
            section_concepts.append(concepts)
        
        # Consolidar conceptos de todas las secciones
        all_concepts = self._consolidate_concepts(section_concepts)
        
        # Limitar al número máximo y ordenar por relevancia
        all_concepts.sort(key=lambda x: x['relevance'], reverse=True)
        top_concepts = all_concepts[:max_concepts]
        
        # Detectar relaciones entre conceptos principales
        relations = self.relation_detector.detect_relationships(top_concepts, text=text)
        
        # Crear estructura jerárquica de temas/subtemas (si hay suficientes conceptos)
        hierarchy = self._create_concept_hierarchy(top_concepts, relations) if len(top_concepts) > 10 else []
        
        # Generar resumen conceptual
        summary = self._generate_conceptual_summary(top_concepts[:10], relations)
        
        return {
            "language": language,
            "concepts": top_concepts,
            "relations": relations,
            "hierarchy": hierarchy,
            "summary": summary
        }
    
    def _split_into_sections(self, text, max_section_length=5000):
        """Divide un documento largo en secciones más manejables"""
        # Si el texto es corto, devolverlo como una sola sección
        if len(text) <= max_section_length:
            return [text]
        
        # Detectar párrafos (separados por doble salto de línea)
        paragraphs = text.split('\n\n')
        
        # Combinar párrafos en secciones del tamaño adecuado
        sections = []
        current_section = ""
        
        for paragraph in paragraphs:
            if len(current_section) + len(paragraph) <= max_section_length:
                current_section += paragraph + "\n\n"
            else:
                sections.append(current_section)
                current_section = paragraph + "\n\n"
        
        # Añadir la última sección si tiene contenido
        if current_section:
            sections.append(current_section)
            
        return sections
    
    def _consolidate_concepts(self, section_concepts):
        """Consolida conceptos de diferentes secciones, fusionando duplicados"""
        concept_map = {}
        
        for section_idx, concepts in enumerate(section_concepts):
            for concept in concepts:
                text = concept['text'].lower()
                
                if text in concept_map:
                    # Actualizar concepto existente
                    existing = concept_map[text]
                    existing['count'] += concept.get('count', 1)
                    existing['relevance'] = max(existing['relevance'], concept['relevance'])
                    existing['sections'].add(section_idx)
                else:
                    # Crear copia del concepto con sección
                    concept_copy = concept.copy()
                    concept_copy['sections'] = {section_idx}
                    concept_map[text] = concept_copy
        
        # Convertir de nuevo a lista
        consolidated = list(concept_map.values())
        
        # Recalcular relevancia basada en presencia en múltiples secciones
        for concept in consolidated:
            # Bonus por aparecer en múltiples secciones
            section_bonus = min(0.3, len(concept['sections']) * 0.1)
            concept['relevance'] += section_bonus
            
            # Convertir secciones a lista para serialización
            concept['sections'] = list(concept['sections'])
            
        return consolidated
    
    def _create_concept_hierarchy(self, concepts, relations, max_depth=3):
        """Crea una jerarquía de conceptos basada en relaciones"""
        import networkx as nx
        
        # Crear grafo dirigido de relaciones
        G = nx.DiGraph()
        
        # Añadir nodos (conceptos)
        for concept in concepts:
            G.add_node(concept['text'], **concept)
        
        # Añadir aristas (relaciones)
        for relation in relations:
            # Crear arista direccional para relaciones jerárquicas
            if relation['type'] in ['hypernym', 'hyponym']:
                if relation['type'] == 'hypernym':
                    G.add_edge(relation['source'], relation['target'], **relation)
                else:
                    G.add_edge(relation['target'], relation['source'], **relation)
            else:
                # Para otras relaciones, crear arista con mayor peso para concepto más relevante
                source_concept = next((c for c in concepts if c['text'] == relation['source']), None)
                target_concept = next((c for c in concepts if c['text'] == relation['target']), None)
                
                if source_concept and target_concept:
                    if source_concept['relevance'] > target_concept['relevance']:
                        G.add_edge(relation['source'], relation['target'], **relation)
                    else:
                        G.add_edge(relation['target'], relation['source'], **relation)
        
        # Encontrar raíces (conceptos sin padres o con alta relevancia)
        roots = []
        for concept in concepts[:5]:  # Considerar los 5 conceptos más relevantes como posibles raíces
            in_degree = G.in_degree(concept['text'])
            if in_degree == 0 or concept['relevance'] > 0.8:
                roots.append(concept['text'])
        
        # Si no hay raíces, usar el concepto más relevante
        if not roots and concepts:
            roots = [concepts[0]['text']]
        
        # Construir jerarquía recursivamente
        hierarchy = []
        visited = set()
        
        for root in roots:
            tree = self._build_subtree(G, root, visited, max_depth)
            if tree:
                hierarchy.append(tree)
        
        return hierarchy
    
    def _build_subtree(self, graph, node, visited, max_depth, current_depth=0):
        """Construye un subárbol recursivamente para la jerarquía de conceptos"""
        if current_depth > max_depth or node in visited:
            return None
            
        visited.add(node)
        
        # Crear nodo actual
        subtree = {
            "concept": node,
            "children": []
        }
        
        # Añadir hijos
        if current_depth < max_depth:
            for child in graph.successors(node):
                if child not in visited:
                    child_tree = self._build_subtree(
                        graph, child, visited, max_depth, current_depth + 1
                    )
                    if child_tree:
                        subtree["children"].append(child_tree)
        
        return subtree
    
    def _generate_conceptual_summary(self, top_concepts, relations):
        """Genera un resumen textual basado en los conceptos principales"""
        if not top_concepts:
            return ""
            
        # Crear mapa de relaciones por concepto
        concept_relations = {}
        for relation in relations:
            source = relation['source']
            target = relation['target']
            
            if source not in concept_relations:
                concept_relations[source] = []
            concept_relations[source].append(relation)
            
            if target not in concept_relations:
                concept_relations[target] = []
            concept_relations[target].append(relation)
        
        # Generar resumen
        lines = []
        
        # Primera línea con conceptos principales
        main_concepts = [c['text'] for c in top_concepts[:3]]
        lines.append(f"El documento trata principalmente sobre {', '.join(main_concepts)}.")
        
        # Añadir líneas sobre conceptos importantes y sus relaciones
        for concept in top_concepts[:5]:  # Top 5 conceptos
            concept_text = concept['text']
            concept_type = concept['type']
            
            # Descripción según tipo de concepto
            if concept_type == 'entity':
                description = f"{concept_text} aparece como una entidad importante"
            elif concept_type == 'keyphrase':
                description = f"La frase clave '{concept_text}' representa un tema central"
            else:
                description = f"El concepto '{concept_text}' es significativo"
                
            # Añadir información sobre relaciones
            related = concept_relations.get(concept_text, [])
            if related:
                # Filtrar a las 3 relaciones más fuertes
                top_relations = sorted(related, key=lambda r: r['strength'], reverse=True)[:3]
                
                relation_texts = []
                for rel in top_relations:
                    other = rel['target'] if rel['source'] == concept_text else rel['source']
                    
                    # Texto según tipo de relación
                    if rel['type'] == 'hypernym':
                        relation_texts.append(f"es un tipo de {other}")
                    elif rel['type'] == 'hyponym':
                        relation_texts.append(f"incluye a {other}")
                    elif rel['type'] == 'semantic_similarity':
                        relation_texts.append(f"está relacionado con {other}")
                    else:
                        relation_texts.append(f"co-ocurre con {other}")
                
                if relation_texts:
                    description += f" y {', '.join(relation_texts)}"
            
            lines.append(description + ".")
        
        return "\n".join(lines)
```

### 3.5 Función Principal e Integración con IANAE

```python
def integrate_with_ianae(sistema, text, max_concepts=30, extraction_params=None):
    """
    Integra el procesamiento NLP con el sistema IANAE
    
    Args:
        sistema: Instancia de ConceptosDifusos
        text: Texto para procesar
        max_concepts: Número máximo de conceptos a extraer
        extraction_params: Parámetros adicionales para la extracción
        
    Returns:
        Tuple de (conceptos_añadidos, relaciones_creadas)
    """
    if extraction_params is None:
        extraction_params = {}
        
    # Inicializar procesadores
    text_processor = TextProcessor(
        language=extraction_params.get('language', 'es'),
        use_gpu=extraction_params.get('use_gpu', False)
    )
    
    concept_extractor = ConceptExtractor(text_processor)
    relation_detector = RelationDetector(text_processor)
    
    # Extraer conceptos
    concepts = concept_extractor.extract_concepts(
        text, 
        max_concepts=max_concepts,
        min_word_length=extraction_params.get('min_word_length', 3)
    )
    
    # Detectar relaciones
    relations = relation_detector.detect_relationships(
        concepts, 
        text=text
    )
    
    # Integrar con IANAE
    conceptos_añadidos = []
    for concept in concepts:
        nombre = concept['text']
        if nombre not in sistema.conceptos:
            # Usar embedding como vector base
            vector = concept['embedding']
            
            # Normalizar vector si es necesario
            if vector is not None:
                vector = vector / np.linalg.norm(vector)
                
                # Añadir concepto
                sistema.añadir_concepto(nombre, atributos=vector)
                conceptos_añadidos.append(nombre)
    
    # Crear relaciones
    relaciones_creadas = 0
    for relation in relations:
        source = relation['source']
        target = relation['target']
        strength = relation['strength']
        
        if source in sistema.conceptos and target in sistema.conceptos:
            if not sistema.grafo.has_edge(source, target):
                sistema.relacionar(source, target, fuerza=strength)
                relaciones_creadas += 1
    
    return conceptos_añadidos, relaciones_creadas
```

## 4. Modificación de Módulos Existentes

### 4.1 Actualización de `emergente.py`

Es necesario modificar el método `cargar_conceptos_desde_texto()` en la clase `PensamientoEmergente` para usar la nueva interfaz NLP:

```python
def cargar_conceptos_desde_texto(self, texto, max_conceptos=30, usar_nlp_avanzado=True):
    """
    Extrae conceptos desde un texto y los añade al sistema
    
    Args:
        texto: Texto de donde extraer conceptos
        max_conceptos: Número máximo de conceptos a extraer
        usar_nlp_avanzado: Si se debe usar la interfaz NLP avanzada
        
    Returns:
        Lista de conceptos extraídos
    """
    if usar_nlp_avanzado:
        try:
            from nlp_interface import integrate_with_ianae
            conceptos_añadidos, _ = integrate_with_ianae(
                self.sistema, 
                texto, 
                max_concepts=max_conceptos
            )
            return conceptos_añadidos
        except ImportError:
            print("Interfaz NLP avanzada no disponible. Usando método básico.")
            # Continuar con método básico
    
    # Método básico (existente)
    # Preprocesamiento simple
    texto = texto.lower()
    for c in ".,;:!?()[]{}\"'":
        texto = texto.replace(c, ' ')
        
    palabras = texto.split()
    
    # Filtrar palabras comunes (simplificado)
    stop_words = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "a", "ante", "bajo",
        "con", "de", "desde", "en", "entre", "hacia", "hasta", "para", "por", "según", "sin",
        "sobre", "tras", "que", "como", "cuando", "donde", "si", "no", "al", "del", "lo", "su",
        "sus", "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "mi", "tu", "su",
        "es", "son", "era", "eran", "sido", "fue", "ha", "han", "he", "hemos"
    }
    
    palabras_filtradas = [p for p in palabras if p not in stop_words and len(p) > 3]
    
    # Contar frecuencias
    frecuencias = {}
    for p in palabras_filtradas:
        frecuencias[p] = frecuencias.get(p, 0) + 1
        
    # Ordenar por frecuencia
    palabras_ordenadas = sorted(frecuencias.items(), key=lambda x: x[1], reverse=True)
    
    # Tomar las más frecuentes hasta max_conceptos
    conceptos_extraidos = [p for p, f in palabras_ordenadas[:max_conceptos]]
    
    # Añadir al sistema
    conceptos_añadidos = []
    for c in conceptos_extraidos:
        if c not in self.sistema.conceptos:
            self.sistema.añadir_concepto(c)
            conceptos_añadidos.append(c)
            
    # Crear relaciones basadas en co-ocurrencia en el texto
    ventana = 5  # Palabras cercanas en el texto
    for i, p1 in enumerate(palabras_filtradas):
        if p1 in self.sistema.conceptos:
            # Buscar palabras cercanas
            inicio = max(0, i - ventana)
            fin = min(len(palabras_filtradas), i + ventana + 1)
            
            for j in range(inicio, fin):
                if i != j:  # No relacionar consigo misma
                    p2 = palabras_filtradas[j]
                    if p2 in self.sistema.conceptos:
                        # Relacionar con fuerza inversamente proporcional a la distancia
                        distancia = abs(i - j)
                        fuerza = 1.0 / max(1, distancia)
                        
                        # Relacionar conceptos
                        self.sistema.relacionar(p1, p2, fuerza=fuerza)
    
    return conceptos_añadidos
```

### 4.2 Actualización de `main.py`

Para proporcionar una interfaz de usuario para las nuevas capacidades NLP, se debe añadir una nueva opción al menú principal en `main.py`:

```python
def main():
    # ... Código existente ...
    
    # Mostrar menú principal
    while True:
        print("\nMenú Principal de IANAE")
        print("-" * 30)
        print("1. Visualizar estado actual")
        # ... Opciones existentes ...
        print("9. Importar conceptos desde texto")  # Nueva opción
        print("10. Procesar documento completo")    # Nueva opción
        print("11. Salir")
        
        opcion = input("\nSelecciona una opción: ")
        
        try:
            # ... Opciones existentes ...
            
            elif opcion == '9':
                # Importar conceptos desde texto
                print("Introduce texto para extraer conceptos (termina con línea vacía):")
                lineas = []
                while True:
                    linea = input()
                    if not linea:
                        break
                    lineas.append(linea)
                    
                texto = "\n".join(lineas)
                if not texto:
                    print("Texto vacío. Operación cancelada.")
                    continue
                    
                # Preguntar si usar NLP avanzado
                usar_nlp_avanzado = input("¿Usar procesamiento NLP avanzado? (s/n): ").lower().startswith('s')
                
                # Extraer conceptos
                conceptos = pensamiento.cargar_conceptos_desde_texto(
                    texto, 
                    max_conceptos=30, 
                    usar_nlp_avanzado=usar_nlp_avanzado
                )
                
                print(f"Se han añadido {len(conceptos)} nuevos conceptos:")
                for c in conceptos:
                    print(f"  - {c}")
                    
                if input("¿Visualizar red actualizada? (s/n): ").lower().startswith('s'):
                    sistema.visualizar()
                    
            elif opcion == '10':
                # Procesar documento completo
                ruta = input("Ruta del documento a procesar: ")
                if not os.path.exists(ruta):
                    print(f"El archivo {ruta} no existe")
                    continue
                    
                try:
                    from nlp_interface import process_document_to_ianae
                    
                    # Procesar documento
                    resultados = process_document_to_ianae(sistema, ruta)
                    
                    print(f"Documento procesado. Idioma detectado: {resultados['language']}")
                    print(f"Conceptos añadidos: {resultados['conceptos_añadidos']}")
                    print(f"Relaciones creadas: {resultados['relaciones_creadas']}")
                    
                    # Mostrar resumen
                    print("\nResumen conceptual:")
                    print(resultados['summary'])
                    
                    if input("¿Visualizar red actualizada? (s/n): ").lower().startswith('s'):
                        sistema.visualizar()
                        
                except ImportError:
                    print("Módulo de NLP avanzado no disponible.")
                
            elif opcion == '11':
                # Salir
                if input("¿Guardar antes de salir? (s/n): ").lower().startswith('s'):
                    sistema.guardar('ianae_estado.json')
                    print("Sistema guardado")
                
                print("¡Hasta pronto!")
                break
            
            # ... 
        # ...
```

## 5. Ejemplos de Uso

### 5.1 Ejemplo Básico: Extracción de Conceptos

```python
from nucleo import ConceptosDifusos
from nlp_interface import integrate_with_ianae

# Crear sistema IANAE
sistema = ConceptosDifusos(dim_vector=15)

# Texto de ejemplo
texto = """
La inteligencia emergente es un fenómeno donde comportamientos complejos surgen de sistemas 
simples interconectados. A diferencia de los sistemas algorítmicos tradicionales, los sistemas 
emergentes no siguen reglas rígidas predefinidas, sino que desarrollan comportamientos adaptativos.
"""

# Integrar con IANAE
conceptos_añadidos, relaciones_creadas = integrate_with_ianae(sistema, texto)

print(f"Conceptos añadidos: {conceptos_añadidos}")
print(f"Relaciones creadas: {relaciones_creadas}")

# Visualizar el resultado
sistema.visualizar()
```

### 5.2 Ejemplo Avanzado: Procesamiento de Documento

```python
from nucleo import ConceptosDifusos
from nlp_interface import TextProcessor, ConceptExtractor, RelationDetector, DocumentProcessor

# Crear sistema IANAE
sistema = ConceptosDifusos(dim_vector=25)

# Inicializar procesadores
text_processor = TextProcessor(language="es")
concept_extractor = ConceptExtractor(text_processor)
relation_detector = RelationDetector(text_processor)
document_processor = DocumentProcessor(text_processor, concept_extractor, relation_detector)

# Leer documento
with open("documento.txt", "r", encoding="utf-8") as f:
    texto = f.read()

# Procesar documento
resultados = document_processor.process_document(texto, max_concepts=50)

# Mostrar resumen conceptual
print("Resumen conceptual:")
print(resultados['summary'])

# Visualizar jerarquía de conceptos
print("\nJerarquía de conceptos:")
for raiz in resultados['hierarchy']:
    print_hierarchy(raiz)

# Integrar con IANAE
for concept in resultados['concepts']:
    if concept['text'] not in sistema.conceptos:
        # Usar embedding como vector base
        vector = concept['embedding']
        if vector is not None:
            sistema.añadir_concepto(concept['text'], atributos=vector)

# Crear relaciones
for relation in resultados['relations']:
    source = relation['source']
    target = relation['target']
    if source in sistema.conceptos and target in sistema.conceptos:
        sistema.relacionar(source, target, fuerza=relation['strength'])

# Visualizar el resultado
sistema.visualizar()
```

### 5.3 Ejemplo de Comparación Multilingüe

```python
from nucleo import ConceptosDifusos
from nlp_interface import TextProcessor, ConceptExtractor

# Crear sistemas IANAE para diferentes idiomas
sistema_es = ConceptosDifusos(dim_vector=15)
sistema_en = ConceptosDifusos(dim_vector=15)

# Textos equivalentes en español e inglés
texto_es = """
La inteligencia artificial es un campo de la informática que busca crear máquinas
capaces de realizar tareas que normalmente requieren inteligencia humana.
"""

texto_en = """
Artificial intelligence is a field of computer science that seeks to create machines
capable of performing tasks that normally require human intelligence.
"""

# Procesar textos en diferentes idiomas
processor_es = TextProcessor(language="es")
processor_en = TextProcessor(language="en")

extractor_es = ConceptExtractor(processor_es)
extractor_en = ConceptExtractor(processor_en)

# Extraer conceptos
conceptos_es = extractor_es.extract_concepts(texto_es)
conceptos_en = extractor_en.extract_concepts(texto_en)

# Comparar embeddings de conceptos equivalentes
for c_es in conceptos_es:
    for c_en in conceptos_en:
        # Calcular similitud entre concepto en español y su equivalente en inglés
        if processor_es._cosine_similarity(c_es['embedding'], c_en['embedding']) > 0.8:
            print(f"Concepto equivalente: '{c_es['text']}' (ES) = '{c_en['text']}' (EN)")
```

## 6. Consideraciones de Implementación

### 6.1 Gestión de Dependencias

La integración NLP requiere varias bibliotecas externas. Se recomienda instalarlas en un entorno virtual:

```bash
python -m venv ianae_env
source ianae_env/bin/activate  # En Windows: ianae_env\Scripts\activate
pip install -r requirements_nlp.txt
```

Contenido de `requirements_nlp.txt`:
```
transformers==4.34.0
spacy==3.7.1
sentence-transformers==2.2.2
nltk==3.8.1
langdetect==1.0.9
networkx==3.1
torch==2.0.1
numpy==1.24.3
```

### 6.2 Gestión de Modelos

Los modelos de lenguaje se descargarán automáticamente la primera vez que se utilicen, pero esto puede llevar tiempo. Una alternativa es descargarlos previamente:

```python
# Script para descargar modelos necesarios
import nltk
import spacy
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

# Descargar recursos NLTK
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')
nltk.download('omw-1.4')

# Descargar modelos spaCy
spacy.cli.download('es_core_news_md')
spacy.cli.download('en_core_web_md')

# Descargar modelo de embeddings
model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v1')
```

### 6.3 Consideraciones de Rendimiento

- **Caché de Embeddings**: Implementar persistencia para la caché de embeddings.
- **Procesamiento por Lotes**: Procesar conceptos en lotes para mejorar rendimiento con GPU.
- **Paralelización**: Utilizar procesamiento paralelo para documentos grandes.

## 7. Próximos Pasos

### 7.1 Mejoras a Corto Plazo

- **Soporte para más idiomas**: Ampliar modelos disponibles para más idiomas.
- **Extracción temporal**: Detectar relaciones temporales entre conceptos.
- **Desambiguación**: Mejorar la desambiguación de conceptos por contexto.

### 7.2 Integraciones Futuras

- **Procesamiento Multimodal**: Integrar con procesamiento de imágenes.
- **API Web**: Crear una API REST para procesar textos remotamente.
- **Análisis de Sentimiento**: Incorporar análisis de sentimiento para conceptos.

## 8. Conclusión

La integración de técnicas modernas de NLP mejora significativamente la capacidad de IANAE para procesar y comprender textos. El nuevo módulo `nlp_interface.py` proporciona una arquitectura extensible que permite:

1. Extraer conceptos más significativos y relevantes
2. Representar conceptos con embeddings semánticamente ricos
3. Detectar relaciones semánticas avanzadas
4. Procesar textos en múltiples idiomas
5. Manejar documentos completos manteniendo el contexto

Esta mejora posiciona a IANAE como un sistema capaz de analizar y comprender textos de manera más similar a la humana, permitiendo una representación más rica y matizada del conocimiento textual.
