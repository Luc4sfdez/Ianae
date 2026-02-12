"""Tests para PipelineNLP y ReduccionDimensional."""
import pytest
import numpy as np
from src.nlp.pipeline import PipelineNLP, ReduccionDimensional
from src.core.nucleo import ConceptosLucas


# --- ReduccionDimensional ---

class TestReduccionDimensional:
    def test_reduccion_384_a_15(self):
        reductor = ReduccionDimensional(dim_target=15)
        rng = np.random.RandomState(42)
        embeddings = rng.normal(0, 1, (20, 384))
        reducidos = reductor.ajustar_y_transformar(embeddings)
        assert reducidos.shape == (20, 15)

    def test_vectores_normalizados(self):
        reductor = ReduccionDimensional(dim_target=15)
        rng = np.random.RandomState(42)
        embeddings = rng.normal(0, 1, (20, 384))
        reducidos = reductor.ajustar_y_transformar(embeddings)
        for v in reducidos:
            norma = np.linalg.norm(v)
            assert abs(norma - 1.0) < 0.01

    def test_pocos_datos_proyeccion_aleatoria(self):
        reductor = ReduccionDimensional(dim_target=15)
        rng = np.random.RandomState(42)
        embeddings = rng.normal(0, 1, (3, 384))
        reducidos = reductor.ajustar_y_transformar(embeddings)
        assert reducidos.shape == (3, 15)

    def test_sin_reduccion_dim_correcta(self):
        reductor = ReduccionDimensional(dim_target=15)
        embedding = np.random.normal(0, 1, 15)
        resultado = reductor.transformar(embedding)
        assert len(resultado) == 15

    def test_padding_dim_menor(self):
        reductor = ReduccionDimensional(dim_target=15)
        embedding = np.ones(5)
        resultado = reductor.transformar(embedding)
        assert len(resultado) == 15

    def test_ajustar_y_transformar_idempotente(self):
        reductor = ReduccionDimensional(dim_target=10)
        rng = np.random.RandomState(42)
        embeddings = rng.normal(0, 1, (15, 100))
        r1 = reductor.ajustar_y_transformar(embeddings)
        # Transformar individual despues de ajustar
        r2 = reductor.transformar(embeddings[0])
        np.testing.assert_array_almost_equal(r1[0], r2)


# --- PipelineNLP ---

class TestPipelineNLP:
    def test_pipeline_sin_sistema(self):
        pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")
        texto = "La inteligencia artificial transforma la tecnologia moderna"
        resultado = pipeline.procesar(texto, max_conceptos=5)
        assert "conceptos" in resultado
        assert "relaciones" in resultado
        assert "vectores_reducidos" in resultado
        assert len(resultado["conceptos"]) > 0

    def test_pipeline_texto_vacio(self):
        pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")
        resultado = pipeline.procesar("")
        assert resultado["conceptos"] == []

    def test_pipeline_cache_embeddings(self):
        pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")
        pipeline.procesar("Python es util para datos", max_conceptos=3)
        assert len(pipeline._embeddings_cache) > 0
        # Segundo procesamiento usa cache
        cache_size_antes = len(pipeline._embeddings_cache)
        pipeline.procesar("Python es genial para datos", max_conceptos=3)
        # Conceptos repetidos deben venir del cache
        assert len(pipeline._embeddings_cache) >= cache_size_antes

    def test_pipeline_batch(self):
        pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")
        textos = [
            "Python es popular en ciencia de datos",
            "OpenCV procesa imagenes y detecta patrones",
            "Docker facilita el despliegue de aplicaciones",
        ]
        resultados = pipeline.procesar_batch(textos, max_conceptos=3)
        assert len(resultados) == 3
        assert all(len(r["conceptos"]) > 0 for r in resultados)

    def test_dim_reducida_correcta(self):
        pipeline = PipelineNLP(sistema_ianae=None, dim_vector=10, modo_nlp="basico")
        resultado = pipeline.procesar("Aprendizaje automatico con redes neuronales")
        assert resultado["dim_reducida"] == 10
        for vec in resultado["vectores_reducidos"].values():
            assert len(vec) == 10


# --- Integracion con nucleo ---

class TestPipelineIntegracion:
    def test_inyectar_conceptos_en_nucleo(self):
        sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        conceptos_antes = len(sistema.conceptos)

        pipeline = PipelineNLP(sistema_ianae=sistema, modo_nlp="basico")
        texto = "El procesamiento de lenguaje natural permite analizar textos automaticamente"
        resultado = pipeline.procesar(texto, max_conceptos=5, categoria="nlp_test")

        conceptos_despues = len(sistema.conceptos)
        assert conceptos_despues > conceptos_antes

    def test_categoria_registrada(self):
        sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        pipeline = PipelineNLP(sistema_ianae=sistema, modo_nlp="basico")
        pipeline.procesar("inteligencia artificial emergente", categoria="mi_categoria")
        assert "mi_categoria" in sistema.categorias

    def test_relaciones_inyectadas(self):
        sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        pipeline = PipelineNLP(sistema_ianae=sistema, modo_nlp="basico")
        texto = "Python y numpy trabajan juntos. Python usa numpy para vectores numpy."
        pipeline.procesar(texto, max_conceptos=5, umbral_relacion=0.1)
        # Debe haber al menos algun concepto inyectado
        assert len(sistema.conceptos) > 0

    def test_activar_concepto_nlp(self):
        """Conceptos NLP inyectados deben ser activables."""
        sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        pipeline = PipelineNLP(sistema_ianae=sistema, modo_nlp="basico")
        texto = "Python numpy vectores matrices algebra lineal"
        resultado = pipeline.procesar(texto, max_conceptos=5)

        # Tomar primer concepto inyectado y activarlo
        if resultado["conceptos"]:
            nombre = resultado["conceptos"][0]["nombre"]
            if nombre in sistema.conceptos:
                activaciones = sistema.activar(nombre, pasos=2)
                assert len(activaciones) > 0

    def test_vectores_dimension_correcta(self):
        """Vectores inyectados deben tener la dimension del sistema."""
        sistema = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        pipeline = PipelineNLP(sistema_ianae=sistema, modo_nlp="basico")
        pipeline.procesar("aprendizaje automatico profundo")

        for nombre, data in sistema.conceptos.items():
            assert len(data["actual"]) == 15, f"{nombre}: dim={len(data['actual'])}"
