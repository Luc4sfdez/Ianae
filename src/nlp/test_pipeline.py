# test_pipeline.py - Tests del pipeline NLP → IANAE
# Ejecutar: python -m pytest src/nlp/test_pipeline.py -v
# O directamente: python src/nlp/test_pipeline.py

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nlp.extractor import ExtractorConceptos
from nlp.pipeline import PipelineNLP, ReduccionDimensional


def test_extraccion_basica():
    """Test: extracción básica funciona sin dependencias externas."""
    extractor = ExtractorConceptos(modo="basico")
    assert extractor.modo == "basico"

    texto = "Python es un lenguaje de programación muy utilizado en inteligencia artificial"
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=5)

    assert len(conceptos) > 0
    assert all("nombre" in c for c in conceptos)
    assert all("relevancia" in c for c in conceptos)
    assert all(0 <= c["relevancia"] <= 1 for c in conceptos)
    print(f"  [OK] Extraídos {len(conceptos)} conceptos: {[c['nombre'] for c in conceptos]}")


def test_embedding_fallback():
    """Test: generación de embedding funciona en modo fallback."""
    extractor = ExtractorConceptos(modo="basico")
    embedding = extractor.generar_embedding("inteligencia")

    assert isinstance(embedding, np.ndarray)
    assert len(embedding) == 15  # dim por defecto en fallback
    print(f"  [OK] Embedding generado: shape={embedding.shape}")

    # Mismo texto debe dar mismo embedding (determinista)
    embedding2 = extractor.generar_embedding("inteligencia")
    np.testing.assert_array_equal(embedding, embedding2)
    print("  [OK] Embeddings deterministas")


def test_relaciones_coocurrencia():
    """Test: detección de relaciones por co-ocurrencia."""
    extractor = ExtractorConceptos(modo="basico")
    texto = "Python y numpy trabajan juntos. Python usa numpy para vectores."
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=5)
    relaciones = extractor.extraer_relaciones(texto, conceptos)

    print(f"  [OK] Relaciones detectadas: {len(relaciones)}")
    for c1, c2, peso in relaciones[:3]:
        print(f"       {c1} ↔ {c2} = {peso}")


def test_reduccion_dimensional():
    """Test: reducción de 384 dim a 15 dim."""
    reductor = ReduccionDimensional(dim_target=15)

    # Simular embeddings de sentence-transformers (384 dim)
    rng = np.random.RandomState(42)
    embeddings = rng.normal(0, 1, (20, 384))

    reducidos = reductor.ajustar_y_transformar(embeddings)
    assert reducidos.shape == (20, 15)

    # Verificar normalización
    for v in reducidos:
        norma = np.linalg.norm(v)
        assert abs(norma - 1.0) < 0.01, f"Vector no normalizado: norma={norma}"

    print(f"  [OK] Reducción 384→15: shape={reducidos.shape}")


def test_reduccion_dimensional_pocos_datos():
    """Test: reducción funciona con pocos datos (proyección aleatoria)."""
    reductor = ReduccionDimensional(dim_target=15)

    # Solo 3 samples (menos que dim_target)
    rng = np.random.RandomState(42)
    embeddings = rng.normal(0, 1, (3, 384))

    reducidos = reductor.ajustar_y_transformar(embeddings)
    assert reducidos.shape == (3, 15)
    print(f"  [OK] Reducción con pocos datos: shape={reducidos.shape}")


def test_reduccion_no_necesaria():
    """Test: si la dimensión ya es correcta, no reduce."""
    reductor = ReduccionDimensional(dim_target=15)
    embedding = np.random.normal(0, 1, 15)
    resultado = reductor.transformar(embedding)
    assert len(resultado) == 15
    print("  [OK] Sin reducción necesaria para dim=15")


def test_pipeline_sin_sistema():
    """Test: pipeline funciona sin sistema IANAE (standalone)."""
    pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")

    texto = "La inteligencia artificial y el aprendizaje automático transforman la tecnología"
    resultado = pipeline.procesar(texto, max_conceptos=5)

    assert "conceptos" in resultado
    assert "relaciones" in resultado
    assert "vectores_reducidos" in resultado
    assert len(resultado["conceptos"]) > 0

    print(f"  [OK] Pipeline standalone: {len(resultado['conceptos'])} conceptos")
    for c in resultado["conceptos"]:
        print(f"       {c['nombre']} (relevancia={c['relevancia']})")


def test_pipeline_con_sistema():
    """Test: pipeline inyecta conceptos en ConceptosLucas."""
    try:
        from core.nucleo import ConceptosLucas
    except ImportError:
        print("  [SKIP] nucleo.py no disponible en path")
        return

    sistema = ConceptosLucas(dim_vector=15)
    sistema.crear_conceptos_lucas()
    conceptos_antes = len(sistema.conceptos)

    pipeline = PipelineNLP(sistema_ianae=sistema, modo_nlp="basico")

    texto = "El procesamiento de lenguaje natural permite analizar textos automáticamente"
    resultado = pipeline.procesar(texto, max_conceptos=5, categoria="nlp_extraidos")

    conceptos_despues = len(sistema.conceptos)
    nuevos = conceptos_despues - conceptos_antes

    assert nuevos > 0, "No se inyectaron conceptos"
    assert "nlp_extraidos" in sistema.categorias

    print(f"  [OK] Inyección en IANAE: {conceptos_antes}→{conceptos_despues} (+{nuevos})")
    print(f"       Categoría nlp_extraidos: {sistema.categorias['nlp_extraidos']}")


def test_pipeline_batch():
    """Test: procesamiento batch de múltiples textos."""
    pipeline = PipelineNLP(sistema_ianae=None, modo_nlp="basico")

    textos = [
        "Python es popular en ciencia de datos",
        "OpenCV procesa imágenes y detecta patrones",
        "Docker facilita el despliegue de aplicaciones"
    ]

    resultados = pipeline.procesar_batch(textos, max_conceptos=3)
    assert len(resultados) == 3
    assert all(len(r["conceptos"]) > 0 for r in resultados)

    print(f"  [OK] Batch procesado: {len(resultados)} textos")


if __name__ == "__main__":
    tests = [
        ("Extracción básica", test_extraccion_basica),
        ("Embedding fallback", test_embedding_fallback),
        ("Relaciones co-ocurrencia", test_relaciones_coocurrencia),
        ("Reducción dimensional", test_reduccion_dimensional),
        ("Reducción pocos datos", test_reduccion_dimensional_pocos_datos),
        ("Reducción no necesaria", test_reduccion_no_necesaria),
        ("Pipeline sin sistema", test_pipeline_sin_sistema),
        ("Pipeline con sistema", test_pipeline_con_sistema),
        ("Pipeline batch", test_pipeline_batch),
    ]

    print("=" * 60)
    print("  TEST SUITE: Pipeline NLP → IANAE")
    print("=" * 60)

    passed = 0
    failed = 0

    for nombre, test_fn in tests:
        print(f"\n▶ {nombre}...")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  RESULTADOS: {passed} passed, {failed} failed / {len(tests)} total")
    print(f"{'=' * 60}")
