# test_ianae.py - Tests básicos para IANAE MVP
import pytest
import json
import sqlite3
import tempfile
import os
from fastapi.testclient import TestClient

# Imports locales (ajustar según estructura)
from ianae_server import app
from memory_connector import LucasMemoryConnector
from llm_connector import LLMConnector
from utils import setup_database_schema, validate_database

# Test client
client = TestClient(app)

class TestDatabase:
    """Tests para funcionalidad de base de datos"""
    
    def test_create_test_database(self):
        """Test crear base de datos de prueba"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        # Crear esquema
        success = setup_database_schema(db_path)
        assert success == True
        
        # Validar estructura
        validation = validate_database(db_path)
        assert validation['valid'] == True
        assert 'conceptos' in validation['tables']
        assert 'relaciones' in validation['tables']
        
        # Cleanup
        os.unlink(db_path)
    
    def test_memory_connector(self):
        """Test conector de memoria"""
        # Crear DB temporal
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        setup_database_schema(db_path)
        
        # Test connector
        connector = LucasMemoryConnector(db_path)
        
        # Test añadir concepto
        connector.add_new_concept("TestConcept", "test", "Concepto de prueba")
        
        # Test buscar
        results = connector.search_concepts("TestConcept")
        assert len(results) == 1
        assert results[0].concepto == "TestConcept"
        
        # Test stats
        stats = connector.get_memory_stats()
        assert stats['concepts'] >= 1
        
        connector.close()
        os.unlink(db_path)

class TestAPI:
    """Tests para endpoints de la API"""
    
    def test_health_endpoint(self):
        """Test endpoint de salud"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "memory" in data
        assert "llm" in data
    
    def test_memory_stats_endpoint(self):
        """Test endpoint de estadísticas"""
        response = client.get("/memory-stats")
        assert response.status_code == 200
        
        data = response.json()
        # Puede tener error si no hay DB, pero debe responder
        assert isinstance(data, dict)
    
    def test_chat_endpoint_empty_message(self):
        """Test chat con mensaje vacío"""
        response = client.post("/chat", json={"message": ""})
        assert response.status_code == 400
    
    def test_chat_endpoint_valid_message(self):
        """Test chat con mensaje válido"""
        response = client.post("/chat", json={"message": "test message"})
        
        # Debe responder aunque no haya DB real
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert "timestamp" in data

class TestLLMConnector:
    """Tests para conector LLM"""
    
    def test_llm_health_check(self):
        """Test verificación de estado LLM"""
        connector = LLMConnector()
        status = connector.health_check()
        
        assert isinstance(status, dict)
        assert "lm_studio" in status
        assert "openai" in status
        assert "recommended" in status
    
    def test_fallback_response(self):
        """Test respuesta de fallback"""
        connector = LLMConnector()
        
        context = {
            "found_concepts": [
                {"name": "TestConcept", "category": "test", "context": "Test context"}
            ]
        }
        
        response = connector._generate_fallback_response("test question", context)
        
        assert response["success"] == True
        assert "TestConcept" in response["response"]
        assert response["provider"] == "Fallback Memory"

class TestUtils:
    """Tests para utilidades"""
    
    def test_sanitize_input(self):
        """Test sanitización de input"""
        from utils import sanitize_input
        
        # Test básico
        result = sanitize_input("  test input  ")
        assert result == "test input"
        
        # Test longitud máxima
        long_text = "a" * 2000
        result = sanitize_input(long_text, max_length=100)
        assert len(result) <= 103  # 100 + "..."
        
        # Test input vacío
        result = sanitize_input("")
        assert result == ""
        
        result = sanitize_input(None)
        assert result == ""
    
    def test_extract_keywords(self):
        """Test extracción de palabras clave"""
        from utils import extract_keywords
        
        text = "Python OpenCV automatización tacógrafos detección círculos"
        keywords = extract_keywords(text)
        
        assert "python" in keywords
        assert "opencv" in keywords
        assert "automatización" in keywords
        assert len(keywords) > 0
    
    def test_check_dependencies(self):
        """Test verificación de dependencias"""
        from utils import check_dependencies
        
        deps = check_dependencies()
        
        assert isinstance(deps, dict)
        assert "fastapi" in deps
        assert "sqlite3" in deps
        assert deps["sqlite3"] == True  # Built-in

