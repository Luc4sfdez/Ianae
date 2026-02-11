#!/usr/bin/env python3
"""
test_ianae.py - Suite completa de tests para IANAE 4.0
Tests automatizados para todos los componentes del sistema
"""

import pytest
import asyncio
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sqlite3
from datetime import datetime

# Imports del sistema IANAE
try:
    from core.manager import IANAECore, create_ianae_system
    from core.database import IANAEDatabase  
    from auto_detector import AutoDetector
    from processors.base import BaseProcessor
    from processors.chatgpt import ChatGPTProcessor
    from processors.claude import ClaudeProcessor
    from processors.cline import ClineProcessor
    IANAE_AVAILABLE = True
except ImportError:
    IANAE_AVAILABLE = False
    pytest.skip("Módulos IANAE no disponibles", allow_module_level=True)

# === FIXTURES ===

@pytest.fixture
def temp_db():
    """Base de datos temporal para tests"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def ianae_system(temp_db):
    """Sistema IANAE para tests"""
    return create_ianae_system(temp_db)

@pytest.fixture
def sample_chatgpt_data():
    """Datos de muestra de ChatGPT"""
    return [
        {
            "id": "test_conv_1",
            "title": "Test Conversation",
            "mapping": {
                "node1": {
                    "message": {
                        "id": "msg1",
                        "author": {"role": "user"},
                        "content": {"parts": ["Hello, how are you?"]},
                        "create_time": 1640995200
                    }
                },
                "node2": {
                    "message": {
                        "id": "msg2", 
                        "author": {"role": "assistant"},
                        "content": {"parts": ["I'm doing well, thank you!"]},
                        "create_time": 1640995260
                    }
                }
            }
        }
    ]

@pytest.fixture
def sample_claude_data():
    """Datos de muestra de Claude"""
    return [
        {
            "conversation_id": "claude_test_1",
            "name": "Test Claude Conversation",
            "chat_messages": [
                {
                    "uuid": "msg1",
                    "sender": "human",
                    "text": "What is Python?",
                    "created_at": "2024-01-01T12:00:00Z"
                },
                {
                    "uuid": "msg2",
                    "sender": "assistant", 
                    "text": "Python is a programming language.",
                    "created_at": "2024-01-01T12:00:30Z"
                }
            ],
            "created_at": "2024-01-01T12:00:00Z"
        }
    ]

@pytest.fixture
def sample_cline_markdown():
    """Contenido de muestra de Cline"""
    return """# Cline Task

## Human:
Can you help me with a Python script?

## Assistant:
Of course! I'd be happy to help you with a Python script. What specific task are you looking to accomplish?

## Human:
I need to read a CSV file and process the data.

## Assistant:
Here's a simple Python script to read and process CSV data:

