#!/usr/bin/env python3
"""
demo_ianae.py - Demostración completa de IANAE 4.0
Muestra todas las capacidades del sistema con datos de ejemplo
"""

import os
import json
import tempfile
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

def print_banner():
    """Banner de la demo"""
    print("🧠" + "="*60 + "🧠")
    print("   IANAE 4.0 - DEMOSTRACIÓN COMPLETA")
    print("   Sistema Universal de Digestión de Conversaciones")
    print("🧠" + "="*60 + "🧠")
    print()

def create_sample_data():
    """Crea datos de muestra para la demostración"""
    print("📝 Creando datos de muestra...")
    
    # Datos ChatGPT
    chatgpt_sample = [
        {
            "id": "demo_chatgpt_1",
            "title": "Python Data Analysis Tutorial",
            "create_time": time.time() - 86400,  # Ayer
            "mapping": {
                "node1": {
                    "message": {
                        "id": "msg1",
                        "author": {"role": "user"},
                        "content": {"parts": ["How do I analyze CSV data with Python pandas?"]},
                        "create_time": time.time() - 86400
                    }
                },
                "node2": {
                    "message": {
                        "id": "msg2",
                        "author": {"role": "assistant"},
                        "content": {"parts": [
                            "Here's a comprehensive guide to analyzing CSV data with pandas:\n\n"
                            "```python\nimport pandas as pd\n\n"
                            "# Read CSV file\ndf = pd.read_csv('data.csv')\n\n"
                            "# Basic info\nprint(df.info())\nprint(df.describe())\n\n"
                            "# Data cleaning\ndf.dropna(inplace=True)\n\n"
                            "# Analysis\nresult = df.groupby('category').sum()\n```\n\n"
                            "This will help you get started with data analysis!"
                        ]},
                        "create_time": time.time() - 86300
                    }
                },
                "node3": {
                    "message": {
                        "id": "msg3",
                        "author": {"role": "user"},
                        "content": {"parts": ["What about visualization with matplotlib?"]},
                        "create_time": time.time() - 86200
                    }
                },
                "node4": {
                    "message": {
                        "id": "msg4",
                        "author": {"role": "assistant"},
                        "content": {"parts": [
                            "Great question! Here's how to create visualizations:\n\n"
                            "```python\nimport matplotlib.pyplot as plt\n\n"
                            "# Simple plot\ndf.plot(kind='bar')\nplt.show()\n\n"
                            "# Advanced plotting\nfig, axes = plt.subplots(2, 2, figsize=(12, 8))\n"
                            "df.hist(ax=axes)\nplt.tight_layout()\n```\n\n"
                            "This creates beautiful charts for your data analysis!"
                        ]},
                        "create_time": time.time() - 86100
                    }
                }
            }
        },
        {
            "id": "demo_chatgpt_2",
            "title": "Web Development with FastAPI",
            "create_time": time.time() - 7200,  # 2 horas ago
            "mapping": {
                "node1": {
                    "message": {
                        "id": "web_msg1",
                        "author": {"role": "user"},
                        "content": {"parts": ["How do I create a REST API with FastAPI?"]},
                        "create_time": time.time() - 7200
                    }
                },
                "node2": {
                    "message": {
                        "id": "web_msg2",
                        "author": {"role": "assistant"},
                        "content": {"parts": [
                            "FastAPI is perfect for building modern APIs! Here's a complete example:\n\n"
                            "```python\nfrom fastapi import FastAPI, HTTPException\n"
                            "from pydantic import BaseModel\n\n"
                            "app = FastAPI(title='My API')\n\n"
                            "class Item(BaseModel):\n    name: str\n    price: float\n\n"
                            "@app.get('/')\nasync def root():\n    return {'message': 'Hello World'}\n\n"
                            "@app.post('/items/')\nasync def create_item(item: Item):\n"
                            "    return {'item': item, 'id': 123}\n```\n\n"
                            "Run with: `uvicorn main:app --reload`"
                        ]},
                        "create_time": time.time() - 7100
                    }
                }
            }
        }
    ]
    
    # Datos Claude
    claude_sample = [
        {
            "conversation_id": "demo_claude_1",
            "name": "Machine Learning Concepts",
            "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
            "chat_messages": [
                {
                    "uuid": "claude_msg1",
                    "sender": "human",
                    "text": "Can you explain the difference between supervised and unsupervised learning?",
                    "created_at": (datetime.now() - timedelta(days=2, hours=1)).isoformat()
                },
                {
                    "uuid": "claude_msg2",
                    "sender": "assistant", 
                    "text": "Certainly! Here are the key differences:\n\n**Supervised Learning:**\n- Uses labeled training data\n- Goal: Predict outcomes for new data\n- Examples: Classification, Regression\n- Algorithms: Decision Trees, Random Forest, SVM\n\n**Unsupervised Learning:**\n- Uses unlabeled data\n- Goal: Find hidden patterns\n- Examples: Clustering, Dimensionality Reduction\n- Algorithms: K-Means, PCA, Hierarchical Clustering\n\nThe main distinction is whether you have target labels in your training data!",
                    "created_at": (datetime.now() - timedelta(days=2)).isoformat()
                },
                {
                    "uuid": "claude_msg3",
                    "sender": "human",
                    "text": "What about reinforcement learning?",
                    "created_at": (datetime.now() - timedelta(days=1, hours=23)).isoformat()
                },
                {
                    "uuid": "claude_msg4",
                    "sender": "assistant",
                    "text": "Reinforcement Learning is a third paradigm!\n\n**Reinforcement Learning:**\n- Agent learns through interaction with environment\n- Receives rewards/penalties for actions\n- Goal: Maximize cumulative reward\n- Examples: Game playing (AlphaGo), Robotics, Trading\n- Key concepts: State, Action, Reward, Policy\n\nIt's like learning through trial and error - the agent discovers what works by trying different strategies and getting feedback!",
                    "created_at": (datetime.now() - timedelta(days=1, hours=22)).isoformat()
                }
            ]
        }
    ]
    
    # Datos Cline/Continue
    cline_sample = """# Cline Task: Database Design Project

## Human:
I need help designing a database schema for a e-commerce application. What tables should I include?

## Assistant:
Great question! Here's a comprehensive e-commerce database schema:

**Core Tables:**

1. **Users**
   - user_id (PK)
   - email, username, password_hash
   - first_name, last_name
   - created_at, updated_at

2. **Products**
   - product_id (PK)
   - name, description, price
   - category_id (FK)
   - stock_quantity
   - is_active

3. **Categories**
   - category_id (PK)
   - name, description
   - parent_id (FK, self-reference)

4. **Orders**
   - order_id (PK)
   - user_id (FK)
   - total_amount, status
   - created_at, shipped_at

5. **Order_Items**
   - order_item_id (PK)
   - order_id (FK)
   - product_id (FK)
   - quantity, unit_price

## Human:
What about handling user addresses and payment methods?

## Assistant:
Excellent additions! Here are the additional tables for addresses and payments:

**Address Management:**

6. **Addresses**
   - address_id (PK)
   - user_id (FK)
   - type (billing/shipping)
   - street_address, city, state, zip_code, country
   - is_default boolean

**Payment System:**

7. **Payment_Methods**
   - payment_method_id (PK)
   - user_id (FK)
   - type (credit_card/paypal/bank)
   - encrypted_details (tokenized)
   - is_default boolean

8. **Payments**
   - payment_id (PK)
   - order_id (FK)
   - payment_method_id (FK)
   - amount, status, transaction_id
   - processed_at

**Additional Features:**

9. **Shopping_Cart**
   - cart_id (PK)
   - user_id (FK)
   - created_at, expires_at

10. **Cart_Items**
    - cart_item_id (PK)
    - cart_id (FK)
    - product_id (FK)
    - quantity

This design supports multiple addresses per user, secure payment processing, and persistent shopping carts!

## Human:
Perfect! Can you show me the SQL to create these tables?

## Assistant:
Absolutely! Here's the complete SQL schema:

```sql
-- Users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories table (hierarchical)
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES categories(category_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category_id INTEGER REFERENCES categories(category_id),
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Addresses table
CREATE TABLE addresses (
    address_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    type VARCHAR(20) CHECK (type IN ('billing', 'shipping')),
    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    zip_code VARCHAR(20),
    country VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payment methods table
CREATE TABLE payment_methods (
    payment_method_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    type VARCHAR(20) CHECK (type IN ('credit_card', 'paypal', 'bank_transfer')),
    encrypted_details TEXT,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    billing_address_id INTEGER REFERENCES addresses(address_id),
    shipping_address_id INTEGER REFERENCES addresses(address_id),
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    shipped_at TIMESTAMP
);

-- Order items table
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payments table
CREATE TABLE payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    payment_method_id INTEGER REFERENCES payment_methods(payment_method_id),
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    transaction_id VARCHAR(255),
    processed_at TIMESTAMP
);

-- Shopping cart table
CREATE TABLE shopping_cart (
    cart_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Cart items table
CREATE TABLE cart_items (
    cart_item_id SERIAL PRIMARY KEY,
    cart_id INTEGER REFERENCES shopping_cart(cart_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_addresses_user ON addresses(user_id);
CREATE INDEX idx_cart_user ON shopping_cart(user_id);
```

This schema includes proper constraints, indexes, and follows e-commerce best practices!
"""
    
    return chatgpt_sample, claude_sample, cline_sample

