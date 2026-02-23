import sqlite3

def check_db():
    conn = sqlite3.connect('control.db')
    cursor = conn.cursor()
    
    tables = [
        "companies", "users", "categories", "products", "movements", 
        "audit_logs", "workers", "worker_types", "shipments", "product_compositions"
    ]
    
    for table in tables:
        print(f"\n--- Table: {table} ---")
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            if not columns:
                print("Table does not exist.")
            else:
                for col in columns:
                    print(f"Column: {col[1]} ({col[2]})")
        except Exception as e:
            print(f"Error: {e}")
            
    conn.close()

if __name__ == "__main__":
    check_db()
