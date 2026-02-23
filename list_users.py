import sqlite3

def list_users():
    conn = sqlite3.connect('control.db')
    cursor = conn.cursor()
    
    print("\n--- Listing Users ---")
    try:
        cursor.execute("SELECT id, email, is_admin, company_id FROM users")
        users = cursor.fetchall()
        for user in users:
            print(f"ID: {user[0]} | Email: {user[1]} | Admin: {user[2]} | Company: {user[3]}")
    except Exception as e:
        print(f"Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    list_users()
