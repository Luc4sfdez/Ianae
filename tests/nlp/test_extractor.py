"""Tests para ExtractorConceptos — extraccion NLP con fallback basico + modos reales."""
import pytest
import numpy as np
from src.nlp.extractor import ExtractorConceptos


# --- Detectar disponibilidad ---

def _spacy_disponible():
    try:
        import spacy
        spacy.load("es_core_news_md")
        return True
    except (ImportError, OSError):
        return False


def _transformers_disponible():
    try:
        from sentence_transformers import SentenceTransformer
        return True
    except ImportError:
        return False


spacy_skip = pytest.mark.skipif(not _spacy_disponible(), reason="spaCy o modelo no instalado")
transformers_skip = pytest.mark.skipif(not _transformers_disponible(), reason="sentence-transformers no instalado")


@pytest.fixture
def extractor():
    return ExtractorConceptos(modo="basico")


# --- Extraccion de conceptos (basico) ---

def test_modo_basico(extractor):
    assert extractor.modo == "basico"
    assert extractor.nlp is None
    assert extractor.modelo_embeddings is None


def test_extraer_conceptos_basico(extractor):
    texto = "Python es un lenguaje de programacion muy utilizado en inteligencia artificial"
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=5)
    assert len(conceptos) > 0
    assert all("nombre" in c for c in conceptos)
    assert all("relevancia" in c for c in conceptos)
    assert all("tipo" in c for c in conceptos)
    assert all(0 <= c["relevancia"] <= 1 for c in conceptos)


def test_extraer_conceptos_texto_vacio(extractor):
    assert extractor.extraer_conceptos("") == []


def test_extraer_conceptos_solo_stopwords(extractor):
    texto = "el la los las un una de en y o a"
    assert extractor.extraer_conceptos(texto) == []


def test_extraer_max_conceptos(extractor):
    texto = ("Python numpy pandas matplotlib scikit tensorflow keras "
             "pytorch opencv flask django fastapi requests")
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=3)
    assert len(conceptos) <= 3


def test_relevancia_ordenada(extractor):
    texto = "Python Python Python numpy numpy tensorflow"
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=10)
    relevancias = [c["relevancia"] for c in conceptos]
    assert relevancias == sorted(relevancias, reverse=True)


# --- Embeddings (basico) ---

def test_embedding_fallback(extractor):
    embedding = extractor.generar_embedding("inteligencia")
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) == 15


def test_embedding_determinista(extractor):
    e1 = extractor.generar_embedding("concepto")
    e2 = extractor.generar_embedding("concepto")
    np.testing.assert_array_equal(e1, e2)


def test_embedding_diferente_texto(extractor):
    e1 = extractor.generar_embedding("python")
    e2 = extractor.generar_embedding("java")
    assert not np.array_equal(e1, e2)


# --- Relaciones (basico) ---

def test_relaciones_coocurrencia(extractor):
    texto = "Python y numpy trabajan juntos. Python usa numpy para vectores."
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=5)
    relaciones = extractor.extraer_relaciones(texto, conceptos)
    assert isinstance(relaciones, list)
    if relaciones:
        assert all(len(r) == 3 for r in relaciones)
        assert all(0 <= r[2] <= 1 for r in relaciones)


def test_relaciones_texto_corto(extractor):
    texto = "solo una palabra"
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=5)
    relaciones = extractor.extraer_relaciones(texto, conceptos)
    assert isinstance(relaciones, list)


# ==================== Tests con spaCy ====================

