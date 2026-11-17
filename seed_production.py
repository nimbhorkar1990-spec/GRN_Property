"""
Production database initialiser.
Run once after deploying to a new server:
    python seed_production.py

- Creates all tables if they don't exist.
- Does NOT overwrite existing records.
- Safe to re-run at any time.
"""
import os
import database as db
from config import Config

def main():
    # Ensure the database directory exists on the production server
    os.makedirs(Config.DATABASE_DIR, exist_ok=True)

    print(f"Database path: {Config.DATABASE}")
    print("Initialising database schema...")
    db.init_db()

    print("Running migrations (safe, additive only)...")
    db.migrate_db()

    print("Done. Database is ready.")

if __name__ == '__main__':
    main()