def save_sample_files(chatgpt_data, claude_data, cline_data):
    """Guarda archivos de muestra en directorio temporal"""
    temp_dir = tempfile.mkdtemp(prefix="ianae_demo_")
    
    # Archivo ChatGPT
    chatgpt_file = Path(temp_dir) / "chatgpt_conversations.json"
    with open(chatgpt_file, 'w', encoding='utf-8') as f:
        json.dump(chatgpt_data, f, indent=2)
    
    # Archivo Claude
    claude_file = Path(temp_dir) / "claude_conversations.json"
    with open(claude_file, 'w', encoding='utf-8') as f:
        json.dump(claude_data, f, indent=2)
    
    # Archivo Cline
    cline_file = Path(temp_dir) / "cline_task.md"
    with open(cline_file, 'w', encoding='utf-8') as f:
        f.write(cline_data)
    
    print(f"✅ Archivos de muestra creados en: {temp_dir}")
    return temp_dir, [chatgpt_file, claude_file, cline_file]

def demo_auto_detection():
    """Demuestra el sistema de auto-detección"""
    print("\n🔍 DEMO: SISTEMA DE AUTO-DETECCIÓN")
    print("-" * 40)
    
    try:
        from auto_detector import AutoDetector
        detector = AutoDetector()
        
        chatgpt_data, claude_data, cline_data = create_sample_data()
        temp_dir, files = save_sample_files(chatgpt_data, claude_data, cline_data)
        
        for file_path in files:
            print(f"\n📄 Analizando: {file_path.name}")
            
            result = detector.detect_file_type(str(file_path))
            
            print(f"   🎯 Tipo detectado: {result['detected_type']}")
            print(f"   📊 Confianza: {result['confidence']:.2f}")
            print(f"   🔍 Indicadores: {list(result['indicators'].keys())}")
            
            if result['confidence'] > 0.8:
                print("   ✅ Detección exitosa")
            else:
                print("   ⚠️ Baja confianza")
        
        return temp_dir
        
    except ImportError:
        print("❌ Módulos IANAE no disponibles")
        print("   Ejecuta desde el directorio del proyecto con todos los archivos")
        return None

