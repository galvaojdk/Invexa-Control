
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.getcwd())

from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.inventory import Product, Movement, MovementType
from app.core.security import get_password_hash

# Setup Test Client
client = TestClient(app)

def get_auth_headers():
    # Login to get token
    login_data = {"email": "admin@invexa.com", "password": "senha123"}
    # Ensure admin user exists
    db = SessionLocal()
    user = db.query(User).filter(User.email == "admin@invexa.com").first()
    if not user:
        user = User(
            email="admin@invexa.com", 
            hashed_password=get_password_hash("senha123"), 
            full_name="Admin Test",
            is_active=True, 
            is_admin=True
        )
        db.add(user)
        db.commit()
    db.close()
    
    response = client.post("/login", data=login_data)
    # The login endpoint sets a cookie "access_token"
    # TestClient handles cookies automatically for subsequent requests if we use the same client instance
    # But for explicit headers if needed:
    token = response.cookies.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}

def test_edit_delete():
    print("Starting verification...")
    
    # 1. Login
    client.post("/login", data={"email": "admin@invexa.com", "password": "senha123"})
    print("Logged in.")
    
    # 2. Create Product
    product_data = {
        "name": "Produto Teste ED",
        "description": "Descricao Original",
        "category_id": 1, # Assuming cat 1 exists
        "unit": "Und",
        "min_stock": 10,
        "current_stock": 100
    }
    # Ensure category exists
    db = SessionLocal()
    from app.models.inventory import Category
    cat = db.query(Category).first()
    if not cat:
        cat = Category(name="Geral")
        db.add(cat)
        db.commit()
    product_data["category_id"] = cat.id
    db.close()

    resp = client.post("/inventory/products", data=product_data)
    assert resp.status_code == 303 or resp.status_code == 200
    print("Product created.")
    
    # Get ID
    db = SessionLocal()
    product = db.query(Product).filter(Product.name == "Produto Teste ED").first()
    pid = product.id
    db.close()
    
    # 3. Update Product
    update_data = {
        "name": "Produto Teste ED Alterado",
        "description": "Descricao Nova",
        "category_id": cat.id,
        "unit": "KG",
        "min_stock": 5,
        "is_composite": False,
        "is_primary": True
    }
    resp = client.post(f"/inventory/products/{pid}/update", data=update_data)
    assert resp.status_code == 303
    print("Product updated.")
    
    # Verify Update
    resp = client.get(f"/inventory/products/{pid}")
    # Note: I changed route to /inventory/products/{id} in recent steps
    # But wait, did I change the app.main inclusion? No.
    # main.py includes inventory.router. inventory.router has prefix="/inventory".
    # So route is /inventory/products/{pid} (GET).
    # Wait, in step 404/408 I added `@router.get("/products/{product_id}")`.
    # So full path is `/inventory/products/{pid}`.
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Produto Teste ED Alterado"
    assert data["unit"] == "KG"
    print("Update verified.")
    
    # 4. Add Movement to block delete
    db = SessionLocal()
    mov = Movement(
        product_id=pid,
        quantity=10,
        type=MovementType.IN,
        user_id=1, # Admin
        reason="Teste"
    )
    db.add(mov)
    db.commit()
    db.close()
    print("Movement added.")
    
    # 5. Try Delete (Should Fail)
    resp = client.post(f"/inventory/products/{pid}/delete")
    assert resp.status_code == 400
    print("Delete blocked correctly.")
    
    # 6. Remove Movement
    db = SessionLocal()
    db.query(Movement).filter(Movement.product_id == pid).delete()
    db.commit()
    db.close()
    print("Movement removed.")
    
    # 7. Delete (Should Succeed)
    resp = client.post(f"/inventory/products/{pid}/delete")
    assert resp.status_code == 303
    print("Product deleted.")
    
    # Verify Deletion
    db = SessionLocal()
    p = db.query(Product).filter(Product.id == pid).first()
    assert p is None
    db.close()
    print("Deletion verified.")
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_edit_delete()
