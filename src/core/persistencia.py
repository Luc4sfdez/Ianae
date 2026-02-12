import logging
import sqlite3
import numpy as np
import json
import io
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class PersistenciaVectores:
    """
    Clase para guardar y cargar vectores numpy en SQLite con metadatos JSON.
    """
    
    def __init__(self, ruta_db='data/ianae.db'):
        """
        Inicializa la conexión SQLite y crea la tabla si no existe.
        
        Args:
            ruta_db: Ruta al archivo de base de datos SQLite
        """
        self.ruta_db = ruta_db
        
        # Crear directorio data si no existe
        directorio = os.path.dirname(ruta_db)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
        
        self._inicializar_tabla()
    
    def _inicializar_tabla(self):
        """Crea la tabla vectores si no existe."""
        with sqlite3.connect(self.ruta_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS vectores (
                    id_vector TEXT PRIMARY KEY,
                    vector_blob BLOB NOT NULL,
                    metadata TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            ''')
            conn.commit()
    
    def guardar_vector(self, id_vector, vector, metadata=None):
        """
        Guarda un vector numpy y metadatos JSON en la base de datos.
        
        Args:
            id_vector: Identificador único del vector
            vector: Array numpy a guardar
            metadata: Diccionario con metadatos (opcional)
        
        Returns:
            bool: True si se guardó correctamente
        """
        if metadata is None:
            metadata = {}
        
        try:
            # Convertir vector numpy a bytes usando BytesIO
            buffer = io.BytesIO()
            np.save(buffer, vector, allow_pickle=False)
            vector_bytes = buffer.getvalue()
            
            # Convertir metadatos a JSON
            metadata_json = json.dumps(metadata)
            
            # Timestamp actual
            timestamp = datetime.now().timestamp()
            
            with sqlite3.connect(self.ruta_db) as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO vectores (id_vector, vector_blob, metadata, timestamp) VALUES (?, ?, ?, ?)',
                    (id_vector, vector_bytes, metadata_json, timestamp)
                )
                conn.commit()
            
            return True
            
        except Exception as e:
            logger.error("Error guardando vector %s: %s", id_vector, e)
            return False
    
    def cargar_vector(self, id_vector):
        """
        Carga un vector y metadatos por ID.
        
        Args:
            id_vector: Identificador del vector a cargar
        
        Returns:
            tuple: (vector_numpy, metadata_dict) o (None, None) si no existe
        """
        try:
            with sqlite3.connect(self.ruta_db) as conn:
                cursor = conn.execute(
                    'SELECT vector_blob, metadata FROM vectores WHERE id_vector = ?',
                    (id_vector,)
                )
                row = cursor.fetchone()
                
                if row is None:
                    return None, None
                
                vector_bytes, metadata_json = row
                
                # Reconstruir vector desde bytes
                buffer = io.BytesIO(vector_bytes)
                vector = np.load(buffer, allow_pickle=False)
                
                # Reconstruir metadatos desde JSON
                metadata = json.loads(metadata_json)
                
                return vector, metadata
                
        except Exception as e:
            logger.error("Error cargando vector %s: %s", id_vector, e)
            return None, None
    
    def listar_vectores(self, limite=100):
        """
        Lista IDs y metadatos de vectores almacenados.
        
        Args:
            limite: Número máximo de resultados
        
        Returns:
            list: Lista de tuples (id_vector, metadata_dict, timestamp)
        """
        try:
            with sqlite3.connect(self.ruta_db) as conn:
                cursor = conn.execute(
                    'SELECT id_vector, metadata, timestamp FROM vectores ORDER BY timestamp DESC LIMIT ?',
                    (limite,)
                )
                
                resultados = []
                for row in cursor.fetchall():
                    id_vector, metadata_json, timestamp = row
                    metadata = json.loads(metadata_json)
                    resultados.append((id_vector, metadata, timestamp))
                
                return resultados
                
        except Exception as e:
            logger.error("Error listando vectores: %s", e)
            return []
    
    def eliminar_vector(self, id_vector):
        """
        Elimina un vector de la base de datos.
        
        Args:
            id_vector: Identificador del vector a eliminar
        
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            with sqlite3.connect(self.ruta_db) as conn:
                cursor = conn.execute(
                    'DELETE FROM vectores WHERE id_vector = ?',
                    (id_vector,)
                )
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error("Error eliminando vector %s: %s", id_vector, e)
            return False
    
    def contar_vectores(self):
        """
        Cuenta el número total de vectores almacenados.
        
        Returns:
            int: Número de vectores en la base de datos
        """
        try:
            with sqlite3.connect(self.ruta_db) as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM vectores')
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error("Error contando vectores: %s", e)
            return 0
    
    def limpiar_tabla(self):
        """
        Elimina todos los vectores de la base de datos.
        
        Returns:
            bool: True si se limpió correctamente
        """
        try:
            with sqlite3.connect(self.ruta_db) as conn:
                conn.execute('DELETE FROM vectores')
                conn.commit()
                return True
                
        except Exception as e:
            logger.error("Error limpiando tabla: %s", e)
            return False