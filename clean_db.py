from app.core.database import SessionLocal, engine, Base
from sqlalchemy import text

def clean_database():
    db = SessionLocal()
    try:
        print("Iniciando limpeza do banco de dados (preservando usuarios)...")
        
        # Disable foreign key constraints appropriately for SQLite
        if 'sqlite' in str(engine.url):
            db.execute(text("PRAGMA foreign_keys = OFF"))
        
        # Order matters if FKs were on, but with OFF it's easier.
        # Still good practice to delete children first.
        
        tables_to_clean = [
            "audit_logs",
            "movements",
            "shipments",
            "product_compositions",
            "products",
            "workers",
            "worker_types",
            "categories"
        ]
        
        for table in tables_to_clean:
            print(f"Limpando tabela: {table}...")
            try:
                db.execute(text(f"DELETE FROM {table}"))
                db.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'")) # Reset IDs in SQLite
            except Exception as e:
                print(f"Erro ao limpar {table}: {e}")
                
        db.commit()
        
        if 'sqlite' in str(engine.url):
             db.execute(text("PRAGMA foreign_keys = ON"))
             
        print("Limpeza concluida com sucesso!")
        
    except Exception as e:
        print(f"Erro critico: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clean_database()
