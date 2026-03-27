import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Fusion.settings.development')
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='central_mess_payments';")
        columns = [row[0] for row in cursor.fetchall()]
        print("Columns in central_mess_payments:", columns)
except Exception as e:
    print("Error:", e)