def demo_processing():
    """Demuestra el procesamiento completo"""
    print("\n⚡ DEMO: PROCESAMIENTO COMPLETO")
    print("-" * 40)
    
    try:
        from core.manager import create_ianae_system
        
        # Crear sistema con BD temporal
        db_path = tempfile.mktemp(suffix='.db')
        ianae = create_ianae_system(db_path)
        
        print(f"🗄️ Sistema creado con BD: {db_path}")
        
        # Crear datos de muestra
        chatgpt_data, claude_data, cline_data = create_sample_data()
        temp_dir, files = save_sample_files(chatgpt_data, claude_data, cline_data)
        
        total_conversations = 0
        total_messages = 0
        
        # Procesar cada archivo
        for file_path in files:
            print(f"\n📝 Procesando: {file_path.name}")
            
            start_time = time.time()
            result = ianae.process_file(str(file_path))
            processing_time = time.time() - start_time
            
            if result['success']:
                stats = result['stats']
                total_conversations += stats['total_conversations']
                total_messages += stats['total_messages']
                
                print(f"   ✅ Éxito en {processing_time:.2f}s")
                print(f"   📊 Conversaciones: {stats['total_conversations']}")
                print(f"   💬 Mensajes: {stats['total_messages']}")
                print(f"   🔧 Tipo: {result['detected_type']}")
            else:
                print(f"   ❌ Error: {result.get('error', 'Desconocido')}")
        
        print(f"\n🎉 PROCESAMIENTO COMPLETADO:")
        print(f"   📁 Total conversaciones: {total_conversations}")
        print(f"   💬 Total mensajes: {total_messages}")
        
        return ianae, temp_dir
        
    except ImportError:
        print("❌ Módulos IANAE no disponibles")
        return None, None

