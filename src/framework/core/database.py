# Database operations 
#!/usr/bin/env python3
"""
core/database.py - Sistema de Base de Datos IANAE Completo
Versión corregida con todas las funcionalidades integradas
"""

import sqlite3
import json
import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IANAEDatabase:
    """
    Sistema de base de datos completo para IANAE.
    Maneja conversaciones, mensajes, conceptos, relaciones y deduplicación.
    """
    
    def __init__(self, db_path: str = "ianae_memoria.db"):
        """
        Inicializa la base de datos IANAE.
        
        Args:
            db_path: Ruta del archivo de base de datos SQLite
        """
        self.db_path = db_path
        self.db_dir = os.path.dirname(os.path.abspath(db_path))
        
        # Crear directorio si no existe
        if self.db_dir and not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir, exist_ok=True)
        
        # Inicializar base de datos
        self._init_database()
        
        # Estadísticas en memoria
        self._stats_cache = {}
        self._cache_timestamp = 0
        self._cache_timeout = 60  # 60 segundos
        
        logger.info(f"IANAEDatabase inicializada: {self.db_path}")
    
    def _init_database(self):
        """Inicializa todas las tablas necesarias"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Habilitar foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Crear tablas principales
            self._create_conversations_table(cursor)
            self._create_messages_table(cursor)
            self._create_concepts_table(cursor)
            self._create_relationships_table(cursor)
            self._create_files_table(cursor)
            self._create_processing_table(cursor)
            
            # Crear índices para optimización
            self._create_indexes(cursor)
            
            # Crear vistas útiles
            self._create_views(cursor)
            
            conn.commit()
            conn.close()
            
            logger.info("Base de datos inicializada correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
            raise
    
    def _create_conversations_table(self, cursor):
        """Crea tabla de conversaciones"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                platform TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                total_messages INTEGER DEFAULT 0,
                content_hash TEXT,
                metadata TEXT,
                source_file TEXT,
                processing_version TEXT DEFAULT '1.0'
            )
        ''')
    
    def _create_messages_table(self, cursor):
        """Crea tabla de mensajes"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT,
                content_hash TEXT,
                content_length INTEGER,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            )
        ''')
    
    def _create_concepts_table(self, cursor):
        """Crea tabla de conceptos"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT DEFAULT 'general',
                strength REAL DEFAULT 1.0,
                usage_count INTEGER DEFAULT 0,
                last_used TEXT,
                file_path TEXT,
                byte_start INTEGER DEFAULT 0,
                byte_end INTEGER DEFAULT 0,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_relationships_table(self, cursor):
        """Crea tabla de relaciones entre conceptos"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept_a TEXT NOT NULL,
                concept_b TEXT NOT NULL,
                strength REAL NOT NULL,
                context_type TEXT DEFAULT 'cooccurrence',
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                discovery_date TEXT,
                context TEXT,
                UNIQUE(concept_a, concept_b)
            )
        ''')
    
    def _create_files_table(self, cursor):
        """Crea tabla de archivos procesados"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                file_path TEXT,
                file_hash TEXT,
                file_size INTEGER,
                processor_used TEXT,
                conversations_extracted INTEGER DEFAULT 0,
                messages_extracted INTEGER DEFAULT 0,
                processing_time REAL DEFAULT 0.0,
                processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed'
            )
        ''')
    
    def _create_processing_table(self, cursor):
        """Crea tabla de historial de procesamiento"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                file_path TEXT,
                processor TEXT,
                start_time TEXT,
                end_time TEXT,
                duration REAL,
                status TEXT,
                items_processed INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_indexes(self, cursor):
        """Crea índices para optimización"""
        indexes = [
            # Conversaciones
            "CREATE INDEX IF NOT EXISTS idx_conversations_platform ON conversations(platform)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_hash ON conversations(content_hash)",
            
            # Mensajes
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role)",
            "CREATE INDEX IF NOT EXISTS idx_messages_hash ON messages(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)",
            
            # Conceptos
            "CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name)",
            "CREATE INDEX IF NOT EXISTS idx_concepts_category ON concepts(category)",
            "CREATE INDEX IF NOT EXISTS idx_concepts_usage ON concepts(usage_count DESC)",
            "CREATE INDEX IF NOT EXISTS idx_concepts_strength ON concepts(strength DESC)",
            
            # Relaciones
            "CREATE INDEX IF NOT EXISTS idx_relationships_a ON relationships(concept_a)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_b ON relationships(concept_b)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_strength ON relationships(strength DESC)",
            
            # Archivos
            "CREATE INDEX IF NOT EXISTS idx_files_filename ON processed_files(filename)",
            "CREATE INDEX IF NOT EXISTS idx_files_hash ON processed_files(file_hash)",
            "CREATE INDEX IF NOT EXISTS idx_files_processed_at ON processed_files(processed_at)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    def _create_views(self, cursor):
        """Crea vistas útiles para consultas"""
        # Vista de estadísticas por plataforma
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS platform_stats AS
            SELECT 
                platform,
                COUNT(*) as conversation_count,
                SUM(total_messages) as total_messages,
                AVG(total_messages) as avg_messages_per_conversation,
                MIN(created_at) as first_conversation,
                MAX(created_at) as last_conversation
            FROM conversations
            GROUP BY platform
        ''')
        
        # Vista de conceptos más utilizados
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS top_concepts AS
            SELECT 
                name,
                category,
                usage_count,
                strength,
                last_used,
                (usage_count * strength) as relevance_score
            FROM concepts
            ORDER BY relevance_score DESC
        ''')
    
    def add_conversation(self, conversation: Dict[str, Any]) -> bool:
        """
        Añade una conversación a la base de datos.
        
        Args:
            conversation: Datos de la conversación en formato IANAE estándar
            
        Returns:
            True si se añadió correctamente
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calcular hash del contenido
            content_hash = self._calculate_conversation_hash(conversation)
            
            # Preparar metadatos
            metadata = json.dumps(conversation.get('metadata', {}))
            
            # Insertar conversación
            cursor.execute('''
                INSERT OR REPLACE INTO conversations 
                (id, title, platform, created_at, total_messages, content_hash, metadata, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                conversation['id'],
                conversation['titulo'],
                conversation['plataforma'],
                conversation.get('timestamp'),
                len(conversation.get('mensajes', [])),
                content_hash,
                metadata,
                conversation.get('metadata', {}).get('source_file')
            ))
            
            # Insertar mensajes
            for mensaje in conversation.get('mensajes', []):
                self._add_message(cursor, mensaje, conversation['id'])
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Conversación añadida: {conversation['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error añadiendo conversación {conversation.get('id', 'unknown')}: {e}")
            return False
    
    def _add_message(self, cursor, message: Dict[str, Any], conversation_id: str):
        """Añade un mensaje a la base de datos"""
        content_hash = hashlib.md5(message['content'].encode()).hexdigest()
        metadata = json.dumps(message.get('metadata', {}))
        
        cursor.execute('''
            INSERT OR REPLACE INTO messages 
            (id, conversation_id, role, content, timestamp, content_hash, content_length, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.get('id', f"{conversation_id}_{content_hash[:8]}"),
            conversation_id,
            message['role'],
            message['content'],
            message.get('timestamp'),
            content_hash,
            len(message['content']),
            metadata
        ))
    
    def add_conversations_batch(self, conversations: List[Dict[str, Any]], 
                               batch_size: int = 100) -> Dict[str, Any]:
        """
        Añade múltiples conversaciones de forma eficiente.
        
        Args:
            conversations: Lista de conversaciones
            batch_size: Tamaño del lote para procesamiento
            
        Returns:
            Estadísticas del procesamiento
        """
        start_time = time.time()
        
        stats = {
            'total_conversations': len(conversations),
            'conversations_added': 0,
            'conversations_updated': 0,
            'conversations_skipped': 0,
            'messages_added': 0,
            'errors': 0,
            'processing_time': 0.0
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            for i in range(0, len(conversations), batch_size):
                batch = conversations[i:i + batch_size]
                
                try:
                    cursor = conn.cursor()
                    cursor.execute("BEGIN TRANSACTION")
                    
                    for conversation in batch:
                        try:
                            # Verificar si ya existe
                            existing = self._get_conversation_by_id(cursor, conversation['id'])
                            
                            if existing:
                                # Comparar hashes para determinar si actualizar
                                new_hash = self._calculate_conversation_hash(conversation)
                                if existing.get('content_hash') != new_hash:
                                    self._update_conversation(cursor, conversation, new_hash)
                                    stats['conversations_updated'] += 1
                                else:
                                    stats['conversations_skipped'] += 1
                            else:
                                # Nueva conversación
                                self._insert_conversation(cursor, conversation)
                                stats['conversations_added'] += 1
                            
                            stats['messages_added'] += len(conversation.get('mensajes', []))
                            
                        except Exception as e:
                            logger.error(f"Error procesando conversación {conversation.get('id')}: {e}")
                            stats['errors'] += 1
                    
                    cursor.execute("COMMIT")
                    
                    # Log progreso
                    if (i + batch_size) % 500 == 0:
                        logger.info(f"Procesadas {i + batch_size}/{len(conversations)} conversaciones...")
                        
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    logger.error(f"Error en lote {i//batch_size + 1}: {e}")
                    stats['errors'] += batch_size
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error en procesamiento por lotes: {e}")
            stats['errors'] = len(conversations)
        
        stats['processing_time'] = time.time() - start_time
        return stats
    
    def _get_conversation_by_id(self, cursor, conv_id: str) -> Optional[Dict]:
        """Obtiene conversación por ID"""
        cursor.execute('''
            SELECT id, title, platform, created_at, content_hash, metadata 
            FROM conversations WHERE id = ?
        ''', (conv_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'title': row[1], 
                'platform': row[2],
                'created_at': row[3],
                'content_hash': row[4],
                'metadata': json.loads(row[5] or '{}')
            }
        return None
    
    def _insert_conversation(self, cursor, conversation: Dict[str, Any]):
        """Inserta nueva conversación"""
        content_hash = self._calculate_conversation_hash(conversation)
        metadata = json.dumps(conversation.get('metadata', {}))
        
        cursor.execute('''
            INSERT INTO conversations 
            (id, title, platform, created_at, total_messages, content_hash, metadata, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conversation['id'],
            conversation['titulo'],
            conversation['plataforma'],
            conversation.get('timestamp'),
            len(conversation.get('mensajes', [])),
            content_hash,
            metadata,
            conversation.get('metadata', {}).get('source_file')
        ))
        
        # Insertar mensajes
        for mensaje in conversation.get('mensajes', []):
            self._add_message(cursor, mensaje, conversation['id'])
    
    def _update_conversation(self, cursor, conversation: Dict[str, Any], new_hash: str):
        """Actualiza conversación existente"""
        metadata = json.dumps(conversation.get('metadata', {}))
        
        cursor.execute('''
            UPDATE conversations 
            SET title=?, total_messages=?, content_hash=?, metadata=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (
            conversation['titulo'],
            len(conversation.get('mensajes', [])),
            new_hash,
            metadata,
            conversation['id']
        ))
        
        # Eliminar mensajes antiguos y añadir nuevos
        cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation['id'],))
        
        for mensaje in conversation.get('mensajes', []):
            self._add_message(cursor, mensaje, conversation['id'])
    
    def _calculate_conversation_hash(self, conversation: Dict[str, Any]) -> str:
        """Calcula hash único de una conversación"""
        content_parts = [
            conversation.get('titulo', ''),
            conversation.get('plataforma', ''),
            str(len(conversation.get('mensajes', []))),
        ]
        
        # Agregar hashes de primeros y últimos mensajes
        messages = conversation.get('mensajes', [])
        if messages:
            content_parts.append(messages[0].get('content', ''))
            if len(messages) > 1:
                content_parts.append(messages[-1].get('content', ''))
        
        content_string = '|'.join(content_parts)
        return hashlib.md5(content_string.encode()).hexdigest()
    
    def search_conversations(self, query: str = None, platform: str = None,
                           date_from: str = None, date_to: str = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """
        Busca conversaciones con filtros opcionales.
        
        Args:
            query: Texto a buscar en título o contenido
            platform: Filtrar por plataforma
            date_from: Fecha inicio (YYYY-MM-DD)
            date_to: Fecha fin (YYYY-MM-DD)
            limit: Máximo número de resultados
            
        Returns:
            Lista de conversaciones que coinciden
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Construir query base
            sql_parts = [
                "SELECT c.id, c.title, c.platform, c.created_at, c.total_messages, c.metadata",
                "FROM conversations c"
            ]
            
            conditions = []
            params = []
            
            # Filtrar por query de texto
            if query:
                sql_parts.append("LEFT JOIN messages m ON c.id = m.conversation_id")
                conditions.append("(c.title LIKE ? OR m.content LIKE ?)")
                query_pattern = f"%{query}%"
                params.extend([query_pattern, query_pattern])
            
            # Filtrar por plataforma
            if platform:
                conditions.append("c.platform = ?")
                params.append(platform)
            
            # Filtrar por fecha
            if date_from:
                conditions.append("c.created_at >= ?")
                params.append(date_from)
            
            if date_to:
                conditions.append("c.created_at <= ?")
                params.append(date_to)
            
            # Agregar condiciones WHERE
            if conditions:
                sql_parts.append("WHERE " + " AND ".join(conditions))
            
            # Agrupar si hay JOIN con mensajes
            if query:
                sql_parts.append("GROUP BY c.id")
            
            # Ordenar y limitar
            sql_parts.extend([
                "ORDER BY c.created_at DESC",
                f"LIMIT {limit}"
            ])
            
            sql = " ".join(sql_parts)
            cursor.execute(sql, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'title': row[1],
                    'platform': row[2],
                    'created_at': row[3],
                    'total_messages': row[4],
                    'metadata': json.loads(row[5] or '{}')
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error buscando conversaciones: {e}")
            return []
    
    def get_conversation_details(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene detalles completos de una conversación incluyendo mensajes.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            Conversación completa con mensajes o None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener conversación
            cursor.execute('''
                SELECT id, title, platform, created_at, updated_at, total_messages, metadata, source_file
                FROM conversations WHERE id = ?
            ''', (conversation_id,))
            
            conv_row = cursor.fetchone()
            if not conv_row:
                return None
            
            # Obtener mensajes
            cursor.execute('''
                SELECT id, role, content, timestamp, content_length, metadata
                FROM messages WHERE conversation_id = ?
                ORDER BY timestamp, rowid
            ''', (conversation_id,))
            
            messages = []
            for msg_row in cursor.fetchall():
                messages.append({
                    'id': msg_row[0],
                    'role': msg_row[1],
                    'content': msg_row[2],
                    'timestamp': msg_row[3],
                    'content_length': msg_row[4],
                    'metadata': json.loads(msg_row[5] or '{}')
                })
            
            conn.close()
            
            return {
                'id': conv_row[0],
                'title': conv_row[1],
                'platform': conv_row[2],
                'created_at': conv_row[3],
                'updated_at': conv_row[4],
                'total_messages': conv_row[5],
                'metadata': json.loads(conv_row[6] or '{}'),
                'source_file': conv_row[7],
                'messages': messages
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles de conversación {conversation_id}: {e}")
            return None
    
    def register_file_processing(self, file_path: str, processor: str, 
                                stats: Dict[str, Any]) -> bool:
        """
        Registra el procesamiento de un archivo.
        
        Args:
            file_path: Ruta del archivo procesado
            processor: Nombre del procesador usado
            stats: Estadísticas del procesamiento
            
        Returns:
            True si se registró correctamente
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calcular hash del archivo
            file_hash = self._calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            filename = os.path.basename(file_path)
            
            cursor.execute('''
                INSERT OR REPLACE INTO processed_files 
                (filename, file_path, file_hash, file_size, processor_used, 
                 conversations_extracted, messages_extracted, processing_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename,
                file_path,
                file_hash,
                file_size,
                processor,
                stats.get('conversations_processed', 0),
                stats.get('messages_processed', 0),
                stats.get('processing_time', 0.0),
                'completed'
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error registrando procesamiento de archivo {file_path}: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calcula hash MD5 de un archivo"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def is_file_processed(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica si un archivo ya fue procesado.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Tupla (ya_procesado, info_procesamiento)
        """
        try:
            filename = os.path.basename(file_path)
            file_hash = self._calculate_file_hash(file_path) if os.path.exists(file_path) else ""
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT file_hash, processor_used, conversations_extracted, 
                       messages_extracted, processed_at, status
                FROM processed_files 
                WHERE filename = ?
            ''', (filename,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return False, {}
            
            stored_hash, processor, convs, msgs, processed_at, status = row
            
            info = {
                'processor_used': processor,
                'conversations_extracted': convs,
                'messages_extracted': msgs,
                'processed_at': processed_at,
                'status': status,
                'file_changed': stored_hash != file_hash
            }
            
            # Si el hash cambió, considerar no procesado
            if stored_hash != file_hash:
                return False, info
            
            return True, info
            
        except Exception as e:
            logger.error(f"Error verificando archivo {file_path}: {e}")
            return False, {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas completas de la base de datos.
        
        Returns:
            Diccionario con estadísticas detalladas
        """
        # Usar cache si está disponible y es reciente
        current_time = time.time()
        if (self._stats_cache and 
            current_time - self._cache_timestamp < self._cache_timeout):
            return self._stats_cache
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # Estadísticas básicas
            cursor.execute("SELECT COUNT(*) FROM conversations")
            stats['total_conversations'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats['total_messages'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM concepts")
            stats['total_concepts'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM relationships")
            stats['total_relationships'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM processed_files")
            stats['total_files_processed'] = cursor.fetchone()[0]
            
            # Estadísticas por plataforma
            cursor.execute('''
                SELECT platform, COUNT(*), SUM(total_messages)
                FROM conversations 
                GROUP BY platform
            ''')
            
            platforms = {}
            for row in cursor.fetchall():
                platforms[row[0]] = {
                    'conversations': row[1],
                    'messages': row[2]
                }
            stats['by_platform'] = platforms
            
            # Archivos procesados recientemente
            cursor.execute('''
                SELECT filename, processor_used, conversations_extracted, 
                       messages_extracted, processed_at
                FROM processed_files 
                ORDER BY processed_at DESC 
                LIMIT 10
            ''')
            
            recent_files = []
            for row in cursor.fetchall():
                recent_files.append({
                    'filename': row[0],
                    'processor': row[1],
                    'conversations': row[2],
                    'messages': row[3],
                    'processed_at': row[4]
                })
            stats['recent_files'] = recent_files
            
            # Conceptos más usados
            cursor.execute('''
                SELECT name, category, usage_count, strength
                FROM concepts 
                ORDER BY usage_count DESC, strength DESC 
                LIMIT 10
            ''')
            
            top_concepts = []
            for row in cursor.fetchall():
                top_concepts.append({
                    'name': row[0],
                    'category': row[1],
                    'usage_count': row[2],
                    'strength': row[3]
                })
            stats['top_concepts'] = top_concepts
            
            # Cálculos adicionales
            if stats['total_conversations'] > 0:
                stats['avg_messages_per_conversation'] = round(
                    stats['total_messages'] / stats['total_conversations'], 2
                )
            else:
                stats['avg_messages_per_conversation'] = 0
            
            # Información de base de datos
            cursor.execute("PRAGMA database_list")
            db_info = cursor.fetchone()
            if db_info:
                stats['database_file'] = db_info[2]
                if os.path.exists(db_info[2]):
                    stats['database_size_mb'] = round(
                        os.path.getsize(db_info[2]) / (1024 * 1024), 2
                    )
            
            conn.close()
            
            # Actualizar cache
            self._stats_cache = stats
            self._cache_timestamp = current_time
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def cleanup_database(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Limpia la base de datos eliminando datos duplicados o corruptos.
        
        Args:
            dry_run: Si True, solo reporta qué se eliminaría sin hacerlo
            
        Returns:
            Estadísticas de la limpieza
        """
        stats = {
            'duplicate_conversations': 0,
            'orphaned_messages': 0,
            'invalid_concepts': 0,
            'broken_relationships': 0,
            'actions_taken': []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Encontrar conversaciones duplicadas por hash
            cursor.execute('''
                SELECT content_hash, COUNT(*), GROUP_CONCAT(id)
                FROM conversations 
                WHERE content_hash IS NOT NULL
                GROUP BY content_hash
                HAVING COUNT(*) > 1
            ''')
            
            for row in cursor.fetchall():
                content_hash, count, ids = row
                id_list = ids.split(',')
                duplicates_to_remove = id_list[1:]  # Mantener el primero
                
                stats['duplicate_conversations'] += len(duplicates_to_remove)
                
                if not dry_run:
                    for dup_id in duplicates_to_remove:
                        cursor.execute("DELETE FROM conversations WHERE id = ?", (dup_id,))
                        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (dup_id,))
                    
                stats['actions_taken'].append(f"Removed {len(duplicates_to_remove)} duplicate conversations")
            
            # Encontrar mensajes huérfanos
            cursor.execute('''
                SELECT COUNT(*)
                FROM messages m
                LEFT JOIN conversations c ON m.conversation_id = c.id
                WHERE c.id IS NULL
            ''')
            
            orphaned_count = cursor.fetchone()[0]
            stats['orphaned_messages'] = orphaned_count
            
            if orphaned_count > 0 and not dry_run:
                cursor.execute('''
                    DELETE FROM messages 
                    WHERE conversation_id NOT IN (SELECT id FROM conversations)
                ''')
                stats['actions_taken'].append(f"Removed {orphaned_count} orphaned messages")
            
            # Encontrar conceptos inválidos
            cursor.execute('''
                SELECT COUNT(*)
                FROM concepts
                WHERE name IS NULL OR name = '' OR length(name) < 2
            ''')
            
            invalid_concepts = cursor.fetchone()[0]
            stats['invalid_concepts'] = invalid_concepts
            
            if invalid_concepts > 0 and not dry_run:
                cursor.execute('''
                    DELETE FROM concepts 
                    WHERE name IS NULL OR name = '' OR length(name) < 2
                ''')
                stats['actions_taken'].append(f"Removed {invalid_concepts} invalid concepts")
            
            # Encontrar relaciones rotas
            cursor.execute('''
                SELECT COUNT(*)
                FROM relationships r
                WHERE r.concept_a NOT IN (SELECT name FROM concepts)
                   OR r.concept_b NOT IN (SELECT name FROM concepts)
            ''')
            
            broken_relationships = cursor.fetchone()[0]
            stats['broken_relationships'] = broken_relationships
            
            if broken_relationships > 0 and not dry_run:
                cursor.execute('''
                    DELETE FROM relationships 
                    WHERE concept_a NOT IN (SELECT name FROM concepts)
                       OR concept_b NOT IN (SELECT name FROM concepts)
                ''')
                stats['actions_taken'].append(f"Removed {broken_relationships} broken relationships")
            
            if not dry_run:
                conn.commit()
                # Optimizar base de datos después de la limpieza
                cursor.execute("VACUUM")
                stats['actions_taken'].append("Database optimized with VACUUM")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error en limpieza de base de datos: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        # SQLite se cierra automáticamente, pero podemos limpiar cache
        self._stats_cache = {}
        logger.info("IANAEDatabase cerrada")


# Funciones de utilidad

def create_database(db_path: str = "ianae_memoria.db") -> IANAEDatabase:
    """
    Crea una nueva instancia de base de datos IANAE.
    
    Args:
        db_path: Ruta del archivo de base de datos
        
    Returns:
        Instancia de IANAEDatabase inicializada
    """
    return IANAEDatabase(db_path)

def migrate_database(old_db_path: str, new_db_path: str) -> bool:
    """
    Migra datos de una base de datos antigua a una nueva.
    
    Args:
        old_db_path: Ruta de la base de datos antigua
        new_db_path: Ruta de la nueva base de datos
        
    Returns:
        True si la migración fue exitosa
    """
    try:
        # Implementar lógica de migración aquí
        logger.info(f"Migración de {old_db_path} a {new_db_path} - Por implementar")
        return True
    except Exception as e:
        logger.error(f"Error en migración: {e}")
        return False


# Testing rápido
def test_database():
    """Función de prueba rápida para la base de datos"""
    print("🧪 TESTING IANAEDatabase")
    print("=" * 40)
    
    # Crear base de datos de prueba
    db = IANAEDatabase("test_ianae.db")
    
    # Test conversación de ejemplo
    test_conversation = {
        'id': 'test_conv_1',
        'titulo': 'Conversación de Prueba',
        'plataforma': 'test',
        'timestamp': '2024-01-01T10:00:00Z',
        'mensajes': [
            {
                'id': 'msg_1',
                'role': 'user',
                'content': 'Hola, esto es una prueba',
                'timestamp': '2024-01-01T10:00:00Z'
            },
            {
                'id': 'msg_2', 
                'role': 'assistant',
                'content': 'Hola! Entendido, es una conversación de prueba.',
                'timestamp': '2024-01-01T10:01:00Z'
            }
        ],
        'metadata': {'test': True}
    }
    
    # Añadir conversación
    success = db.add_conversation(test_conversation)
    print(f"Conversación añadida: {success}")
    
    # Obtener estadísticas
    stats = db.get_statistics()
    print(f"Estadísticas: {stats}")
    
    # Buscar conversación
    results = db.search_conversations("prueba")
    print(f"Resultados búsqueda: {len(results)}")
    
    # Limpiar
    db.close()
    if os.path.exists("test_ianae.db"):
        os.remove("test_ianae.db")
    
    print("✅ Test completado")

if __name__ == "__main__":
    test_database()