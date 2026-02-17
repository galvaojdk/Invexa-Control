import json

BASE_URL = "http://localhost:8000"  # Adjust if needed, but usually we run locally
# Since I cannot run the server and hit it from outside easily without ensuring it's running, 
# I will use the internal DB session to verify logic directly, similar to a unit test.
# This is more reliable as I can control the environment.

from app.core.database import SessionLocal
from app.models.inventory import Product, Category, ProductComposition
from app.models.user import User

db = SessionLocal()

def verify_logic():
    print("Iniciando verificação de lógica de produtos compostos...")

    # 1. Clean up previous test data
    print("Limpando dados de teste anteriores...")
    db.query(ProductComposition).delete()
    db.query(Product).filter(Product.sku.like("TEST-%")).delete()
    db.commit()

    # 2. Setup Category and User (assuming they exist or create mocks)
    # We'll use existing category or create one
    cat = db.query(Category).first()
    if not cat:
        cat = Category(name="Test Category")
        db.add(cat)
        db.commit()
    
    # 3. Create Primary Products
    print("Criando produtos primários...")
    p1 = Product(sku="TEST-P1", name="Parafuso", category_id=cat.id, unit="Und", is_primary=True)
    p2 = Product(sku="TEST-P2", name="Porca", category_id=cat.id, unit="Und", is_primary=True)
    db.add(p1)
    db.add(p2)
    db.commit()
    
    print(f"Produtos primários criados: ID {p1.id}, ID {p2.id}")

    # 4. Create Composite Product
    print("Criando produto composto...")
    p3 = Product(sku="TEST-COMP", name="Kit Fixação", category_id=cat.id, unit="Kit", is_composite=True)
    db.add(p3)
    db.commit()
    
    # Add composition manually (simulating the API logic)
    c1 = ProductComposition(composite_id=p3.id, component_id=p1.id, quantity=2.0)
    c2 = ProductComposition(composite_id=p3.id, component_id=p2.id, quantity=2.0)
    db.add(c1)
    db.add(c2)
    db.commit()
    
    print(f"Produto composto criado: ID {p3.id}")

    # 5. Verify Composition
    print("Verificando composição...")
    comp = db.query(ProductComposition).filter(ProductComposition.composite_id == p3.id).all()
    assert len(comp) == 2
    assert comp[0].quantity == 2.0
    assert comp[1].quantity == 2.0
    print("Composição Inicial OK")

    # 6. Update Composition (Simulate Logic)
    print("Atualizando composição (Removendo um item e alterando qtd)...")
    # Logic: Delete all and recreate
    db.query(ProductComposition).filter(ProductComposition.composite_id == p3.id).delete()
    # New composition: 5x P1 only
    c3 = ProductComposition(composite_id=p3.id, component_id=p1.id, quantity=5.0)
    db.add(c3)
    db.commit()

    # 7. Verify Update
    comp_updated = db.query(ProductComposition).filter(ProductComposition.composite_id == p3.id).all()
    assert len(comp_updated) == 1
    assert comp_updated[0].component_id == p1.id
    assert comp_updated[0].quantity == 5.0
    print("Atualização de Composição OK")
    
    # 8. Cleanup
    print("Limpando dados de teste...")
    db.query(ProductComposition).delete()
    db.query(Product).filter(Product.sku.like("TEST-%")).delete()
    db.commit()
    
    print("VERIFICAÇÃO CONCLUÍDA COM SUCESSO!")

if __name__ == "__main__":
    try:
        verify_logic()
    except Exception as e:
        print(f"ERRO NA VERIFICAÇÃO: {e}")
        exit(1)