def demo_search(ianae):
    """Demuestra la funcionalidad de búsqueda"""
    print("\n🔍 DEMO: BÚSQUEDA DE CONVERSACIONES")
    print("-" * 40)
    
    search_queries = [
        "Python",
        "pandas",
        "FastAPI", 
        "machine learning",
        "database",
        "SQL"
    ]
    
    for query in search_queries:
        print(f"\n🔎 Buscando: '{query}'")
        
        try:
            results = ianae.search_conversations(query, limit=5)
            
            if results:
                print(f"   ✅ Encontrados {len(results)} resultados:")
                for i, result in enumerate(results[:3], 1):
                    title = result.get('title', 'Sin título')[:40]
                    content_preview = result.get('content', '')[:80]
                    platform = result.get('platform', 'unknown')
                    
                    print(f"   {i}. [{platform}] {title}")
                    print(f"      {content_preview}...")
            else:
                print("   ❌ No se encontraron resultados")
                
        except Exception as e:
            print(f"   ❌ Error en búsqueda: {e}")

def demo_statistics(ianae):
    """Demuestra las estadísticas del sistema"""
    print("\n📊 DEMO: ESTADÍSTICAS DEL SISTEMA")
    print("-" * 40)
    
    try:
        stats = ianae.get_statistics()
        
        print(f"📈 ESTADÍSTICAS GENERALES:")
        print(f"   💬 Total conversaciones: {stats.get('total_conversations', 0)}")
        print(f"   📝 Total mensajes: {stats.get('total_messages', 0)}")
        print(f"   📁 Total archivos: {stats.get('total_files', 0)}")
        
        if 'by_platform' in stats:
            print(f"\n🌐 POR PLATAFORMA:")
            for platform, count in stats['by_platform'].items():
                print(f"   • {platform}: {count} conversaciones")
        
        if 'processing_stats' in stats:
            proc_stats = stats['processing_stats']
            print(f"\n⚡ RENDIMIENTO:")
            print(f"   • Tiempo promedio: {proc_stats.get('avg_processing_time', 0):.3f}s")
            print(f"   • Tiempo total: {proc_stats.get('total_processing_time', 0):.2f}s")
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")

