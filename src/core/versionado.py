"""
Versionado de estados persistentes para IANAE.

Permite guardar snapshots con version, timestamp y metadata,
y cargar/listar versiones anteriores.
"""
import time
import hashlib
import json
import sqlite3
from typing import List, Dict, Optional, Any


class VersionadoEstado:
    """
    Sistema de versionado sobre PersistenciaVectores.

    Cada snapshot se guarda con un version_id auto-incremental,
    timestamp, hash del estado, y metadata descriptiva.
    """

    def __init__(self, db_path: str = "ianae_versiones.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS versiones (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    estado_hash TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    num_conceptos INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS version_datos (
                    version_id INTEGER NOT NULL,
                    concepto TEXT NOT NULL,
                    vector TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    PRIMARY KEY (version_id, concepto),
                    FOREIGN KEY (version_id) REFERENCES versiones(version_id)
                )
            """)
            conn.commit()

    @staticmethod
    def _hash_estado(conceptos: Dict) -> str:
        """Hash reproducible del estado de conceptos."""
        claves = sorted(conceptos.keys())
        h = hashlib.md5()
        for c in claves:
            h.update(c.encode())
        return h.hexdigest()[:12]

    def guardar_con_version(self, nombre: str, conceptos: Dict[str, Dict],
                            metadata: Optional[Dict] = None) -> int:
        """
        Guardar snapshot versionado.

        Args:
            nombre: nombre descriptivo del snapshot
            conceptos: dict de conceptos (nombre -> data con 'actual')
            metadata: metadata adicional

        Returns:
            version_id asignado
        """
        meta = metadata or {}
        estado_hash = self._hash_estado(conceptos)
        ts = time.time()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO versiones (nombre, timestamp, estado_hash, metadata, num_conceptos) "
                "VALUES (?, ?, ?, ?, ?)",
                (nombre, ts, estado_hash, json.dumps(meta), len(conceptos))
            )
            vid = cursor.lastrowid

            for concepto_nombre, data in conceptos.items():
                vec = data.get('actual', data.get('base'))
                vec_json = json.dumps(vec.tolist() if hasattr(vec, 'tolist') else list(vec))
                concepto_meta = json.dumps({
                    "categoria": data.get("categoria", ""),
                    "fuerza": data.get("fuerza", 1.0),
                })
                conn.execute(
                    "INSERT INTO version_datos (version_id, concepto, vector, metadata) "
                    "VALUES (?, ?, ?, ?)",
                    (vid, concepto_nombre, vec_json, concepto_meta)
                )
            conn.commit()

        return vid

    def cargar_version(self, version_id: int) -> Optional[Dict]:
        """
        Cargar datos de una version especifica.

        Returns:
            Dict con {nombre, timestamp, metadata, conceptos: {nombre: vector_list}}
            o None si no existe.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT nombre, timestamp, metadata FROM versiones WHERE version_id = ?",
                (version_id,)
            ).fetchone()
            if not row:
                return None

            conceptos = {}
            for drow in conn.execute(
                "SELECT concepto, vector, metadata FROM version_datos WHERE version_id = ?",
                (version_id,)
            ).fetchall():
                conceptos[drow[0]] = {
                    "vector": json.loads(drow[1]),
                    "metadata": json.loads(drow[2]),
                }

            return {
                "version_id": version_id,
                "nombre": row[0],
                "timestamp": row[1],
                "metadata": json.loads(row[2]),
                "conceptos": conceptos,
            }

    def listar_versiones(self, limite: int = 50) -> List[Dict]:
        """Listar versiones ordenadas por timestamp descendente."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT version_id, nombre, timestamp, estado_hash, metadata, num_conceptos "
                "FROM versiones ORDER BY timestamp DESC LIMIT ?",
                (limite,)
            ).fetchall()

        return [
            {
                "version_id": r[0],
                "nombre": r[1],
                "timestamp": r[2],
                "estado_hash": r[3],
                "metadata": json.loads(r[4]),
                "num_conceptos": r[5],
            }
            for r in rows
        ]

    def contar_versiones(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM versiones").fetchone()[0]