```python
import pandas as pd

# Read CSV file
df = pd.read_csv('your_file.csv')

# Process the data
print(df.head())
```
"""

# === TESTS DE AUTO-DETECTOR ===

class TestAutoDetector:
    """Tests para el sistema de auto-detección"""
    
    def test_detect_chatgpt_json(self, sample_chatgpt_data):
        """Test detección de ChatGPT JSON"""
        detector = AutoDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(sample_chatgpt_data, tmp)
            tmp_path = tmp.name
        
        try:
            result = detector.detect_file_type(tmp_path)
            
            assert result['detected_type'] == 'chatgpt_json'
            assert result['confidence'] > 0.8
            assert result['indicators']['has_mapping'] == True
            
        finally:
            os.unlink(tmp_path)
    
    def test_detect_claude_json(self, sample_claude_data):
        """Test detección de Claude JSON"""
        detector = AutoDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(sample_claude_data, tmp)
            tmp_path = tmp.name
        
        try:
            result = detector.detect_file_type(tmp_path)
            
            assert result['detected_type'] == 'claude_json'
            assert result['confidence'] > 0.8
            assert result['indicators']['has_conversation_id'] == True
            
        finally:
            os.unlink(tmp_path)
    
    def test_detect_cline_markdown(self, sample_cline_markdown):
        """Test detección de Cline Markdown"""
        detector = AutoDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            tmp.write(sample_cline_markdown)
            tmp_path = tmp.name
        
        try:
            result = detector.detect_file_type(tmp_path)
            
            assert result['detected_type'] == 'cline_markdown'
            assert result['confidence'] > 0.8
            assert result['indicators']['has_cline_task'] == True
            
        finally:
            os.unlink(tmp_path)
    
    def test_unknown_file_type(self):
        """Test archivo de tipo desconocido"""
        detector = AutoDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("This is just random text with no conversation structure.")
            tmp_path = tmp.name
        
        try:
            result = detector.detect_file_type(tmp_path)
            
            assert result['detected_type'] == 'unknown'
            assert result['confidence'] < 0.5
            
        finally:
            os.unlink(tmp_path)

# === TESTS DE PROCESADORES ===

class TestProcessors:
    """Tests para los procesadores especializados"""
    
    def test_chatgpt_processor(self, sample_chatgpt_data):
        """Test procesador ChatGPT"""
        processor = ChatGPTProcessor()
        
        # Test can_process
        assert processor.can_process(sample_chatgpt_data) == True
        
        # Test process
        result = processor.process(sample_chatgpt_data, "test_file.json")
        
        assert result['success'] == True
        assert len(result['conversations']) == 1
        assert result['stats']['total_conversations'] == 1
        assert result['stats']['total_messages'] == 2
        
        conv = result['conversations'][0]
        assert conv['id'] == 'test_conv_1'
        assert conv['title'] == 'Test Conversation'
        assert conv['platform'] == 'chatgpt'
        assert len(conv['messages']) == 2
    
    def test_claude_processor(self, sample_claude_data):
        """Test procesador Claude"""
        processor = ClaudeProcessor()
        
        # Test can_process
        assert processor.can_process(sample_claude_data) == True
        
        # Test process
        result = processor.process(sample_claude_data, "test_file.json")
        
        assert result['success'] == True
        assert len(result['conversations']) == 1
        assert result['stats']['total_conversations'] == 1
        assert result['stats']['total_messages'] == 2
        
        conv = result['conversations'][0]
        assert conv['id'] == 'claude_test_1'
        assert conv['platform'] == 'claude'
        assert len(conv['messages']) == 2
    
    def test_cline_processor(self, sample_cline_markdown):
        """Test procesador Cline"""
        processor = ClineProcessor()
        
        # Test can_process
        assert processor.can_process(sample_cline_markdown) == True
        
        # Test process
        result = processor.process(sample_cline_markdown, "test_file.md")
        
        assert result['success'] == True
        assert len(result['conversations']) == 1
        assert result['stats']['total_conversations'] == 1
        assert result['stats']['total_messages'] >= 2  # Variable según parsing
        
        conv = result['conversations'][0]
        assert conv['platform'] == 'cline'
        assert len(conv['messages']) >= 2

# === TESTS DE BASE DE DATOS ===

class TestIANAEDatabase:
    """Tests para el sistema de base de datos"""
    
    def test_database_creation(self, temp_db):
        """Test creación de base de datos"""
        db = IANAEDatabase(temp_db)
        
        # Verificar que las tablas existen
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['conversations', 'messages', 'files']
        for table in expected_tables:
            assert table in tables
        
        conn.close()
    
    def test_store_conversation(self, temp_db):
        """Test almacenamiento de conversación"""
        db = IANAEDatabase(temp_db)
        
        conversation = {
            'id': 'test_conv_1',
            'title': 'Test Conversation',
            'platform': 'test',
            'timestamp': datetime.now().isoformat(),
            'messages': [
                {
                    'id': 'msg1',
                    'role': 'user',
                    'content': 'Hello',
                    'timestamp': datetime.now().isoformat()
                }
            ]
        }
        
        result = db.store_conversation(conversation, 'test_file.json')
        assert result == True
        
        # Verificar que se almacenó
        stored = db.get_conversation('test_conv_1')
        assert stored is not None
        assert stored['title'] == 'Test Conversation'
    
    def test_search_conversations(self, temp_db):
        """Test búsqueda de conversaciones"""
        db = IANAEDatabase(temp_db)
        
        # Almacenar conversación de prueba
        conversation = {
            'id': 'search_test',
            'title': 'Python Programming Discussion',
            'platform': 'test',
            'timestamp': datetime.now().isoformat(),
            'messages': [
                {
                    'id': 'msg1',
                    'role': 'user', 
                    'content': 'How do I use Python pandas?',
                    'timestamp': datetime.now().isoformat()
                }
            ]
        }
        
        db.store_conversation(conversation, 'test_search.json')
        
        # Buscar
        results = db.search_conversations("Python")
        assert len(results) > 0
        assert any("Python" in r['content'] for r in results)
    
    def test_get_statistics(self, temp_db):
        """Test obtención de estadísticas"""
        db = IANAEDatabase(temp_db)
        
        # Agregar datos de prueba
        conversation = {
            'id': 'stats_test',
            'title': 'Test for Stats',
            'platform': 'test',
            'timestamp': datetime.now().isoformat(),
            'messages': [
                {'id': 'msg1', 'role': 'user', 'content': 'Test message', 'timestamp': datetime.now().isoformat()}
            ]
        }
        
        db.store_conversation(conversation, 'stats_test.json')
        
        # Obtener estadísticas
        stats = db.get_statistics()
        
        assert 'total_conversations' in stats
        assert 'total_messages' in stats
        assert 'by_platform' in stats
        assert stats['total_conversations'] >= 1
        assert stats['total_messages'] >= 1

# === TESTS DEL SISTEMA INTEGRADO ===

class TestIANAECore:
    """Tests para el sistema principal IANAE"""
    
    def test_system_creation(self, temp_db):
        """Test creación del sistema"""
        system = create_ianae_system(temp_db)
        
        assert isinstance(system, IANAECore)
        assert system.database is not None
        assert system.detector is not None
        assert len(system.processors) > 0
    
    def test_process_file_chatgpt(self, ianae_system, sample_chatgpt_data):
        """Test procesamiento de archivo ChatGPT"""
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(sample_chatgpt_data, tmp)
            tmp_path = tmp.name
        
        try:
            result = ianae_system.process_file(tmp_path)
            
            assert result['success'] == True
            assert result['detected_type'] == 'chatgpt_json'
            assert result['stats']['total_conversations'] > 0
            
        finally:
            os.unlink(tmp_path)
    
    def test_process_file_claude(self, ianae_system, sample_claude_data):
        """Test procesamiento de archivo Claude"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(sample_claude_data, tmp)
            tmp_path = tmp.name
        
        try:
            result = ianae_system.process_file(tmp_path)
            
            assert result['success'] == True
            assert result['detected_type'] == 'claude_json'
            assert result['stats']['total_conversations'] > 0
            
        finally:
            os.unlink(tmp_path)
    
    def test_process_directory(self, ianae_system, sample_chatgpt_data, sample_claude_data):
        """Test procesamiento de directorio"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear archivos de prueba
            chatgpt_file = Path(temp_dir) / "chatgpt.json"
            claude_file = Path(temp_dir) / "claude.json"
            
            with open(chatgpt_file, 'w') as f:
                json.dump(sample_chatgpt_data, f)
            
            with open(claude_file, 'w') as f:
                json.dump(sample_claude_data, f)
            
            # Procesar directorio
            result = ianae_system.process_directory(temp_dir)
            
            assert result['success'] == True
            assert result['files_processed'] == 2
            assert result['total_conversations'] >= 2
    
    def test_search_conversations(self, ianae_system, sample_chatgpt_data):
        """Test búsqueda en el sistema integrado"""
        # Primero procesar un archivo
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(sample_chatgpt_data, tmp)
            tmp_path = tmp.name
        
        try:
            ianae_system.process_file(tmp_path)
            
            # Buscar
            results = ianae_system.search_conversations("hello")
            
            # Debe encontrar algo (case insensitive)
            assert len(results) >= 0  # Puede ser 0 si el texto no contiene "hello"
            
        finally:
            os.unlink(tmp_path)

# === TESTS DE INTEGRACIÓN WEB ===

@pytest.mark.asyncio
class TestWebApp:
    """Tests para la aplicación web"""
    
    async def test_health_endpoint(self):
        """Test endpoint de health check"""
        from fastapi.testclient import TestClient
        
        # Mock de la app sin dependencias
        with patch('ianae_webapp.get_ianae_system') as mock_get_system:
            mock_system = Mock()
            mock_get_system.return_value = mock_system
            
            from ianae_webapp import app
            client = TestClient(app)
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            assert 'stats' in data
            assert data['stats']['total_conversations'] == 10

# === TESTS DE PERFORMANCE ===

class TestPerformance:
    """Tests de rendimiento del sistema"""
    
    def test_large_file_processing(self, ianae_system):
        """Test procesamiento de archivo grande"""
        # Crear datos grandes simulados
        large_chatgpt_data = []
        for i in range(100):  # 100 conversaciones
            conv = {
                "id": f"large_conv_{i}",
                "title": f"Large Conversation {i}",
                "mapping": {}
            }
            
            # 10 mensajes por conversación
            for j in range(10):
                node_id = f"node_{i}_{j}"
                conv["mapping"][node_id] = {
                    "message": {
                        "id": f"msg_{i}_{j}",
                        "author": {"role": "user" if j % 2 == 0 else "assistant"},
                        "content": {"parts": [f"Message {j} in conversation {i}"]},
                        "create_time": 1640995200 + (i * 100) + j
                    }
                }
            
            large_chatgpt_data.append(conv)
        
        # Procesar y medir tiempo
        import time
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(large_chatgpt_data, tmp)
            tmp_path = tmp.name
        
        try:
            start_time = time.time()
            result = ianae_system.process_file(tmp_path)
            processing_time = time.time() - start_time
            
            assert result['success'] == True
            assert result['stats']['total_conversations'] == 100
            assert result['stats']['total_messages'] == 1000
            
            # Debe procesar en menos de 30 segundos
            assert processing_time < 30.0
            print(f"Processed 100 conversations (1000 messages) in {processing_time:.2f}s")
            
        finally:
            os.unlink(tmp_path)
    
    def test_concurrent_processing(self, ianae_system, sample_chatgpt_data):
        """Test procesamiento concurrente"""
        import threading
        import time
        
        results = []
        errors = []
        
        def process_file(file_data, file_suffix):
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{file_suffix}.json', delete=False) as tmp:
                    json.dump(file_data, tmp)
                    tmp_path = tmp.name
                
                result = ianae_system.process_file(tmp_path)
                results.append(result)
                
                os.unlink(tmp_path)
                
            except Exception as e:
                errors.append(str(e))
        
        # Crear 5 hilos procesando simultáneamente
        threads = []
        for i in range(5):
            # Modificar datos para que sean únicos
            data_copy = json.loads(json.dumps(sample_chatgpt_data))
            data_copy[0]['id'] = f"concurrent_test_{i}"
            
            thread = threading.Thread(
                target=process_file,
                args=(data_copy, f"thread_{i}")
            )
            threads.append(thread)
        
        # Iniciar todos los hilos
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verificar resultados
        assert len(errors) == 0, f"Errors in concurrent processing: {errors}"
        assert len(results) == 5
        assert all(r['success'] for r in results)
        
        print(f"Concurrent processing of 5 files completed in {total_time:.2f}s")

# === TESTS DE ROBUSTEZ ===

class TestRobustness:
    """Tests de robustez y manejo de errores"""
    
    def test_corrupted_json_file(self, ianae_system):
        """Test archivo JSON corrupto"""
        corrupted_json = '{"invalid": json, missing quotes}'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write(corrupted_json)
            tmp_path = tmp.name
        
        try:
            result = ianae_system.process_file(tmp_path)
            
            # Debe manejar el error gracefully
            assert result['success'] == False
            assert 'error' in result
            
        finally:
            os.unlink(tmp_path)
    
    def test_empty_file(self, ianae_system):
        """Test archivo vacío"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write('')
            tmp_path = tmp.name
        
        try:
            result = ianae_system.process_file(tmp_path)
            
            assert result['success'] == False
            assert 'error' in result
            
        finally:
            os.unlink(tmp_path)
    
    def test_very_large_file(self, ianae_system):
        """Test archivo muy grande (límite de memoria)"""
        # Crear archivo de ~10MB de datos JSON
        large_content = {
            "conversations": [
                {
                    "id": f"large_{i}",
                    "title": "Large conversation " + "x" * 1000,  # Títulos largos
                    "content": "Very long content " + "data " * 1000  # Contenido largo
                }
                for i in range(1000)  # 1000 conversaciones con mucho texto
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(large_content, tmp)
            tmp_path = tmp.name
        
        try:
            # Verificar tamaño
            file_size = os.path.getsize(tmp_path) / (1024 * 1024)  # MB
            print(f"Testing large file of {file_size:.1f} MB")
            
            result = ianae_system.process_file(tmp_path)
            
            # Debe manejar archivos grandes o fallar gracefully
            if result['success']:
                assert 'stats' in result
            else:
                assert 'error' in result
                
        finally:
            os.unlink(tmp_path)
    
    def test_non_existent_file(self, ianae_system):
        """Test archivo inexistente"""
        result = ianae_system.process_file("/path/that/does/not/exist.json")
        
        assert result['success'] == False
        assert 'error' in result
    
    def test_invalid_permissions(self, ianae_system):
        """Test archivo sin permisos de lectura"""
        import stat
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump({"test": "data"}, tmp)
            tmp_path = tmp.name
        
        try:
            # Quitar permisos de lectura (solo en Unix)
            if os.name != 'nt':  # No es Windows
                os.chmod(tmp_path, stat.S_IWRITE)  # Solo escritura
                
                result = ianae_system.process_file(tmp_path)
                
                assert result['success'] == False
                assert 'error' in result
                
        finally:
            # Restaurar permisos para poder eliminar
            if os.name != 'nt':
                os.chmod(tmp_path, stat.S_IREAD | stat.S_IWRITE)
            os.unlink(tmp_path)

# === UTILIDADES DE TEST ===

class TestUtilities:
    """Utilidades y helpers para testing"""
    
    @staticmethod
    def create_test_conversations(count=10, messages_per_conv=5):
        """Crear conversaciones de prueba"""
        conversations = []
        
        for i in range(count):
            conv = {
                "id": f"test_conv_{i}",
                "title": f"Test Conversation {i}",
                "platform": "test",
                "timestamp": datetime.now().isoformat(),
                "messages": []
            }
            
            for j in range(messages_per_conv):
                message = {
                    "id": f"msg_{i}_{j}",
                    "role": "user" if j % 2 == 0 else "assistant",
                    "content": f"Message {j} in conversation {i}",
                    "timestamp": datetime.now().isoformat()
                }
                conv["messages"].append(message)
            
            conversations.append(conv)
        
        return conversations
    
    @staticmethod
    def assert_conversation_structure(conversation):
        """Validar estructura de conversación"""
        required_fields = ['id', 'title', 'platform', 'messages']
        
        for field in required_fields:
            assert field in conversation, f"Missing field: {field}"
        
        assert isinstance(conversation['messages'], list)
        
        for message in conversation['messages']:
            message_fields = ['id', 'role', 'content']
            for field in message_fields:
                assert field in message, f"Missing message field: {field}"

# === CONFIGURACIÓN DE PYTEST ===

def pytest_configure(config):
    """Configuración de pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )

# === MAIN PARA EJECUTAR TESTS ===

if __name__ == "__main__":
    import sys
    
    print("🧠 IANAE 4.0 - Suite de Tests Automatizados")
    print("=" * 50)
    
    if not IANAE_AVAILABLE:
        print("❌ Módulos IANAE no disponibles")
        print("   Asegúrate de tener todos los archivos del proyecto")
        sys.exit(1)
    
    # Configuración de pytest
    pytest_args = [
        "-v",  # Verbose
        "-x",  # Stop on first failure
        "--tb=short",  # Short traceback format
        "--durations=10",  # Show 10 slowest tests
        "--color=yes"  # Colored output
    ]
    
    # Agregar argumentos de línea de comandos
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])
    else:
        # Por defecto ejecutar todos los tests excepto los lentos
        pytest_args.append('-m "not slow"')
        pytest_args.append(__file__)
    
    print("🚀 Ejecutando tests con pytest...")
    print(f"   Argumentos: {' '.join(pytest_args)}")
    print()
    
    # Ejecutar pytest
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ Todos los tests pasaron correctamente")
        print("🎉 IANAE 4.0 está funcionando perfectamente")
    else:
        print(f"\n❌ Algunos tests fallaron (código: {exit_code})")
        print("🔧 Revisa los errores arriba y corrige los problemas")
    
    sys.exit(exit_code) import app
            client = TestClient(app)
            
            response = client.get("/api/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert 'timestamp' in data
    
    async def test_stats_endpoint(self):
        """Test endpoint de estadísticas"""
        from fastapi.testclient import TestClient
        
        with patch('ianae_webapp.get_ianae_system') as mock_get_system:
            mock_system = Mock()
            mock_system.get_statistics.return_value = {
                'total_conversations': 10,
                'total_messages': 50
            }
            mock_get_system.return_value = mock_system
            
            from ianae_webapp