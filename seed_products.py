from app.core.database import SessionLocal
from app.models.user import User
from app.models.inventory import Product, Category, ProductComposition

def get_or_create_category(db, name):
    cat = db.query(Category).filter(Category.name == name).first()
    if not cat:
        cat = Category(name=name)
        db.add(cat)
        db.commit()
    return cat

def seed_products():
    db = SessionLocal()
    try:
        print("Criando produtos...")

        # 1. Create Category
        materiais = get_or_create_category(db, "Materiais")
        acabados = get_or_create_category(db, "Acabados")

        # 2. Create Primary Products (Components)
        botoes = Product(
            name="Botão",
            description="Botão padrão para camisas",
            unit="un",
            current_stock=1000.0, # Initial stock for testing
            is_composite=False,
            is_primary=True,
            category_id=materiais.id
        )
        manga = Product(
            name="Manga de Camisa",
            description="Manga pronta ou corte de manga",
            unit="un",
            current_stock=500.0,
            is_composite=False,
            is_primary=True,
            category_id=materiais.id
        )
        tecido = Product(
            name="Tecido Branco",
            description="Tecido de algodão branco",
            unit="mt",
            current_stock=200.0,
            is_composite=False,
            is_primary=True,
            category_id=materiais.id
        )

        db.add_all([botoes, manga, tecido])
        db.commit()
        
        # 3. Create Composite Product
        camisa = Product(
            name="Camisa Branca",
            description="Camisa social branca completa",
            unit="un",
            current_stock=0.0,
            is_composite=True,
            is_primary=False,
            category_id=acabados.id
        )
        db.add(camisa)
        db.commit()

        # 4. Define Composition
        # "4 botoes, 2 mangas e 1 metros de tecido bRANCO"
        comps = [
            ProductComposition(composite_id=camisa.id, component_id=botoes.id, quantity=4.0),
            ProductComposition(composite_id=camisa.id, component_id=manga.id, quantity=2.0),
            ProductComposition(composite_id=camisa.id, component_id=tecido.id, quantity=1.0)
        ]
        db.add_all(comps)
        db.commit()

        print("Produtos criados com sucesso!")
        print(f"ID Camisa: {camisa.id}")
        print(f"Composição: 4x {botoes.name}, 2x {manga.name}, 1x {tecido.name}")

    except Exception as e:
        print(f"Erro ao criar produtos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_products()
