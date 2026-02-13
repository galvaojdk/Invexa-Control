import sqlite3
import shutil
import os
from datetime import datetime

DB_PATH = "control.db"
BACKUP_PATH = f"control_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"

def backup_database():
    if os.path.exists(DB_PATH):
        shutil.copy(DB_PATH, BACKUP_PATH)
        print(f"Database backed up to {BACKUP_PATH}")
    else:
        print(f"Database file {DB_PATH} not found.")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Create worker_types table
        print("Creating worker_types table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL UNIQUE
            )
        """)

        # 2. Get distinct roles from workers
        print("Migrating roles to worker_types...")
        cursor.execute("SELECT DISTINCT role FROM workers WHERE role IS NOT NULL AND role != ''")
        roles = cursor.fetchall()
        
        role_map = {}
        for role_tuple in roles:
            role_name = role_tuple[0]
            # Check if type exists
            cursor.execute("SELECT id FROM worker_types WHERE name = ?", (role_name,))
            res = cursor.fetchone()
            if res:
                role_map[role_name] = res[0]
            else:
                cursor.execute("INSERT INTO worker_types (name) VALUES (?)", (role_name,))
                role_map[role_name] = cursor.lastrowid
        
        print(f"Migrated {len(role_map)} roles.")

        # 3. Add new columns to workers if they don't exist
        print("Adding new columns to workers...")
        columns_to_add = [
            ("address", "VARCHAR"),
            ("zip_code", "VARCHAR"),
            ("worker_type_id", "INTEGER REFERENCES worker_types(id)")
        ]

        cursor.execute("PRAGMA table_info(workers)")
        existing_columns = [info[1] for info in cursor.fetchall()]

        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                cursor.execute(f"ALTER TABLE workers ADD COLUMN {col_name} {col_type}")
                print(f"Added column {col_name}")

        # 4. Update workers with type_id
        print("Updating workers with worker_type_id...")
        cursor.execute("SELECT id, role FROM workers WHERE role IS NOT NULL AND role != ''")
        workers = cursor.fetchall()
        for w_id, w_role in workers:
            if w_role in role_map:
                cursor.execute("UPDATE workers SET worker_type_id = ? WHERE id = ?", (role_map[w_role], w_id))
        
        # 5. Commit changes
        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    backup_database()
    migrate()
