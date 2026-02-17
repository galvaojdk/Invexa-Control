from app.core.database import engine, Base
from app.models.inventory import ProductComposition

print("Atualizando esquema do banco de dados...")
Base.metadata.create_all(bind=engine)
print("Tabelas atualizadas com sucesso!")
