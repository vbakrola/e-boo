"""Database backup script using SQLite online backup API with integrity verification."""
import os
import sys
import sqlite3
import argparse
from datetime import datetime, timezone

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app.config import settings


def backup_database(destination_dir: str = "./backups") -> str:
    """Perform safe atomic SQLite online backup without stopping the server."""
    os.makedirs(destination_dir, exist_ok=True)
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    
    if not os.path.exists(db_file):
        raise FileNotFoundError(f"Database file '{db_file}' not found.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(destination_dir, f"lab_manager_backup_{timestamp}.db")

    print(f"Starting online backup from '{db_file}' to '{backup_file}'...")
    src = sqlite3.connect(db_file)
    dst = sqlite3.connect(backup_file)

    with dst:
        src.backup(dst, pages=100)

    # Perform integrity check on the new backup
    cursor = dst.cursor()
    cursor.execute("PRAGMA integrity_check")
    integrity_result = cursor.fetchone()[0]

    dst.close()
    src.close()

    if integrity_result != "ok":
        raise RuntimeError(f"Backup integrity check failed: {integrity_result}")

    size_mb = os.path.getsize(backup_file) / (1024 * 1024)
    print(f"Backup successfully completed! Size: {size_mb:.2f} MB")
    print(f"Integrity check: {integrity_result}")
    return backup_file


def main():
    parser = argparse.ArgumentParser(description="Backup SQLite Database Online")
    parser.add_argument("--out", default="./backups", help="Target backup directory")
    args = parser.parse_args()

    try:
        backup_database(args.out)
    except Exception as e:
        print(f"Error during backup: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