def demo_batch_processing():
    """Demuestra procesamiento por lotes"""
    print("\n📦 DEMO: PROCESAMIENTO POR LOTES")
    print("-" * 40)
    
    try:
        from core.manager import create_ianae_system
        
        # Sistema nuevo para lotes
        db_path = tempfile.mktemp(suffix='_batch.db')
        ianae = create_ianae_system(db_path)
        
        # Crear directorio con múltiples archivos
        batch_dir = tempfile.mkdtemp(prefix="ianae_batch_")
        
        # Crear varios archivos de muestra
        for i in range(5):
            # ChatGPT files
            chatgpt_sample = [{
                "id": f"batch_chatgpt_{i}",
                "title": f"Batch Conversation {i}",
                "mapping": {
                    "node1": {
                        "message": {
                            "id": f"batch_msg_{i}",
                            "author": {"role": "user"},
                            "content": {"parts": [f"This is batch conversation number {i}"]},
                            "create_time": time.time() - (i * 3600)
                        }
                    }
                }
            }]
            
            file_path = Path(batch_dir) / f"batch_{i}.json"
            with open(file_path, 'w') as f:
                json.dump(chatgpt_sample, f)
        
        print(f"📁 Directorio de lote: {batch_dir}")
        print(f"📄 Archivos creados: 5")
        
        # Procesar directorio completo
        start_time = time.time()
        result = ianae.process_directory(batch_dir, max_files=10)
        batch_time = time.time() - start_time
        
        if result['success']:
            print(f"\n✅ LOTE PROCESADO EN {batch_time:.2f}s:")
            print(f"   📁 Archivos procesados: {result['files_processed']}")
            print(f"   ⏭️ Archivos omitidos: {result['files_skipped']}")
            print(f"   💬 Total conversaciones: {result['total_conversations']}")
            print(f"   📝 Total mensajes: {result['total_messages']}")
            
            if 'detailed_results' in result:
                print(f"\n📋 DETALLE POR ARCHIVO:")
                for file_result in result['detailed_results'][:3]:
                    filename = Path(file_result['filename']).name
                    print(f"   • {filename}: {file_result['conversations']} conv, {file_result['messages']} msg")
        else:
            print(f"❌ Error en procesamiento por lotes")
        
        return ianae
        
    except ImportError:
        print("❌ Módulos IANAE no disponibles")
        return None

def demo_api_endpoints():
    """Demuestra los endpoints de la API"""
    print("\n🌐 DEMO: ENDPOINTS DE LA API")
    print("-" * 40)
    
    endpoints = [
        ("GET", "/api/health", "Health check del sistema"),
        ("GET", "/api/stats", "Estadísticas del sistema"),
        ("POST", "/api/process-file", "Procesar archivo individual"),
        ("POST", "/api/process-batch", "Procesamiento por lotes"),
        ("POST", "/api/search", "Búsqueda de conversaciones"),
        ("GET", "/api/conversations/{id}", "Obtener conversación específica"),
        ("GET", "/api/platforms", "Plataformas soportadas"),
        ("POST", "/api/export", "Exportar conversaciones")
    ]
    
    print("📡 ENDPOINTS DISPONIBLES:")
    for method, endpoint, description in endpoints:
        print(f"   {method:4} {endpoint:25} - {description}")
    
    print("\n🔧 EJEMPLOS DE USO:")
    print("   # Health check")
    print("   curl http://localhost:8000/api/health")
    print()
    print("   # Subir archivo")
    print("   curl -X POST -F 'file=@conversation.json' \\")
    print("        http://localhost:8000/api/process-file")
    print()
    print("   # Buscar conversaciones")
    print("   curl -X POST -H 'Content-Type: application/json' \\")
    print("        -d '{\"query\":\"Python\",\"limit\":10}' \\")
    print("        http://localhost:8000/api/search")

