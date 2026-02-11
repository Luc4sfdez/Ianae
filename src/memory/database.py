#!/usr/bin/env python3
"""
ianae_db.py - Sistema de Base de Datos Optimizado para IANAE
Convierte el JSON gigante en SQLite eficiente con índices y consultas rápidas
"""

import sqlite3
import json
import os
import time
from typing import List, Dict, Any, Tuple
import numpy as np

class IANAEDatabase:
    """
    Base de datos optimizada para IANAE con búsquedas ultrarrápidas
    """
    
    def __init__(self, db_path='ianae_memoria.db'):
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Inicializa la base de datos con estructura optimizada"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Para acceso por nombre de columna
        
        # Crear tablas optimizadas
        self._create_tables()
        self._create_indexes()
    
    def _create_tables(self):
        """Crea tablas optimizadas para conceptos y relaciones"""
        cursor = self.conn.cursor()
        
        # Tabla de conceptos con contexto completo
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conceptos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                categoria TEXT NOT NULL,
                fuente TEXT,
                contexto TEXT,
                palabras_clave TEXT, -- JSON array
                activaciones INTEGER DEFAULT 0,
                relevancia REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de relaciones con peso optimizado
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concepto1_id INTEGER,
                concepto2_id INTEGER,
                peso REAL NOT NULL,
                tipo TEXT DEFAULT 'general', -- tecnologia, problema, solucion
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (concepto1_id) REFERENCES conceptos (id),
                FOREIGN KEY (concepto2_id) REFERENCES conceptos (id),
                UNIQUE(concepto1_id, concepto2_id)
            )
        ''')
        
        # Tabla de conversaciones originales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                archivo TEXT UNIQUE NOT NULL,
                fecha_creacion TEXT,
                num_mensajes INTEGER,
                tecnologias TEXT, -- JSON array
                temas TEXT, -- JSON array  
                resumen TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de mapeo concepto-conversación
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS concepto_conversacion (
                concepto_id INTEGER,
                conversacion_id INTEGER,
                relevancia REAL DEFAULT 1.0,
                FOREIGN KEY (concepto_id) REFERENCES conceptos (id),
                FOREIGN KEY (conversacion_id) REFERENCES conversaciones (id),
                PRIMARY KEY (concepto_id, conversacion_id)
            )
        ''')
        
        # Tabla de vectores conceptuales (para emergencia)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vectores_conceptuales (
                concepto_id INTEGER PRIMARY KEY,
                vector BLOB, -- Numpy array serializado
                dimension INTEGER DEFAULT 20,
                FOREIGN KEY (concepto_id) REFERENCES conceptos (id)
            )
        ''')
        
        self.conn.commit()
    
    def _create_indexes(self):
        """Crea índices para consultas ultrarrápidas"""
        cursor = self.conn.cursor()
        
        # Índices para búsquedas de texto
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conceptos_nombre ON conceptos(nombre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conceptos_categoria ON conceptos(categoria)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conceptos_contexto ON conceptos(contexto)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conceptos_relevancia ON conceptos(relevancia DESC)')
        
        # Índices para relaciones
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relaciones_c1 ON relaciones(concepto1_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relaciones_c2 ON relaciones(concepto2_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relaciones_peso ON relaciones(peso DESC)')
        
        # Índices para conversaciones
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversaciones_titulo ON conversaciones(titulo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversaciones_archivo ON conversaciones(archivo)')
        
        # Full-text search virtual table para búsquedas semánticas
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS conceptos_fts USING fts5(
                nombre, contexto, palabras_clave, categoria,
                content='conceptos',
                content_rowid='id'
            )
        ''')
        
        self.conn.commit()
    
    def importar_desde_json_gigante(self, json_path):
        """Importa el JSON gigante a la base de datos optimizada"""
        print(f"🔄 Importando desde {json_path}...")
        
        if not os.path.exists(json_path):
            print(f"❌ Archivo {json_path} no encontrado")
            return False
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📊 Datos cargados: {len(data.get('conceptos', {}))} conceptos")
            
            # Importar conceptos
            conceptos_importados = self._importar_conceptos(data)
            print(f"✅ Conceptos importados: {conceptos_importados}")
            
            # Importar relaciones (con filtrado inteligente)
            relaciones_importadas = self._importar_relaciones_filtradas(data)
            print(f"✅ Relaciones importantes importadas: {relaciones_importadas}")
            
            # Actualizar FTS
            self._actualizar_fts()
            print("✅ Índices de búsqueda actualizados")
            
            # Mostrar estadísticas
            self._mostrar_estadisticas_db()
            
            return True
            
        except Exception as e:
            print(f"❌ Error importando: {e}")
            return False
    
    def _importar_conceptos(self, data):
        """Importa conceptos con contexto rico"""
        cursor = self.conn.cursor()
        conceptos_data = data.get('conceptos', {})
        contextos_data = data.get('contextos', {})
        fuentes_data = data.get('fuentes', {})
        categorias_data = data.get('categorias', {})
        
        importados = 0
        
        for nombre, concepto_info in conceptos_data.items():
            # Extraer contexto rico
            contexto_obj = contextos_data.get(nombre, {})
            contexto_texto = contexto_obj.get('descripcion', '')
            categoria = contexto_obj.get('categoria', 'general')
            palabras_clave = json.dumps(contexto_obj.get('palabras_clave', []))
            fuente = fuentes_data.get(nombre, '')
            activaciones = concepto_info.get('activaciones', 0)
            
            # Calcular relevancia basada en activaciones y longitud de contexto
            relevancia = min(10.0, activaciones * 0.1 + len(contexto_texto) * 0.001)
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO conceptos 
                    (nombre, categoria, fuente, contexto, palabras_clave, activaciones, relevancia)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (nombre, categoria, fuente, contexto_texto, palabras_clave, activaciones, relevancia))
                
                importados += 1
                
            except sqlite3.Error as e:
                print(f"⚠️ Error importando concepto {nombre}: {e}")
        
        self.conn.commit()
        return importados
    
    def _importar_relaciones_filtradas(self, data):
        """Importa solo las relaciones más importantes para evitar explosión"""
        cursor = self.conn.cursor()
        relaciones_data = data.get('relaciones', [])
        
        # Obtener IDs de conceptos
        cursor.execute('SELECT nombre, id FROM conceptos')
        nombre_a_id = {row['nombre']: row['id'] for row in cursor.fetchall()}
        
        importadas = 0
        relaciones_procesadas = 0
        
        print(f"🔗 Procesando {len(relaciones_data)} relaciones...")
        
        for relacion in relaciones_data:
            relaciones_procesadas += 1
            
            # Progreso cada 10000 relaciones
            if relaciones_procesadas % 10000 == 0:
                print(f"   Procesadas: {relaciones_procesadas}/{len(relaciones_data)}")
            
            origen = relacion.get('origen')
            destino = relacion.get('destino') 
            peso = relacion.get('peso', 0.1)
            
            # Filtros de calidad para evitar ruido
            if peso < 0.15:  # Solo relaciones significativas
                continue
            
            if origen == destino:  # Sin auto-relaciones
                continue
                
            # Verificar que ambos conceptos existen
            if origen not in nombre_a_id or destino not in nombre_a_id:
                continue
            
            id1 = nombre_a_id[origen]
            id2 = nombre_a_id[destino]
            
            # Determinar tipo de relación
            tipo = self._determinar_tipo_relacion(origen, destino, data)
            
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO relaciones 
                    (concepto1_id, concepto2_id, peso, tipo)
                    VALUES (?, ?, ?, ?)
                ''', (min(id1, id2), max(id1, id2), peso, tipo))
                
                if cursor.rowcount > 0:
                    importadas += 1
                    
            except sqlite3.Error as e:
                continue  # Ignorar errores de duplicados
        
        self.conn.commit()
        return importadas
    
    def _determinar_tipo_relacion(self, concepto1, concepto2, data):
        """Determina el tipo de relación basado en categorías"""
        contextos = data.get('contextos', {})
        cat1 = contextos.get(concepto1, {}).get('categoria', 'general')
        cat2 = contextos.get(concepto2, {}).get('categoria', 'general')
        
        if cat1 == 'tecnologia' and cat2 == 'tecnologia':
            return 'tecnologia'
        elif 'problema' in cat1 or 'problema' in cat2:
            return 'problema'
        elif cat1 == cat2:
            return cat1
        else:
            return 'general'
    
    def _actualizar_fts(self):
        """Actualiza la tabla de búsqueda full-text"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM conceptos_fts')
        cursor.execute('''
            INSERT INTO conceptos_fts(rowid, nombre, contexto, palabras_clave, categoria)
            SELECT id, nombre, contexto, palabras_clave, categoria FROM conceptos
        ''')
        self.conn.commit()
    
    def buscar_conceptos_rapido(self, query: str, limite: int = 10) -> List[Dict]:
        """Búsqueda ultrarrápida usando FTS e índices"""
        cursor = self.conn.cursor()
        
        # Limpiar query para FTS
        query_clean = ' '.join(query.split())
        
        # Búsqueda full-text principal
        cursor.execute('''
            SELECT c.*, fts.rank
            FROM conceptos_fts fts
            JOIN conceptos c ON c.id = fts.rowid
            WHERE conceptos_fts MATCH ?
            ORDER BY 
                fts.rank,
                c.relevancia DESC,
                c.activaciones DESC
            LIMIT ?
        ''', (query_clean, limite))
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'concepto': row['nombre'],
                'categoria': row['categoria'],
                'contexto': row['contexto'],
                'fuente': row['fuente'],
                'palabras_clave': json.loads(row['palabras_clave'] or '[]'),
                'puntuacion': float(row.get('rank', 1.0)),
                'relevancia': row['relevancia'],
                'activaciones': row['activaciones']
            })
        
        # Si pocos resultados, búsqueda aproximada
        if len(resultados) < limite // 2:
            resultados.extend(self._busqueda_aproximada(query, limite - len(resultados)))
        
        return resultados
    
    def _busqueda_aproximada(self, query: str, limite: int) -> List[Dict]:
        """Búsqueda aproximada usando LIKE para términos no encontrados en FTS"""
        cursor = self.conn.cursor()
        palabras = query.lower().split()
        
        # Construir condiciones LIKE
        condiciones = []
        params = []
        
        for palabra in palabras:
            if len(palabra) > 2:  # Solo palabras significativas
                condiciones.append("(LOWER(nombre) LIKE ? OR LOWER(contexto) LIKE ?)")
                params.extend([f'%{palabra}%', f'%{palabra}%'])
        
        if not condiciones:
            return []
        
        query_sql = f'''
            SELECT nombre, categoria, contexto, fuente, palabras_clave, relevancia, activaciones
            FROM conceptos
            WHERE {' OR '.join(condiciones)}
            ORDER BY relevancia DESC, activaciones DESC
            LIMIT ?
        '''
        params.append(limite)
        
        cursor.execute(query_sql, params)
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'concepto': row['nombre'],
                'categoria': row['categoria'],
                'contexto': row['contexto'],
                'fuente': row['fuente'],
                'palabras_clave': json.loads(row['palabras_clave'] or '[]'),
                'puntuacion': row['relevancia'],
                'relevancia': row['relevancia'],
                'activaciones': row['activaciones']
            })
        
        return resultados
    
    def obtener_conceptos_relacionados(self, concepto_nombre: str, limite: int = 10) -> List[Dict]:
        """Obtiene conceptos relacionados usando la red de relaciones"""
        cursor = self.conn.cursor()
        
        # Obtener ID del concepto
        cursor.execute('SELECT id FROM conceptos WHERE nombre = ?', (concepto_nombre,))
        row = cursor.fetchone()
        if not row:
            return []
        
        concepto_id = row['id']
        
        # Buscar conceptos relacionados ordenados por peso
        cursor.execute('''
            SELECT c.nombre, c.categoria, c.contexto, c.fuente, 
                   c.palabras_clave, r.peso, c.relevancia, c.activaciones
            FROM relaciones r
            JOIN conceptos c ON (
                CASE 
                    WHEN r.concepto1_id = ? THEN c.id = r.concepto2_id
                    WHEN r.concepto2_id = ? THEN c.id = r.concepto1_id
                END
            )
            WHERE r.concepto1_id = ? OR r.concepto2_id = ?
            ORDER BY r.peso DESC, c.relevancia DESC
            LIMIT ?
        ''', (concepto_id, concepto_id, concepto_id, concepto_id, limite))
        
        relacionados = []
        for row in cursor.fetchall():
            relacionados.append({
                'concepto': row['nombre'],
                'categoria': row['categoria'],
                'contexto': row['contexto'],
                'fuente': row['fuente'],
                'palabras_clave': json.loads(row['palabras_clave'] or '[]'),
                'peso_relacion': row['peso'],
                'relevancia': row['relevancia'],
                'activaciones': row['activaciones']
            })
        
        return relacionados
    
    def generar_contexto_para_llm(self, conceptos_encontrados: List[Dict]) -> str:
        """Genera contexto optimizado para el LLM"""
        if not conceptos_encontrados:
            return "No se encontró contexto relevante en la memoria de Lucas."
        
        contexto_partes = ["MEMORIA PERSONAL DE LUCAS:\n"]
        
        for i, concepto in enumerate(conceptos_encontrados[:5], 1):
            nombre = concepto['concepto']
            categoria = concepto['categoria']
            contexto_texto = concepto['contexto']
            fuente = concepto['fuente']
            
            contexto_partes.append(f"\n{i}. {nombre.upper().replace('_', ' ')}")
            contexto_partes.append(f"   Categoría: {categoria}")
            if fuente:
                contexto_partes.append(f"   Fuente: {fuente}")
            if contexto_texto and len(contexto_texto) > 10:
                contexto_partes.append(f"   Contexto: {contexto_texto}")
            
            # Agregar conceptos relacionados si es relevante
            if concepto.get('peso_relacion', 0) > 0.5:
                relacionados = self.obtener_conceptos_relacionados(nombre, 3)
                if relacionados:
                    relacionados_nombres = [r['concepto'].replace('_', ' ') for r in relacionados[:2]]
                    contexto_partes.append(f"   Relacionado: {', '.join(relacionados_nombres)}")
        
        return '\n'.join(contexto_partes)
    
    def _mostrar_estadisticas_db(self):
        """Muestra estadísticas de la base de datos"""
        cursor = self.conn.cursor()
        
        # Contar registros
        cursor.execute('SELECT COUNT(*) FROM conceptos')
        num_conceptos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM relaciones')
        num_relaciones = cursor.fetchone()[0]
        
        # Categorías
        cursor.execute('SELECT categoria, COUNT(*) FROM conceptos GROUP BY categoria ORDER BY COUNT(*) DESC')
        categorias = cursor.fetchall()
        
        # Tamaño del archivo
        db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
        
        print(f"\n📊 ESTADÍSTICAS DE LA BASE DE DATOS:")
        print(f"💾 Tamaño archivo: {db_size:.1f} MB")
        print(f"🧠 Conceptos: {num_conceptos:,}")
        print(f"🔗 Relaciones: {num_relaciones:,}")
        print(f"\nCategorías:")
        for categoria, cantidad in categorias:
            print(f"  📁 {categoria}: {cantidad:,} conceptos")
    
    def cerrar(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()

def migrar_json_a_db():
    """Función principal para migrar el JSON gigante a SQLite optimizado"""
    print("🚀 MIGRANDO IANAE A BASE DE DATOS OPTIMIZADA")
    print("=" * 50)
    
    # Verificar que existe el JSON
    json_path = 'conceptos_lucas_completo.json'
    if not os.path.exists(json_path):
        print(f"❌ No se encontró {json_path}")
        return False
    
    # Crear base de datos
    print("📊 Creando base de datos optimizada...")
    db = IANAEDatabase('ianae_memoria_optimizada.db')
    
    # Migrar datos
    inicio = time.time()
    exito = db.importar_desde_json_gigante(json_path)
    tiempo_total = time.time() - inicio
    
    if exito:
        print(f"\n🎉 MIGRACIÓN COMPLETADA EN {tiempo_total:.1f} SEGUNDOS")
        print("✅ Base de datos optimizada creada: ianae_memoria_optimizada.db")
        print("🚀 Ahora IANAE será ultrarrápido en búsquedas")
        
        # Hacer backup del JSON gigante
        if os.path.exists(json_path):
            backup_name = json_path.replace('.json', '_backup.json')
            os.rename(json_path, backup_name)
            print(f"💾 JSON original respaldado como: {backup_name}")
    else:
        print("❌ Error en la migración")
    
    db.cerrar()
    return exito

if __name__ == "__main__":
    migrar_json_a_db()
