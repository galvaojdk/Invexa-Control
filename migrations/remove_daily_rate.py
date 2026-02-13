import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

def remove_daily_rate():
    if not DATABASE_URL:
        print("DATABASE_URL variable not set. Skipping.")
        return

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        print("Removing daily_rate column from workers table...")
        cursor.execute("ALTER TABLE workers DROP COLUMN IF EXISTS daily_rate")
        
        conn.commit()
        print("Column daily_rate removed successfully.")

    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        print(f"Error removing column: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    remove_daily_rate()
