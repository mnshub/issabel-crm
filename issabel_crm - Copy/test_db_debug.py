# test_db_debug.py
import os
import sys
import pymysql

# Load Django context configuration exactly how management commands do it
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings

print("\n" + "="*50)
print("     CRM TO ISSABEL MARIADB CONNECTION DEBUGGER     ")
print("="*50)

# 1. Fetch exactly what Django settings currently holds
host = getattr(settings, 'PBX_DB_HOST', 'NOT SET')
user = getattr(settings, 'PBX_DB_USER', 'NOT SET')
database = getattr(settings, 'PBX_DB_NAME', 'asteriskcdrdb')
password = getattr(settings, 'PBX_DB_PASS', '')

print(f"[1] HOST:     {host}")
print(f"[2] USER:     {user}")
print(f"[3] DATABASE: {database}")
print(f"[4] PASSWORD ANALYSIS:")
print(f"    -> Total character length: {len(password)}")
print(f"    -> Contains '!' mark?      {'YES' if '!' in password else 'NO'}")
print(f"    -> Contains 'i' character? {'YES' if 'i' in password else 'NO'}")
print(f"    -> Raw password read is:   \"{password}\"")
print("-"*50)

# 2. Test the connection
print("[5] Attempting network handshake with Issabel server...")
try:
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        connect_timeout=5
    )
    print("\n✅ SUCCESS! Connection established perfectly.")
    connection.close()
except pymysql.err.OperationalError as e:
    print(f"\n❌ CONNECTION REFUSED BY DATABASE SERVER:")
    print(f"   Error Code: {e.args[0]}")
    print(f"   Error Msg:  {e.args[1]}")
except Exception as e:
    print(f"\n❌ UNEXPECTED PACKET ERROR: {e}")

print("="*50 + "\n")