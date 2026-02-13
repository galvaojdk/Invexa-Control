import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    if not DATABASE_URL:
        print("DATABASE_URL variable not set. Skipping migration.")
        return

    try:
        # Parse connection URL if needed, or pass directly commonly supported by psycopg2
        # Render DATABASE_URL format: postgres://user:pass@host/dbname
        # SQLAlchemy requires postgresql:// but psycopg2 is fine with postgres:// usually, 
        # but let's be safe and replace if needed for some libs, though psycopg2 connect takes url directly.
        
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 1. Create worker_types table
        print("Creating worker_types table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE
            );
        """)

        # 2. Get distinct roles from workers
        print("Migrating roles to worker_types...")
        # Check if column role exists first to avoid error if re-running after drop (though we don't drop)
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='workers' AND column_name='role';
        """)
        if cursor.fetchone():
            cursor.execute("SELECT DISTINCT role FROM workers WHERE role IS NOT NULL AND role != ''")
            roles = cursor.fetchall()
            
            role_map = {}
            for role_tuple in roles:
                role_name = role_tuple[0]
                # Check if type exists
                cursor.execute("SELECT id FROM worker_types WHERE name = %s", (role_name,))
                res = cursor.fetchone()
                if res:
                    role_map[role_name] = res[0]
                else:
                    cursor.execute("INSERT INTO worker_types (name) VALUES (%s) RETURNING id", (role_name,))
                    role_type_id = cursor.fetchone()[0]
                    role_map[role_name] = role_type_id
            
            print(f"Migrated {len(role_map)} roles.")
        else:
            print("Column 'role' not found in workers (already dropped?), skipping role migration.")
            roles = []

        # 3. Add new columns to workers if they don't exist
        print("Adding new columns to workers...")
        cursor.execute("ALTER TABLE workers ADD COLUMN IF NOT EXISTS address VARCHAR")
        cursor.execute("ALTER TABLE workers ADD COLUMN IF NOT EXISTS zip_code VARCHAR")
        cursor.execute("ALTER TABLE workers ADD COLUMN IF NOT EXISTS worker_type_id INTEGER REFERENCES worker_types(id)")

        # 4. Update workers with type_id
        if roles:
            print("Updating workers with worker_type_id...")
            # We need to fetch workers again to update them
            cursor.execute("SELECT id, role FROM workers WHERE role IS NOT NULL AND role != ''")
            workers = cursor.fetchall()
            for w_id, w_role in workers:
                if w_role in role_map:
                    cursor.execute("UPDATE workers SET worker_type_id = %s WHERE id = %s", (role_map[w_role], w_id))

        # 5. Commit changes
        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    migrate()
