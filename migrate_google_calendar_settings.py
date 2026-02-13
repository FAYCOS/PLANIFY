import sqlite3
import os

# Database path
db_path = os.path.join(os.getcwd(), 'instance', 'dj_prestations.db')

def migrate_google_settings():
    print(f"Migrating database at {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Columns to add
    columns = [
        ("google_calendar_enabled", "BOOLEAN", "0"),
        ("google_client_id", "VARCHAR(200)", "NULL"),
        ("google_client_secret", "VARCHAR(200)", "NULL")
    ]
    
    for col_name, col_type, default_val in columns:
        try:
            # Check if column exists
            cursor.execute(f"SELECT {col_name} FROM parametres_entreprise LIMIT 1")
            print(f"Column {col_name} already exists.")
        except sqlite3.OperationalError:
            # Add column if it doesn't exist
            print(f"Adding column {col_name}...")
            if default_val == "NULL":
                cursor.execute(f"ALTER TABLE parametres_entreprise ADD COLUMN {col_name} {col_type}")
            else:
                cursor.execute(f"ALTER TABLE parametres_entreprise ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
            print(f"Column {col_name} added successfully.")
            
    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate_google_settings()
