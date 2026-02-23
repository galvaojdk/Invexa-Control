import sqlite3

def migrate():
    conn = sqlite3.connect('control.db')
    cursor = conn.cursor()
    
    tables_to_update = [
        "users", "categories", "products", "movements", 
        "audit_logs", "workers", "worker_types", "shipments", "product_compositions"
    ]
    
    for table in tables_to_update:
        print(f"Migrating table: {table}")
        try:
            # Check if company_id already exists to avoid errors on multiple runs
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'company_id' not in columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN company_id INTEGER REFERENCES companies(id)")
                print(f"  Added company_id to {table}")
            else:
                print(f"  company_id already exists in {table}")
                
        except Exception as e:
            print(f"  Error migrating {table}: {e}")
            
    conn.commit()
    conn.close()
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    migrate()
