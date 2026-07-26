import sqlite3
import os

DATABASE = "instance/wareflow.db"


def migrate():

    if not os.path.exists(DATABASE):
        print("Database not found.")
        return

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(product)")
    columns = [row[1] for row in cursor.fetchall()]

    print("Existing columns:", columns)

    if "category" not in columns:
        cursor.execute(
            "ALTER TABLE product ADD COLUMN category VARCHAR(50) DEFAULT 'General'"
        )

    if "quantity" not in columns:
        cursor.execute(
            "ALTER TABLE product ADD COLUMN quantity INTEGER DEFAULT 0"
        )

    if "supplier" not in columns:
        cursor.execute(
            "ALTER TABLE product ADD COLUMN supplier VARCHAR(100) DEFAULT 'Unknown'"
        )

    if "created_at" not in columns:
        cursor.execute(
            "ALTER TABLE product ADD COLUMN created_at DATETIME"
        )

    cursor.execute("""
        UPDATE product
        SET category = 'General'
        WHERE category IS NULL
    """)

    cursor.execute("""
        UPDATE product
        SET quantity = 0
        WHERE quantity IS NULL
    """)

    cursor.execute("""
        UPDATE product
        SET supplier = 'Unknown'
        WHERE supplier IS NULL
    """)

    cursor.execute("""
        UPDATE product
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
    """)

    connection.commit()
    connection.close()

    print("Phase 2 database migration completed.")


if __name__ == "__main__":
    migrate()