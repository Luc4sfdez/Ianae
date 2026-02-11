"""
Migración 001: Agregar campo workflow_status para tracking de estados
"""

import sqlite3
import os

DB_PATH = os.environ.get("DOCS_DB_PATH", "./orchestra/data/docs.db")


def migrate():
    """Ejecutar migración"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'workflow_status' not in columns:
            print("[MIGRATION] Añadiendo columna workflow_status...")

            # Añadir columna workflow_status
            cursor.execute("""
                ALTER TABLE documents
                ADD COLUMN workflow_status TEXT DEFAULT 'pending'
            """)

            # Crear índice para workflow_status
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_docs_workflow_status
                ON documents(workflow_status)
            """)

            # Inicializar workflow_status basado en status actual
            cursor.execute("""
                UPDATE documents
                SET workflow_status = status
                WHERE workflow_status IS NULL
            """)

            conn.commit()
            print("[MIGRATION] [OK] Columna workflow_status anadida correctamente")
            print("[MIGRATION] [OK] Indice creado")
            print("[MIGRATION] [OK] Datos inicializados")
        else:
            print("[MIGRATION] [SKIP] Columna workflow_status ya existe, saltando migracion")

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION] [ERROR] {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  Migración 001: workflow_status")
    print("=" * 60)
    migrate()
    print("\n[MIGRATION] Completada")
