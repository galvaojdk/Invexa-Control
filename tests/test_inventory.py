from app.models.inventory import Product, Category

def test_create_category(client, db_session):
    response = client.post(
        "/inventory/categories",
        data={"name": "Test Category"},
        follow_redirects=False # API might redirect or return JSON, need to check implementation
    )
    # Check if category created in DB
    cat = db_session.query(Category).filter(Category.name == "Test Category").first()
    assert cat is not None
    assert cat.name == "Test Category"

def test_create_product(client, db_session):
    # First create a category
    cat = Category(name="Electronics")
    db_session.add(cat)
    db_session.commit()
    
    response = client.post(
        "/inventory/products",
        data={
            "sku": "TEST-PROD-001",
            "name": "Test Product",
            "description": "A test product description",
            "category_id": cat.id,
            "min_stock": 10,
            "current_stock": 100,
            "unit": "un",
            "is_composite": False,
            "is_primary": True
        },
        follow_redirects=False
    )
    
    # Check redirection or success
    assert response.status_code in [302, 303, 200]
    
    # Check DB
    prod = db_session.query(Product).filter(Product.sku == "TEST-PROD-001").first()
    assert prod is not None
    assert prod.name == "Test Product"
    assert prod.current_stock == 100
    assert prod.unit == "un"

def test_stock_movement_entry(client, db_session):
    # Create product
    cat = Category(name="Raw Materials")
    db_session.add(cat)
    db_session.commit()
    
    prod = Product(
        sku="RAW-001", 
        name="Raw Material 1", 
        category_id=cat.id, 
        current_stock=50,
        unit="kg"
    )
    db_session.add(prod)
    db_session.commit()
    
    # Perform Entry movement
    response = client.post(
        "/movements",
        data={
            "product_id": prod.id,
            "type": "entrada",
            "quantity": 20,
            "reason": "Purchase",
            "sector": "Warehouse A"
        },
        follow_redirects=False
    )
    
    assert response.status_code in [302, 303, 200]
    
    # Verify stock update
    db_session.refresh(prod)
    assert prod.current_stock == 70 # 50 + 20

def test_stock_movement_exit(client, db_session):
    # Create product
    cat = Category(name="Finished Goods")
    db_session.add(cat)
    db_session.commit()
    
    prod = Product(
        sku="FIN-001", 
        name="Finished Product", 
        category_id=cat.id, 
        current_stock=100,
        unit="un"
    )
    db_session.add(prod)
    db_session.commit()
    
    # Perform Exit movement
    response = client.post(
        "/movements",
        data={
            "product_id": prod.id,
            "type": "saida",
            "quantity": 10,
            "reason": "Sale",
            "sector": "Store Front"
        },
        follow_redirects=False
    )
    
    assert response.status_code in [302, 303, 200]
    
    # Verify stock update
    db_session.refresh(prod)
    assert prod.current_stock == 90 # 100 - 10
