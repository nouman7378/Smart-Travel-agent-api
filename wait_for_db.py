"""
Utility script to wait for PostgreSQL database to be fully up and running before migrating on Fly.io.
"""
import os
import sys
import time
import django

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connections
from django.db.utils import OperationalError

def wait_for_db():
    print("🚀 SmartTravel Deployment: Waiting for database (PostgreSQL) to accept connections...")
    max_retries = 15
    for attempt in range(1, max_retries + 1):
        try:
            # Try to connect to the default database
            db_conn = connections['default']
            db_conn.ensure_connection()
            print("✅ Database is ready and fully operational!")
            sys.exit(0)
        except OperationalError as e:
            err_msg = str(e)
            print(f"⚠️ [Attempt {attempt}/{max_retries}] Database not ready yet ({err_msg}). Retrying in 2 seconds...")
            time.sleep(2)
            
    print("❌ Fatal: Database did not become ready in time. Exiting with error.")
    sys.exit(1)

if __name__ == '__main__':
    wait_for_db()
