import requests
import sys

BASE_URL = "http://localhost:8000"
# Use a new user to avoid conflict if possible, or handle existing
USERNAME = "test_reviewer@invexa.com"
PASSWORD = "password123"

def register():
    print(f"Registering user {USERNAME}...")
    session = requests.Session()
    try:
        # Corrected URL: no /auth prefix
        response = session.post(f"{BASE_URL}/register", data={
            "full_name": "Test Reviewer",
            "email": USERNAME,
            "password": PASSWORD
        })
        # If it redirects to login or returns 200, it's likely fine.
        # Check if we got an error or just redirected.
        if response.status_code in [200, 303]:
             print("[INFO] Register request completed (might be redirected to login)")
             return True
        else:
             print(f"[WARN] Register returned {response.status_code}")
             # It might fail if user exists, which is fine, we try to login then.
             return True 
    except Exception as e:
        print(f"[WARN] Register error: {e}")
        return False

def login():
    print(f"Logging in as {USERNAME}...")
    session = requests.Session()
    try:
        response = session.post(f"{BASE_URL}/login", data={"email": USERNAME, "password": PASSWORD})
        
        # Check if we are still on login page (simple check for input name="email")
        if 'name="email"' in response.text and 'action="/login"' in response.text:
             print("[FAIL] Login failed - Still on login page.")
             # Print a snippet of the page to debug
             # print(response.text[:500])
             sys.exit(1)
             
        if response.status_code == 200:
            print("[OK] Login successful (dashboard reached or redirected)")
            return session
        else:
            print(f"[FAIL] Login failed: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Connection error: {e}")
        sys.exit(1)

def verify_report(session):
    print("Verifying Review Report...")
    try:
        response = session.get(f"{BASE_URL}/reports?report_type=worker_review")
        
        if response.status_code == 200:
            print("[OK] Report page request successful")
            
            # Check for strings
            if "Relatório de Review de Terceirizados" in response.text:
                 print("[OK] Report title found")
            else:
                 print("[FAIL] Report title NOT found")
                 
            if "Total Enviado" in response.text and "Saldo (A Devolver)" in response.text:
                print("[OK] Table headers found")
            else:
                print("[FAIL] Table headers NOT found")
            
        else:
            print(f"[FAIL] Failed to load report page: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Error verifying report: {e}")

if __name__ == "__main__":
    register()
    session = login()
    verify_report(session)
