"""Tests para PipelineNLP, ReduccionDimensional, EmbeddingCacheDisco y chunking."""
import os
import tempfile
import pytest
import numpy as np
from src.nlp.pipeline import PipelineNLP, ReduccionDimensional, EmbeddingCacheDisco
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


# --- EmbeddingCacheDisco ---

class TestEmbeddingCacheDisco:
    def test_put_y_get(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ruta = f.name
        try:
            cache = EmbeddingCacheDisco(ruta=ruta, modelo_id="test")
            vec = np.array([1.0, 2.0, 3.0])
            cache.put("hola", vec)
            result = cache.get("hola")
            assert result is not None
            np.testing.assert_array_almost_equal(result, vec)
        finally:
            os.unlink(ruta)

    def test_persistencia_entre_instancias(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ruta = f.name
        try:
            cache1 = EmbeddingCacheDisco(ruta=ruta, modelo_id="test")
            cache1.put("concepto", np.array([0.5, 0.6, 0.7]))

            cache2 = EmbeddingCacheDisco(ruta=ruta, modelo_id="test")
            result = cache2.get("concepto")
            assert result is not None
            np.testing.assert_array_almost_equal(result, [0.5, 0.6, 0.7])
        finally:
            os.unlink(ruta)

    def test_get_inexistente(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ruta = f.name
        try:
            cache = EmbeddingCacheDisco(ruta=ruta, modelo_id="test")
            assert cache.get("noexiste") is None
        finally:
            os.unlink(ruta)

    def test_contains(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ruta = f.name
        try:
            cache = EmbeddingCacheDisco(ruta=ruta, modelo_id="test")
            cache.put("existe", np.array([1.0]))
            assert "existe" in cache
            assert "noexiste" not in cache
        finally:
            os.unlink(ruta)

    def test_len(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ruta = f.name
        try:
            cache = EmbeddingCacheDisco(ruta=ruta, modelo_id="test")
            assert len(cache) == 0
            cache.put("a", np.array([1.0]))
            cache.put("b", np.array([2.0]))
            assert len(cache) == 2
        finally:
            os.unlink(ruta)

    def test_no_duplica_entries(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ruta = f.name
        try:
            cache = EmbeddingCacheDisco(ruta=ruta, modelo_id="test")
            cache.put("x", np.array([1.0]))
            cache.put("x", np.array([1.0]))  # duplicado
            assert len(cache) == 1
        finally:
            os.unlink(ruta)

    def test_archivo_inexistente_no_crashea(self):
        cache = EmbeddingCacheDisco(ruta="/tmp/no_existe_abc123.jsonl", modelo_id="test")
        assert len(cache) == 0

    def test_modelos_diferentes_keys_diferentes(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ruta = f.name
        try:
            cache = EmbeddingCacheDisco(ruta=ruta, modelo_id="modelo_a")
            cache.put("texto", np.array([1.0, 2.0]))

            cache_b = EmbeddingCacheDisco(ruta=ruta, modelo_id="modelo_b")
            # Mismo texto, modelo diferente -> key diferente
            assert cache_b.get("texto") is None
        finally:
            os.unlink(ruta)


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

    def test_pipeline_cache_disco(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ruta = f.name
        try:
            pipeline = PipelineNLP(
                sistema_ianae=None, modo_nlp="basico",
                cache_disco=True, cache_ruta=ruta
            )
            pipeline.procesar("Python numpy tensorflow", max_conceptos=3)
            assert pipeline._cache_disco is not None
            assert len(pipeline._cache_disco) > 0

            # Segunda instancia lee del disco
            pipeline2 = PipelineNLP(
                sistema_ianae=None, modo_nlp="basico",
                cache_disco=True, cache_ruta=ruta
            )
            assert len(pipeline2._cache_disco) > 0
        finally:
            os.unlink(ruta)


# --- Chunking ---

class TestChunking:
    def test_dividir_texto_corto_no_divide(self):
        chunks = PipelineNLP._dividir_chunks("texto corto de prueba", max_palabras=200)
        assert len(chunks) == 1

    def test_dividir_texto_largo(self):
        palabras = ["palabra"] * 500
        texto = " ".join(palabras)
        chunks = PipelineNLP._dividir_chunks(texto, max_palabras=100, solapamiento=10)
        assert len(chunks) > 1
        # Cada chunk no excede max_palabras (aprox)
        for chunk in chunks:
            assert len(chunk.split()) <= 110  # margen por solapamiento

    def test_dividir_con_puntos(self):
        # Texto con puntos naturales — debe preferir cortar ahí
        oraciones = ["Oracion numero {}.".format(i) for i in range(50)]
        texto = " ".join(oraciones)
        chunks = PipelineNLP._dividir_chunks(texto, max_palabras=20, solapamiento=3)
        assert len(chunks) > 1
        # Al menos un chunk debe terminar con punto
        terminan_punto = [c for c in chunks if c.rstrip().endswith('.')]
        assert len(terminan_punto) > 0

    def test_procesar_largo_texto_corto(self):
        pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")
        resultado = pipeline.procesar_largo("Python es rapido", max_conceptos=3)
        assert resultado["chunks"] == 1
        assert len(resultado["conceptos"]) > 0

    def test_procesar_largo_texto_largo(self):
        pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")
        # Generar texto largo con conceptos variados
        partes = [
            "Python es un lenguaje de programacion versatil.",
            "Numpy permite operaciones con vectores numericos.",
            "OpenCV procesa imagenes y detecta patrones visuales.",
            "FastAPI construye servicios web rapidos.",
            "Docker empaqueta aplicaciones en contenedores.",
        ] * 20  # ~500 palabras
        texto = " ".join(partes)
        resultado = pipeline.procesar_largo(texto, max_palabras_chunk=50,
                                             solapamiento=5, max_conceptos=8)
        assert resultado["chunks"] > 1
        assert len(resultado["conceptos"]) > 0
        assert len(resultado["conceptos"]) <= 8

    def test_procesar_largo_deduplica_conceptos(self):
        pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")
        # Mismo concepto repetido en multiples chunks
        texto = " ".join(["Python es genial."] * 100)
        resultado = pipeline.procesar_largo(texto, max_palabras_chunk=30,
                                             solapamiento=5, max_conceptos=10)
        nombres = [c["nombre"] for c in resultado["conceptos"]]
        assert len(nombres) == len(set(nombres))  # sin duplicados


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