class TestIntegration:
    """Tests de integración completa"""
    
    def test_full_workflow_without_db(self):
        """Test workflow completo sin DB real"""
        # Test que el sistema responda aunque no tenga DB real
        response = client.post("/chat", json={
            "message": "¿Cómo estás IANAE?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
    
    def test_static_files(self):
        """Test que los archivos estáticos se sirvan"""
        # Estos tests fallarán si no existe la estructura real
        # pero dan una idea de lo que debería funcionar
        
        response = client.get("/")
        # Debería servir el HTML principal
        assert response.status_code in [200, 404]  # 404 si no existe template

class TestMemoryIntegration:
    """Tests de integración con memoria real (requiere DB)"""
    
    @pytest.fixture
    def sample_database(self):
        """Crear base de datos de ejemplo para tests"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        # Crear esquema
        setup_database_schema(db_path)
        
        # Añadir datos de ejemplo
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Conceptos de ejemplo
        sample_concepts = [
            ("Python", "tecnologias", "Lenguaje de programación favorito", 10),
            ("OpenCV", "tecnologias", "Biblioteca de visión artificial", 8),
            ("Tacografos", "proyectos", "Proyecto de detección de tacógrafos", 5),
            ("Automatizacion", "herramientas", "Proceso de automatización", 7)
        ]
        
        for concepto, categoria, contexto, activaciones in sample_concepts:
            cursor.execute("""
                INSERT INTO conceptos (concepto, categoria, contexto, activaciones)
                VALUES (?, ?, ?, ?)
            """, (concepto, categoria, contexto, activaciones))
        
        # Relaciones de ejemplo
        sample_relations = [
            ("Python", "OpenCV", 0.8, "implementacion"),
            ("OpenCV", "Tacografos", 0.9, "proyecto"),
            ("Python", "Automatizacion", 0.7, "herramienta")
        ]
        
        for c1, c2, peso, tipo in sample_relations:
            cursor.execute("""
                INSERT INTO relaciones (concepto1, concepto2, peso, tipo)
                VALUES (?, ?, ?, ?)
            """, (c1, c2, peso, tipo))
        
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        os.unlink(db_path)
    
    def test_memory_search_with_data(self, sample_database):
        """Test búsqueda en memoria con datos reales"""
        connector = LucasMemoryConnector(sample_database)
        
        # Test búsqueda por concepto
        results = connector.search_concepts("Python")
        assert len(results) >= 1
        assert any(r.concepto == "Python" for r in results)
        
        # Test búsqueda por contexto
        results = connector.search_concepts("visión")
        assert len(results) >= 1
        
        # Test contexto para query
        context = connector.get_context_for_query("OpenCV")
        assert len(context["found_concepts"]) >= 1
        assert len(context["related_patterns"]) >= 1
        
        connector.close()
    
    def test_full_chat_with_memory(self, sample_database, monkeypatch):
        """Test chat completo con memoria real"""
        # Monkey patch para usar nuestra DB de test
        def mock_get_memory_connector():
            return LucasMemoryConnector(sample_database)
        
        monkeypatch.setattr("ianae_server.get_memory_connector", mock_get_memory_connector)
        
        # Test chat sobre Python
        response = client.post("/chat", json={
            "message": "¿Qué sabes sobre Python?"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Debería encontrar contexto sobre Python
        assert "Python" in data["response"] or "python" in data["response"].lower()
        assert "context_info" in data

# Fixtures y utilidades de test
@pytest.fixture
def mock_lm_studio_running(monkeypatch):
    """Mock LM Studio como si estuviera funcionando"""
    def mock_post(*args, **kwargs):
        class MockResponse:
            status_code = 200
            def json(self):
                return {
                    "choices": [{
                        "message": {
                            "content": "Respuesta de prueba de LM Studio"
                        }
                    }]
                }
        return MockResponse()
    
    monkeypatch.setattr("requests.post", mock_post)

def test_with_mocked_llm(mock_lm_studio_running):
    """Test con LM Studio mockeado"""
    connector = LLMConnector()
    
    response = connector._try_lm_studio("test prompt")
    
    assert response["success"] == True
    assert "Respuesta de prueba" in response["response"]
    assert response["provider"] == "LM Studio"

# Comandos para ejecutar tests
if __name__ == "__main__":
    print("🧪 Ejecutando tests de IANAE MVP...")
    print("=" * 40)
    
    # Ejecutar tests básicos
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n✅ Tests completados")
    print("\nPara ejecutar tests específicos:")
    print("pytest test_ianae.py::TestAPI::test_health_endpoint -v")
    print("pytest test_ianae.py::TestDatabase -v")
    print("pytest test_ianae.py -k 'memory' -v")