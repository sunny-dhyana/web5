import sqlite3

import os

try:
    db_path = os.path.join(os.getcwd(), 'backend', 'data', 'mercury.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE users ADD COLUMN profile_picture_url VARCHAR(500);")
    conn.commit()
    print("Column added successfully.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