def demo_performance_test():
    """Demuestra las capacidades de rendimiento"""
    print("\n⚡ DEMO: TEST DE RENDIMIENTO")
    print("-" * 40)
    
    try:
        from core.manager import create_ianae_system
        
        # Sistema para performance
        db_path = tempfile.mktemp(suffix='_perf.db')
        ianae = create_ianae_system(db_path)
        
        # Crear archivo grande para testing
        print("📝 Creando archivo de prueba grande...")
        
        large_conversations = []
        for i in range(50):  # 50 conversaciones
            conv = {
                "id": f"perf_conv_{i}",
                "title": f"Performance Test Conversation {i}",
                "mapping": {}
            }
            
            # 5 mensajes por conversación
            for j in range(5):
                node_id = f"node_{i}_{j}"
                conv["mapping"][node_id] = {
                    "message": {
                        "id": f"perf_msg_{i}_{j}",
                        "author": {"role": "user" if j % 2 == 0 else "assistant"},
                        "content": {"parts": [
                            f"This is message {j} in performance test conversation {i}. " +
                            "Adding some extra content to make the message longer and test processing speed. " * 3
                        ]},
                        "create_time": time.time() - (i * 100) + j
                    }
                }
            
            large_conversations.append(conv)
        
        # Guardar archivo grande
        large_file = tempfile.mktemp(suffix='_large.json')
        with open(large_file, 'w') as f:
            json.dump(large_conversations, f)
        
        file_size = os.path.getsize(large_file) / (1024 * 1024)  # MB
        print(f"📄 Archivo creado: {file_size:.1f} MB")
        print(f"📊 Contenido: 50 conversaciones, 250 mensajes")
        
        # Procesar y medir tiempo
        print("\n⏱️ Procesando archivo grande...")
        start_time = time.time()
        result = ianae.process_file(large_file)
        processing_time = time.time() - start_time
        
        if result['success']:
            stats = result['stats']
            throughput_conv = stats['total_conversations'] / processing_time
            throughput_msg = stats['total_messages'] / processing_time
            
            print(f"✅ PROCESAMIENTO EXITOSO:")
            print(f"   ⏱️ Tiempo total: {processing_time:.2f}s")
            print(f"   📈 Conversaciones/segundo: {throughput_conv:.1f}")
            print(f"   💬 Mensajes/segundo: {throughput_msg:.1f}")
            print(f"   📊 Conversaciones procesadas: {stats['total_conversations']}")
            print(f"   💬 Mensajes procesados: {stats['total_messages']}")
            
            # Test de búsqueda en el archivo grande
            print(f"\n🔍 Test de búsqueda...")
            search_start = time.time()
            search_results = ianae.search_conversations("performance test")
            search_time = time.time() - search_start
            
            print(f"   ⏱️ Tiempo de búsqueda: {search_time:.3f}s")
            print(f"   📋 Resultados encontrados: {len(search_results)}")
            
        else:
            print(f"❌ Error en procesamiento: {result.get('error', 'Desconocido')}")
        
        # Cleanup
        os.unlink(large_file)
        
    except ImportError:
        print("❌ Módulos IANAE no disponibles")
    except Exception as e:
        print(f"❌ Error en test de rendimiento: {e}")

def demo_web_interface():
    """Información sobre la interfaz web"""
    print("\n🌐 DEMO: INTERFAZ WEB")
    print("-" * 40)
    
    print("🚀 PARA PROBAR LA INTERFAZ WEB:")
    print("   1. Ejecutar: python ianae_webapp.py")
    print("   2. Abrir navegador en: http://localhost:8000")
    print("   3. Arrastar archivos al área de carga")
    print("   4. Usar la búsqueda en tiempo real")
    print()
    print("🎨 CARACTERÍSTICAS DE LA UI:")
    print("   • Drag & drop de archivos")
    print("   • Auto-detección visual")
    print("   • Estadísticas en tiempo real")
    print("   • Búsqueda instantánea")
    print("   • Interfaz responsive")
    print("   • Progreso de procesamiento")
    print()
    print("📡 API DOCS INTERACTIVA:")
    print("   • Swagger UI: http://localhost:8000/api/docs")
    print("   • ReDoc: http://localhost:8000/api/redoc")

def demo_integration_examples():
    """Ejemplos de integración"""
    print("\n🔧 DEMO: EJEMPLOS DE INTEGRACIÓN")
    print("-" * 40)
    
    print("💻 INTEGRACIÓN EN SCRIPTS PYTHON:")
    print("""
from core.manager import create_ianae_system

# Setup básico
ianae = create_ianae_system("mi_proyecto.db")

# Procesar directorio de backups
result = ianae.process_directory("/backups/conversaciones/")
print(f"Procesadas {result['total_conversations']} conversaciones")

# Búsqueda específica
resultados = ianae.search_conversations("error python", limit=5)
for conv in resultados:
    print(f"Problema: {conv['title']}")
""")
    
    print("\n🌐 INTEGRACIÓN VÍA API REST:")
    print("""
import requests

# Subir archivo
with open('conversacion.json', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/process-file',
        files={'file': f}
    )
    result = response.json()

# Buscar contenido
search_data = {"query": "machine learning", "limit": 10}
response = requests.post(
    'http://localhost:8000/api/search',
    json=search_data
)
resultados = response.json()['results']
""")
    
    print("\n📦 INTEGRACIÓN EN PIPELINE DE DATOS:")
    print("""
# pipeline_conversaciones.py
from core.manager import create_ianae_system
import schedule
import time

def procesar_nuevas_conversaciones():
    ianae = create_ianae_system("empresa.db")
    
    # Procesar directorio de nuevas conversaciones
    result = ianae.process_directory("/data/nuevas_conversaciones/")
    
    # Log de resultados
    print(f"{result['files_processed']} archivos procesados")
    
    # Mover archivos procesados
    # ... lógica de archivo

# Ejecutar cada hora
schedule.every().hour.do(procesar_nuevas_conversaciones)

while True:
    schedule.run_pending()
    time.sleep(60)
""")

