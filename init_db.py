from app.core.database import engine, Base
from app.models.company import Company
from app.models.inventory import Product, Category, Movement
from app.models.user import User
from app.models.worker import Worker, Shipment
from app.models.worker_type import WorkerType
from app.models.production import ProductionOrder, OPMaterial
from app.core import security
from sqlalchemy.orm import Session

print("Iniciando criação das tabelas...")
Base.metadata.create_all(bind=engine)

# Criar usuário admin padrão
db = Session(engine)
admin = db.query(User).filter(User.email == "admin@invexa.com").first()
if not admin:
    print("Criando usuário admin padrão...")
    hashed_pwd = security.get_password_hash("admin123")
    admin = User(email="admin@invexa.com", hashed_password=hashed_pwd, full_name="Administrador", is_admin=True, is_premium=True)
    db.add(admin)
    db.commit()
    print("Usuário 'admin@invexa.com' com senha 'admin123' criado!")

# Criar categorias padrão
categories = ["Escritório", "Limpeza", "Matéria-prima", "Informática"]
for cat_name in categories:
    cat = db.query(Category).filter(Category.name == cat_name).first()
    if not cat:
        print(f"Criando categoria '{cat_name}'...")
        db.add(Category(name=cat_name))
db.commit()

print("Tabelas e dados iniciais criados com sucesso!")
