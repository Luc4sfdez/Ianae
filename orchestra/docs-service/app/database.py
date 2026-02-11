"""
Base de datos SQLite con FTS5 para docs-service IANAE.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path


DB_PATH = os.environ.get("DOCS_DB_PATH", "./orchestra/data/docs.db")


def get_connection():
    """Obtener conexión a la base de datos."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializar esquema de la base de datos."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                author TEXT NOT NULL,
                tags TEXT,
                priority TEXT DEFAULT 'media',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_docs_status ON documents(status);
            CREATE INDEX IF NOT EXISTS idx_docs_category ON documents(category);
            CREATE INDEX IF NOT EXISTS idx_docs_created ON documents(created_at);
            CREATE INDEX IF NOT EXISTS idx_docs_updated ON documents(updated_at);

            -- FTS5 para búsqueda
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title, content, category, tags,
                content='documents',
                content_rowid='id'
            );

            -- Triggers para mantener FTS5 sincronizado
            CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, title, content, category, tags)
                VALUES (new.id, new.title, new.content, new.category, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON documents BEGIN
                DELETE FROM documents_fts WHERE rowid = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON documents BEGIN
                UPDATE documents_fts
                SET title = new.title, content = new.content,
                    category = new.category, tags = new.tags
                WHERE rowid = new.id;
            END;
        """)
        conn.commit()
    finally:
        conn.close()
