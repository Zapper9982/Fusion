
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Fusion.settings.development')
django.setup()

from django.contrib.auth.models import User
from applications.globals.models import ExtraInfo, DepartmentInfo

def fix_user():
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No superuser found. Please create one first.")
        return

    dept = DepartmentInfo.objects.first()
    if not dept:
        # Create a dummy department if none exists
        dept = DepartmentInfo.objects.create(name='CSE')
        print("Created dummy department 'CSE'")

    extrainfo, created = ExtraInfo.objects.get_or_create(
        user=user,
        defaults={
            'user_type': 'faculty',
            'id': '9999',
            'sex': 'M',
            'age': 30,
            'department': dept
        }
    )

    if created:
        print(f"Successfully created ExtraInfo for user: {user.username}")
    else:
        # Update if it somehow exists but is broken
        extrainfo.department = dept
        extrainfo.user_type = 'faculty'
        extrainfo.save()
        print(f"Updated existing ExtraInfo for user: {user.username}")

if __name__ == "__main__":
    fix_user()
