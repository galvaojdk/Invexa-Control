import requests

import sys

BASE_URL = "http://localhost:8000"
USERNAME = "admin@invexa.com"
PASSWORD = "admin"

def login():
    session = requests.Session()
    try:
        response = session.post(f"{BASE_URL}/login", data={"email": USERNAME, "password": PASSWORD})
        if response.status_code == 200:
            print("[OK] Login successful")
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
            
            # Check if headers exist directly in text
            if "Relatório de Review de Terceirizados" in response.text:
                 print("[OK] Report title found")
            else:
                 print("[FAIL] Report title NOT found")
            
            # Check table headers
            if "Total Enviado" in response.text and "Saldo (A Devolver)" in response.text:
                print("[OK] Table headers found")
            else:
                print("[FAIL] Table headers NOT found")

            # Check for worker name if any data exists (optional)
            
        else:
            print(f"[FAIL] Failed to load report page: {response.status_code}")
            
    except Exception as e:
        print(f"[FAIL] Error verifying report: {e}")

def debug_response(session):
    print("Debugging response...")
    response = session.get(f"{BASE_URL}/reports?report_type=worker_review")
    print(f"Status Code: {response.status_code}")
    print("Response snippet (first 1000 chars):")
    print(response.text[:1000])
    print("Searching for specific strings again...")
    if "Review de Terceirizados" in response.text:
        print("FOUND: Review de Terceirizados")
    else:
        print("NOT FOUND: Review de Terceirizados")

if __name__ == "__main__":
    session = login()
    # verify_report(session)
    debug_response(session)