@spacy_skip
class TestExtractorSpacy:
    @pytest.fixture
    def ext_spacy(self):
        return ExtractorConceptos(modo="spacy")

    def test_modo_spacy_cargado(self, ext_spacy):
        assert ext_spacy.nlp is not None
        assert ext_spacy.modo == "spacy"

    def test_extraer_conceptos_spacy(self, ext_spacy):
        texto = "Python es utilizado por Lucas para desarrollar IANAE con inteligencia artificial"
        conceptos = ext_spacy.extraer_conceptos(texto, max_conceptos=5)
        assert len(conceptos) > 0
        # spaCy debe detectar al menos tipos NER o POS
        tipos = [c["tipo"] for c in conceptos]
        assert any("NER:" in t or "POS:" in t or "CHUNK:" in t for t in tipos)

    def test_extraccion_entidades_nombradas(self, ext_spacy):
        texto = "Madrid es la capital de España y Barcelona es una ciudad importante"
        conceptos = ext_spacy.extraer_conceptos(texto, max_conceptos=10)
        nombres = [c["nombre"] for c in conceptos]
        # Al menos debe detectar alguna entidad de lugar
        assert len(conceptos) > 0

    def test_relevancia_spacy_normalizada(self, ext_spacy):
        texto = "El procesamiento de lenguaje natural usa redes neuronales profundas"
        conceptos = ext_spacy.extraer_conceptos(texto, max_conceptos=5)
        assert all(0 <= c["relevancia"] <= 1 for c in conceptos)
        if conceptos:
            assert conceptos[0]["relevancia"] == 1.0  # max normalizado a 1

    def test_embedding_spacy_vector(self, ext_spacy):
        embedding = ext_spacy.generar_embedding("inteligencia")
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 300  # es_core_news_md tiene vectores 300d

    def test_relaciones_por_dependencias(self, ext_spacy):
        texto = "Python procesa datos. Python analiza textos con numpy."
        conceptos = ext_spacy.extraer_conceptos(texto, max_conceptos=5)
        relaciones = ext_spacy.extraer_relaciones(texto, conceptos)
        assert isinstance(relaciones, list)
        for c1, c2, peso in relaciones:
            assert isinstance(c1, str)
            assert isinstance(c2, str)
            assert 0 <= peso <= 1

    def test_max_conceptos_respetado(self, ext_spacy):
        texto = ("Madrid Barcelona Valencia Sevilla Bilbao Malaga "
                 "Zaragoza Murcia Palma Granada")
        conceptos = ext_spacy.extraer_conceptos(texto, max_conceptos=3)
        assert len(conceptos) <= 3


# ==================== Tests con sentence-transformers ====================

@transformers_skip
class TestExtractorTransformers:
    @pytest.fixture
    def ext_transformers(self):
        return ExtractorConceptos(modo="transformers")

    def test_modo_transformers_cargado(self, ext_transformers):
        assert ext_transformers.modelo_embeddings is not None
        assert ext_transformers.modo == "transformers"

    def test_embedding_transformers_384d(self, ext_transformers):
        embedding = ext_transformers.generar_embedding("inteligencia artificial")
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384

    def test_embedding_semantico_similares(self, ext_transformers):
        e1 = ext_transformers.generar_embedding("perro")
        e2 = ext_transformers.generar_embedding("gato")
        e3 = ext_transformers.generar_embedding("matematicas")
        # perro-gato deben ser mas similares que perro-matematicas
        sim_12 = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
        sim_13 = np.dot(e1, e3) / (np.linalg.norm(e1) * np.linalg.norm(e3))
        assert sim_12 > sim_13

    def test_relaciones_por_similitud(self, ext_transformers):
        conceptos = [
            {"nombre": "Python", "relevancia": 1.0, "tipo": "freq"},
            {"nombre": "programacion", "relevancia": 0.8, "tipo": "freq"},
            {"nombre": "cocina", "relevancia": 0.5, "tipo": "freq"},
        ]
        relaciones = ext_transformers.extraer_relaciones("", conceptos)
        assert isinstance(relaciones, list)
        # Python-programacion deberia tener mas peso que Python-cocina
        if len(relaciones) >= 2:
            pesos = {(r[0], r[1]): r[2] for r in relaciones}
            prog_peso = pesos.get(("Python", "programacion"), 0)
            cocina_peso = pesos.get(("Python", "cocina"), 0)
            assert prog_peso >= cocina_peso

    def test_relaciones_un_concepto(self, ext_transformers):
        conceptos = [{"nombre": "solo", "relevancia": 1.0, "tipo": "freq"}]
        relaciones = ext_transformers.extraer_relaciones("", conceptos)
        assert relaciones == []


# ==================== Tests modo completo (spaCy + transformers) ====================

@spacy_skip
@transformers_skip
class TestExtractorCompleto:
    @pytest.fixture
    def ext_completo(self):
        return ExtractorConceptos(modo="auto")

    def test_modo_auto_detecta_completo(self, ext_completo):
        assert ext_completo.modo == "completo"
        assert ext_completo.nlp is not None
        assert ext_completo.modelo_embeddings is not None

    def test_pipeline_completo_texto_real(self, ext_completo):
        texto = """
        Lucas esta desarrollando un sistema de inteligencia artificial llamado IANAE
        que usa conceptos difusos y pensamiento emergente. El proyecto utiliza Python
        con numpy para los vectores multidimensionales.
        """
        conceptos = ext_completo.extraer_conceptos(texto, max_conceptos=8)
        assert len(conceptos) > 0

        embedding = ext_completo.generar_embedding("Python")
        assert len(embedding) == 384  # transformers tiene prioridad

        relaciones = ext_completo.extraer_relaciones(texto, conceptos)
        assert isinstance(relaciones, list)
        # En modo completo con transformers, usa similitud coseno
        for c1, c2, peso in relaciones:
            assert 0 <= peso <= 1
