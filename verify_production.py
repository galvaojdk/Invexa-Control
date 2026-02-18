import requests
import time
import sys
import re

BASE_URL = "http://localhost:8000"
# Dynamic user to ensure clean state
TIMESTAMP = int(time.time())
USERNAME = f"teste_{TIMESTAMP}@teste.com"
PASSWORD = "teste"

def login():
    session = requests.Session()
    print(f"Attempting logic at {BASE_URL} with user {USERNAME}")

    try:
        # 1. Register (Always new user)
        try:
            print("Registering test user...")
            reg_resp = session.post(f"{BASE_URL}/register", data={
                "full_name": "Admin Test",
                "email": USERNAME,
                "password": PASSWORD
            })
            print(f"Register Response: {reg_resp.status_code}")
        except Exception as e:
            print(f"Registration failed: {e}")
            sys.exit(1)

        # 2. Login
        print(f"Logging in as {USERNAME}...")
        response = session.post(f"{BASE_URL}/login", data={"email": USERNAME, "password": PASSWORD})
        
        # Final Check
        if response.status_code == 200 and "E-mail ou senha incorretos" not in response.text and not response.url.endswith("/login"):
             print("[OK] Login successful")
             return session
        else:
             print(f"[FAIL] Login failed. Status: {response.status_code}, URL: {response.url}")
             sys.exit(1)

    except Exception as e:
        print(f"[FAIL] Connection error: {e}")
        sys.exit(1)