def run_interactive_demo():
    """Demo interactivo con menú"""
    print("\n🎮 MODO INTERACTIVO")
    print("-" * 40)
    
    ianae = None
    temp_dir = None
    
    while True:
        print("\n📋 OPCIONES DISPONIBLES:")
        print("1. 🔍 Auto-detección de archivos")
        print("2. ⚡ Procesamiento completo") 
        print("3. 🔍 Búsqueda de conversaciones")
        print("4. 📊 Estadísticas del sistema")
        print("5. 📦 Procesamiento por lotes")
        print("6. ⚡ Test de rendimiento")
        print("7. 🌐 Información de API")
        print("8. 🔧 Ejemplos de integración")
        print("9. 🌐 Interfaz web")
        print("0. 🚪 Salir")
        
        try:
            opcion = input("\n🎮 Selecciona opción (0-9): ").strip()
            
            if opcion == "0":
                print("\n👋 ¡Gracias por probar IANAE 4.0!")
                break
            elif opcion == "1":
                temp_dir = demo_auto_detection()
            elif opcion == "2":
                ianae, temp_dir = demo_processing()
            elif opcion == "3":
                if ianae:
                    demo_search(ianae)
                else:
                    print("❌ Primero ejecuta el procesamiento completo (opción 2)")
            elif opcion == "4":
                if ianae:
                    demo_statistics(ianae)
                else:
                    print("❌ Primero ejecuta el procesamiento completo (opción 2)")
            elif opcion == "5":
                demo_batch_processing()
            elif opcion == "6":
                demo_performance_test()
            elif opcion == "7":
                demo_api_endpoints()
            elif opcion == "8":
                demo_integration_examples()
            elif opcion == "9":
                demo_web_interface()
            else:
                print("❌ Opción no válida")
                
        except KeyboardInterrupt:
            print("\n\n👋 Demo cancelado por el usuario")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            
        input("\n⏎ Presiona Enter para continuar...")

def main():
    """Función principal de la demo"""
    print_banner()
    
    print("🎯 BIENVENIDO A LA DEMO DE IANAE 4.0")
    print()
    print("Esta demostración te mostrará todas las capacidades del sistema:")
    print("• Auto-detección inteligente de tipos de archivo")
    print("• Procesamiento universal de conversaciones")  
    print("• Base de datos optimizada con búsqueda")
    print("• API REST completa")
    print("• Tests de rendimiento")
    print()
    
    modo = input("🎮 ¿Modo automático (a) o interactivo (i)? [a/i]: ").strip().lower()
    
    if modo == 'i':
        run_interactive_demo()
    else:
        print("🚀 Ejecutando demo automática completa...\n")
        
        # Demo automática secuencial
        temp_dir = demo_auto_detection()
        
        if temp_dir:
            ianae, _ = demo_processing()
            
            if ianae:
                demo_search(ianae)
                demo_statistics(ianae)
            
            demo_batch_processing()
            demo_performance_test()
            demo_api_endpoints()
            demo_integration_examples()
            demo_web_interface()
            
            print("\n🎉 DEMO AUTOMÁTICA COMPLETADA")
            print("=" * 50)
            print("✅ Todas las funcionalidades han sido demostradas")
            print("🚀 Para usar IANAE 4.0:")
            print("   1. python ianae_webapp.py")
            print("   2. Abrir http://localhost:8000")
            print("   3. ¡Subir tus conversaciones!")
        else:
            print("❌ No se pudo ejecutar la demo completa")
            print("   Asegúrate de tener todos los módulos IANAE")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo cancelado. ¡Hasta pronto!")
    except Exception as e:
        print(f"\n❌ Error en la demo: {e}")
        print("🔧 Verifica que todos los módulos IANAE estén disponibles")