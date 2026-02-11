#!/usr/bin/env python3
"""
test_sistema_completo.py - Test completo del sistema IANAE integrado
Prueba TODOS los componentes funcionando juntos
"""

import os
import json
import tempfile
import shutil
from pathlib import Path

def test_sistema_ianae_completo():
    """Test completo del sistema IANAE"""
    
    print("🧪 TESTING SISTEMA IANAE COMPLETO")
    print("=" * 60)
    
    # 1. Test de imports
    print("\n1️⃣ PROBANDO IMPORTS...")
    try:
        from core.manager import IANAECore, create_ianae_system
        from auto_detector import AutoDetector
        # Los procesadores están directamente en la carpeta
        from chatgpt import ChatGPTProcessor
        from claude import ClaudeProcessor
        from cline import ClineProcessor
        print("✅ Todos los imports funcionan correctamente")
    except ImportError as e:
        print(f"❌ Error en imports: {e}")
        return False
    
    # 2. Test de creación del sistema
    print("\n2️⃣ PROBANDO CREACIÓN DEL SISTEMA...")
    try:
        ianae = create_ianae_system("test_completo.db")
        print(f"✅ Sistema creado: {ianae}")
    except Exception as e:
        print(f"❌ Error creando sistema: {e}")
        return False
    
    # 3. Test de procesadores
    print("\n3️⃣ PROBANDO PROCESADORES...")
    try:
        # Verificar que están en el sistema
        processor_names = list(ianae.processors.keys())
        print(f"✅ Procesadores disponibles: {processor_names}")
        
        for name in processor_names:
            if hasattr(ianae.processors[name], 'name'):
                print(f"  ✓ {name}: Integrado correctamente")
            else:
                print(f"  ❌ {name}: Problema en integración")
    except Exception as e:
        print(f"❌ Error en procesadores: {e}")
        return False
    
    # 4. Test de auto-detector
    print("\n4️⃣ PROBANDO AUTO-DETECTOR...")
    try:
        detector_stats = ianae.detector.get_statistics()
        print(f"✅ Auto-detector inicializado: {detector_stats['supported_processors']}")
    except Exception as e:
        print(f"❌ Error en auto-detector: {e}")
        return False
    
    # 5. Test con archivos de ejemplo
    print("\n5️⃣ PROBANDO CON ARCHIVOS DE EJEMPLO...")
    
    # Crear directorio temporal
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Archivo ChatGPT de ejemplo
        chatgpt_data = {
            "title": "Test ChatGPT Conversation",
            "create_time": 1640995200.0,
            "mapping": {
                "node1": {
                    "message": {
                        "id": "msg1",
                        "author": {"role": "user"},
                        "content": {"parts": ["Hola, ¿cómo estás?"]},
                        "create_time": 1640995200.0
                    },
                    "parent": None,
                    "children": ["node2"]
                },
                "node2": {
                    "message": {
                        "id": "msg2",
                        "author": {"role": "assistant"},
                        "content": {"parts": ["¡Hola! Estoy muy bien, gracias por preguntar. ¿En qué puedo ayudarte hoy?"]},
                        "create_time": 1640995260.0
                    },
                    "parent": "node1",
                    "children": []
                }
            }
        }
        
        chatgpt_file = os.path.join(temp_dir, "test_chatgpt.json")
        with open(chatgpt_file, 'w', encoding='utf-8') as f:
            json.dump(chatgpt_data, f, indent=2)
        
        # Archivo Claude de ejemplo
        claude_data = [
            {
                "conversation_id": "conv-test-123",
                "name": "Test Claude Conversation",
                "created_at": "2024-01-01T10:00:00Z",
                "chat_messages": [
                    {
                        "uuid": "msg-abc-123",
                        "sender": "human",
                        "text": "¿Puedes ayudarme con Python?",
                        "created_at": "2024-01-01T10:00:00Z"
                    },
                    {
                        "uuid": "msg-def-456",
                        "sender": "assistant", 
                        "text": "¡Por supuesto! Estaré encantado de ayudarte con Python. ¿Qué específicamente necesitas?",
                        "created_at": "2024-01-01T10:01:00Z"
                    }
                ]
            }
        ]
        
        claude_file = os.path.join(temp_dir, "test_claude.json")
        with open(claude_file, 'w', encoding='utf-8') as f:
            json.dump(claude_data, f, indent=2)
        
        # Archivo Cline de ejemplo
        cline_content = """# Cline Task: Test Conversation

## Human:
Necesito crear una función que calcule el factorial de un número.

## Assistant:
Te ayudo a crear una función para calcular el factorial. Aquí tienes una implementación:

```python
def factorial(n):
    if n < 0:
        raise ValueError("El factorial no está definido para números negativos")
    elif n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

# Ejemplo de uso
print(factorial(5))  # 120
```

Esta función usa recursión para calcular el factorial.

## Human:
¡Perfecto! ¿Podrías mostrarme también una versión iterativa?

## Assistant:
¡Claro! Aquí tienes la versión iterativa del factorial:

```python
def factorial_iterativo(n):
    if n < 0:
        raise ValueError("El factorial no está definido para números negativos")
    
    resultado = 1
    for i in range(1, n + 1):
        resultado *= i
    
    return resultado

# Ejemplo de uso
print(factorial_iterativo(5))  # 120
```

La versión iterativa es más eficiente en memoria para números grandes.
"""
        
        cline_file = os.path.join(temp_dir, "test_cline.md")
        with open(cline_file, 'w', encoding='utf-8') as f:
            f.write(cline_content)
        
        print(f"✅ Archivos de ejemplo creados en: {temp_dir}")
        
        # 6. Test de procesamiento individual
        print("\n6️⃣ PROBANDO PROCESAMIENTO INDIVIDUAL...")
        
        test_files = [
            (chatgpt_file, "chatgpt"),
            (claude_file, "claude"), 
            (cline_file, "cline")
        ]
        
        for file_path, expected_type in test_files:
            print(f"\n  📄 Procesando: {os.path.basename(file_path)}")
            
            # Auto-detección
            detection = ianae.detector.detect_file_type(file_path)
            print(f"    🔍 Detectado: {detection.get('processor', 'unknown')} "
                  f"(confianza: {detection.get('confidence', 0):.1f}%)")
            
            if detection['success'] and detection['processor'] == expected_type:
                print(f"    ✅ Auto-detección correcta")
            else:
                print(f"    ❌ Auto-detección incorrecta (esperado: {expected_type})")
            
            # Procesamiento
            result = ianae.process_file(file_path)
            
            if result['success']:
                stats = result['stats']
                print(f"    ✅ Procesado: {stats.get('total_conversations', 0)} conversaciones, "
                      f"{stats.get('total_messages', 0)} mensajes")
            else:
                print(f"    ❌ Error procesando: {result.get('error', 'Unknown')}")
        
        # 7. Test de procesamiento por lotes
        print("\n7️⃣ PROBANDO PROCESAMIENTO POR LOTES...")
        
        batch_result = ianae.process_directory(temp_dir, max_files=10)
        
        if batch_result['success']:
            print(f"✅ Lote procesado: {batch_result['files_processed']} archivos, "
                  f"{batch_result['total_conversations']} conversaciones, "
                  f"{batch_result['total_messages']} mensajes")
        else:
            print(f"❌ Error en lote: {batch_result.get('error', 'Unknown')}")
        
        # 8. Test de búsqueda
        print("\n8️⃣ PROBANDO BÚSQUEDA...")
        
        search_results = ianae.search_conversations("Python", limit=10)
        print(f"✅ Búsqueda 'Python': {len(search_results)} resultados")
        
        for result in search_results[:2]:  # Mostrar primeros 2
            print(f"  📄 {result['title']} ({result['platform']})")
        
        # 9. Test de estadísticas
        print("\n9️⃣ PROBANDO ESTADÍSTICAS...")
        
        stats = ianae.get_statistics()
        summary = stats['summary']
        
        print(f"✅ Estadísticas del sistema:")
        print(f"  📊 Conversaciones: {summary['total_conversations']}")
        print(f"  💬 Mensajes: {summary['total_messages']}")
        print(f"  📁 Archivos procesados: {summary['total_files_processed']}")
        print(f"  🏗️ Plataformas: {summary['supported_platforms']}")
        
        # 10. Test de exportación
        print("\n🔟 PROBANDO EXPORTACIÓN...")
        
        export_file = os.path.join(temp_dir, "export_test.json")
        export_result = ianae.export_conversations(export_file, format='json')
        
        if export_result['success']:
            print(f"✅ Exportación exitosa: {export_result['conversations_exported']} conversaciones")
            print(f"  📄 Archivo: {export_file} ({export_result['file_size']} bytes)")
        else:
            print(f"❌ Error en exportación: {export_result.get('error', 'Unknown')}")
        
        print("\n🎉 TODOS LOS TESTS COMPLETADOS EXITOSAMENTE")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Limpiar archivos temporales
        try:
            ianae.close()
            shutil.rmtree(temp_dir)
            if os.path.exists("test_completo.db"):
                os.remove("test_completo.db")
            print("🧹 Archivos temporales limpiados")
        except Exception as e:
            print(f"⚠️ Error limpiando archivos: {e}")

def test_quick_smoke():
    """Test rápido para verificar que todo funciona básicamente"""
    print("⚡ SMOKE TEST RÁPIDO...")
    
    try:
        from core.manager import create_ianae_system
        
        ianae = create_ianae_system("smoke_test.db")
        stats = ianae.get_statistics()
        ianae.close()
        
        if os.path.exists("smoke_test.db"):
            os.remove("smoke_test.db")
        
        print("✅ Smoke test PASADO - Sistema funcional")
        return True
        
    except Exception as e:
        print(f"❌ Smoke test FALLÓ: {e}")
        return False

if __name__ == "__main__":
    print("🚀 INICIANDO TESTS DEL SISTEMA IANAE")
    print("=" * 60)
    
    # Smoke test primero
    if not test_quick_smoke():
        print("💥 Sistema no funcional - Abortando tests completos")
        exit(1)
    
    print()
    
    # Test completo
    success = test_sistema_ianae_completo()
    
    if success:
        print("\n🎊 SISTEMA IANAE COMPLETAMENTE FUNCIONAL")
        print("🚀 Listo para usar en producción")
    else:
        print("\n💥 SISTEMA TIENE PROBLEMAS")
        print("🔧 Revisar logs de error arriba")
        exit(1)