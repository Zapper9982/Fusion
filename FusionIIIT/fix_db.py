import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Fusion.settings.development')
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute("ALTER TABLE central_mess_payments ADD COLUMN sem integer;")
        cursor.execute("ALTER TABLE central_mess_payments ALTER COLUMN sem SET DEFAULT 1;")
    print("Column added successfully!")
except Exception as e:
    print("Error:", e)