def verify_production(session):
    print("--- Setting up Data ---")
    
    # 1. Create Component (Fabric)
    # Use unique name to avoid conflict if run multiple times without cleanup
    timestamp = int(time.time())
    comp_name = f"Tecido Teste {timestamp}"
    
    resp = session.post(f"{BASE_URL}/inventory/products", data={
        "name": comp_name,
        "category_id": 1, 
        "unit": "m",
        "is_primary": "true", 
        "is_composite": "false",
        "current_stock": 100
    })
    print(f"Create Component '{comp_name}': {resp.status_code}")
    
    # Get Component ID by searching in inventory HTML
    resp = session.get(f"{BASE_URL}/inventory?tab=products")
    content = resp.text
    
    # Regex to find ID associated with name
    # Looking for deleteProduct(ID, 'Name')
    match = re.search(fr"deleteProduct\((\d+),\s*'{comp_name}'\)", content)
    if not match:
        print(f"[FAIL] Could not find created component ID for {comp_name}")
        return
    
    component_id = match.group(1)
    print(f"Component ID: {component_id}")

    # 1.5. Add Stock to Component
    # Since creation defaults to 0, we need to add stock via movement
    resp = session.post(f"{BASE_URL}/movements", data={
        "product_id": component_id,
        "quantity": 100,
        "type": "entrada",
        "reason": "Estoque Inicial Teste",
        "sector": "Depósito"
    })
    print(f"Add Stock Component: {resp.status_code}")
    if resp.status_code != 303 and resp.status_code != 200:
         print(f"Add Stock Error: {resp.text}")
    composite_name = f"Blusa Teste {timestamp}"
    
    resp = session.post(f"{BASE_URL}/inventory/products", data={
        "name": composite_name,
        "category_id": 1,
        "unit": "un",
        "is_primary": "false",
        "is_composite": "true",
        "current_stock": 0,
        "composition_data": f'[{{"id": {component_id}, "quantity": 1.5}}]' # 1.5m per blouse
    })
    print(f"Create Composite '{composite_name}': {resp.status_code}")
    
    # Get Composite ID
    resp = session.get(f"{BASE_URL}/inventory?tab=products")
    content = resp.text
    match = re.search(fr"deleteProduct\((\d+),\s*'{composite_name}'\)", content)
    if not match:
        print(f"[FAIL] Could not find created composite ID for {composite_name}")
        return
    composite_id = match.group(1)
    print(f"Composite ID: {composite_id}")

    # 3. Create Worker
    # First create a worker type
    type_name = "Costura"
    # Check if exists or create
    # Just try to create, if fails (400) it exists.
    # But we need the ID.
    # Let's clean up: create a unique type or just assume ID 1 if lazy? 
    # Better: List types and pick one or create.
    # Since we don't have easy JSON API for list, let's just create one with unique name.
    type_name = f"Costura {timestamp}"
    resp = session.post(f"{BASE_URL}/workers/types/create", data={"name": type_name})
    print(f"Create Worker Type '{type_name}': {resp.status_code}")
    
    # Get Worker Type ID
    resp = session.get(f"{BASE_URL}/workers")
    content = resp.text
    # Search for type in some list? The workers view lists types in a modal or similar?
    # workers.html passes "worker_types".
    # Regex for <option value="ID">NAME</option> inside the worker creation modal?
    # Or just look for the create/edit type forms?
    # Assuming standard option pattern: <option value="(\d+)">Costura ...</option>
    match = re.search(fr'<option value="(\d+)">{type_name}</option>', content)
    if not match:
         print(f"[FAIL] Could not find created worker type ID for {type_name}")
         # Attempt to find ANY type
         match = re.search(r'<option value="(\d+)">.*?</option>', content)
         if not match:
              print("[FAIL] No worker types found at all.")
              return
         print("[WARN] Using first available worker type.")
    
    worker_type_id = match.group(1)
    print(f"Worker Type ID: {worker_type_id}")

    worker_name = f"Costureira Teste {timestamp}"
    resp = session.post(f"{BASE_URL}/workers/create", data={
        "name": worker_name,
        "worker_type_id": worker_type_id,
        "phone": "123456789"
    })
    print(f"Create Worker '{worker_name}': {resp.status_code}")
    
    # Get Worker ID
    resp = session.get(f"{BASE_URL}/workers")
    content = resp.text
    
    # Try to find ID.
    # Pattern: openEditWorkerModal('ID', 'Name'...)
    # Regex needs to be flexible for quotes and spacing
    # HTML: onclick="openEditWorkerModal('1', 'Name', ...)"
    match = re.search(fr"openEditWorkerModal\('(\d+)',\s*'{worker_name}'", content)
    if not match:
         print(f"[FAIL] Could not find created worker ID for {worker_name}")
         # Attempt fallback: find any edit button? No, needs to be specific.
         # Maybe the name is truncated or formatted differently?
         # Let's try searching just the name and looking around it.
         print("Debug: Content snippet around name:")
         start = content.find(worker_name)
         if start != -1:
             print(content[start-100:start+200])
         return
    
    worker_id = match.group(1)
    print(f"Worker ID: {worker_id}")

    # 4. Send Shipment (Component to Worker)
    # Send 15 meters
    resp = session.post(f"{BASE_URL}/shipments/create", data={
        "worker_id": worker_id,
        "product_id": component_id,
        "quantity": 15, 
        "cost_per_unit": 0
    })
    print(f"Create Shipment: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Shipment Error: {resp.text}")

    # 5. Register Production
    # Produce 5 Blouses. Should consume 5 * 1.5 = 7.5 meters.
    print("--- Registering Production ---")
    resp = session.post(f"{BASE_URL}/production/register", data={
        "worker_id": worker_id,
        "product_id": composite_id,
        "quantity": 5
    })
    print(f"Register Production Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    
    if resp.status_code != 200:
        print("[FAIL] Production registration failed")
        return

    # 6. Verify Results
    print("--- Verifying Results ---")
    
    # Check Finished Good Stock
    # Should be 5
    # We can check via API/HTML or helper endpoint
    resp = session.get(f"{BASE_URL}/inventory/products/{composite_id}")
    if resp.status_code == 200:
        data = resp.json()
        stock = data.get("current_stock")
        print(f"Composite Stock: {stock} (Expected: 5.0)")
        if float(stock) == 5.0:
             print("[PASS] Finished Good Stock Correct")
        else:
             print("[FAIL] Finished Good Stock Incorrect")
    else:
        print("[WARN] Could not fetch product details JSON")

    print("[DONE] Script finished.")

if __name__ == "__main__":
    session = login()
    verify_production(session)
