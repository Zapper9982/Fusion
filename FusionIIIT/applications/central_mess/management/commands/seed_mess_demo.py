from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from applications.academic_information.models import Student
from applications.central_mess.models import (
    Feedback,
    Menu,
    MessBillBase,
    Mess_reg,
    Messinfo,
    Monthly_bill,
    PaymentUpdateRequest,
    Payments,
    RegistrationRequest,
    Rebate,
    Special_request,
)
from applications.globals.models import DepartmentInfo, Designation, ExtraInfo, Faculty, HoldsDesignation


MENU_TEMPLATE = {
    "MB": "Poha, Banana, Tea",
    "ML": "Rice, Dal, Paneer Curry",
    "MD": "Chapati, Mixed Veg, Kheer",
    "TB": "Aloo Paratha, Curd",
    "TL": "Jeera Rice, Rajma, Salad",
    "TD": "Chapati, Chole, Gulab Jamun",
    "WB": "Upma, Coconut Chutney",
    "WL": "Rice, Sambar, Potato Fry",
    "WD": "Chapati, Dal Tadka, Halwa",
    "THB": "Idli, Sambar",
    "THL": "Veg Pulao, Raita, Dal",
    "THD": "Chapati, Kofta Curry, Rice",
    "FB": "Sandwich, Milk",
    "FL": "Rice, Kadhi, Mix Veg",
    "FD": "Noodles, Manchurian",
    "SB": "Poori, Sabzi",
    "SL": "Veg Biryani, Raita",
    "SD": "Chapati, Dal Makhani, Rice",
    "SUB": "Dosa, Chutney",
    "SUL": "Fried Rice, Chili Paneer",
    "SUD": "Pulao, Shahi Paneer, Dessert",
}


class Command(BaseCommand):
    help = "Seed demo users and sample data for the mess management presentation."

    def handle(self, *args, **options):
        today = timezone.now().date()
        department, _ = DepartmentInfo.objects.get_or_create(name="CSE")

        student_designation, _ = Designation.objects.get_or_create(
            name="student",
            defaults={"full_name": "Student", "type": "academic"},
        )
        mess_manager_designation, _ = Designation.objects.get_or_create(
            name="mess_manager",
            defaults={"full_name": "Mess Manager", "type": "administrative"},
        )
        mess_warden_designation, _ = Designation.objects.get_or_create(
            name="mess_warden",
            defaults={"full_name": "Mess Warden", "type": "administrative"},
        )

        registered_student = self._create_student(
            username="22BCS001",
            first_name="Aarav",
            last_name="Sharma",
            department=department,
            designation=student_designation,
        )
        applicant_student = self._create_student(
            username="22BCS002",
            first_name="Diya",
            last_name="Verma",
            department=department,
            designation=student_designation,
        )
        manager_user = self._create_faculty(
            username="teacher.demo",
            first_name="Ritika",
            last_name="Sen",
            department=department,
            designation=mess_manager_designation,
        )
        warden_user = self._create_faculty(
            username="warden.demo",
            first_name="Manish",
            last_name="Rao",
            department=department,
            designation=mess_warden_designation,
        )

        for mess_option in ("mess1", "mess2"):
            for meal_time, dish in MENU_TEMPLATE.items():
                Menu.objects.update_or_create(
                    mess_option=mess_option,
                    meal_time=meal_time,
                    defaults={"dish": dish if mess_option == "mess1" else "{} (NV Counter)".format(dish)},
                )

        Mess_reg.objects.update_or_create(
            sem=4,
            defaults={
                "start_reg": today - timedelta(days=2),
                "end_reg": today + timedelta(days=10),
            },
        )
        MessBillBase.objects.get_or_create(bill_amount=3200)
        Messinfo.objects.update_or_create(
            student_id=registered_student,
            defaults={"mess_option": "mess1"},
        )
        Monthly_bill.objects.update_or_create(
            student_id=registered_student,
            month=today.strftime("%B"),
            year=today.year,
            defaults={
                "amount": 3200,
                "rebate_count": 2,
                "rebate_amount": 220,
                "nonveg_total_bill": 0,
                "total_bill": 2980,
            },
        )
        Payments.objects.update_or_create(
            student_id=registered_student,
            sem=4,
            year=today.year,
            defaults={
                "amount_paid": 2500,
                "payment_date": today - timedelta(days=5),
                "payment_month": today.strftime("%B"),
                "payment_year": today.year,
                "status": "accept",
                "Txn_no": "TXN-DEMO-PAID-1",
            },
        )

        RegistrationRequest.objects.update_or_create(
            student_id=applicant_student,
            Txn_no="TXN-DEMO-REG-1",
            defaults={
                "mess_option": "mess2",
                "start_date": today + timedelta(days=2),
                "payment_date": today,
                "amount": 3200,
                "registration_remark": "Demo registration request",
                "status": "pending",
            },
        )
        Rebate.objects.update_or_create(
            student_id=registered_student,
            start_date=today + timedelta(days=4),
            end_date=today + timedelta(days=6),
            defaults={
                "purpose": "Demo outstation visit",
                "status": "1",
                "app_date": today,
                "leave_type": "casual",
                "rebate_remark": "",
            },
        )
        Special_request.objects.update_or_create(
            student_id=registered_student,
            start_date=today + timedelta(days=3),
            end_date=today + timedelta(days=3),
            defaults={
                "request": "Light meal required for recovery",
                "item1": "Khichdi",
                "item2": "Lunch",
                "status": "1",
                "app_date": today,
                "special_request_remark": "",
            },
        )
        PaymentUpdateRequest.objects.update_or_create(
            student_id=registered_student,
            Txn_no="TXN-DEMO-UPD-1",
            defaults={
                "payment_date": today - timedelta(days=1),
                "amount": 480,
                "update_remark": "Please reconcile this extra payment",
                "status": "pending",
            },
        )
        Feedback.objects.update_or_create(
            student_id=registered_student,
            fdate=today - timedelta(days=1),
            defaults={
                "mess": "mess1",
                "mess_rating": 4,
                "description": "Food quality has improved, but breakfast service can be faster during rush hour.",
                "feedback_type": "Food",
                "is_read": False,
            },
        )

        self.stdout.write(self.style.SUCCESS("Mess demo data is ready."))
        self.stdout.write("Student (registered): 22BCS001 / demo123")
        self.stdout.write("Student (registration flow): 22BCS002 / demo123")
        self.stdout.write("Teacher / mess manager: teacher.demo / demo123")
        self.stdout.write("Mess warden: warden.demo / demo123")

    def _create_student(self, username, first_name, last_name, department, designation):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": "{}@example.com".format(username.lower()),
            },
        )
        user.set_password("demo123")
        user.save()

        extrainfo, _ = ExtraInfo.objects.get_or_create(
            id=username,
            defaults={
                "user": user,
                "user_type": "student",
                "department": department,
                "title": "Mr.",
                "sex": "M",
            },
        )
        if extrainfo.user_id != user.id:
            extrainfo.user = user
            extrainfo.user_type = "student"
            extrainfo.department = department
            extrainfo.save()

        student, _ = Student.objects.get_or_create(
            id=extrainfo,
            defaults={
                "programme": "B.Tech",
                "batch": 2022,
                "cpi": 8.2,
                "category": "GEN",
                "father_name": "Demo Father",
                "mother_name": "Demo Mother",
                "hall_no": 1,
                "room_no": "A-101",
                "specialization": "None",
                "curr_semester_no": 4,
            },
        )

        HoldsDesignation.objects.get_or_create(
            user=user,
            working=user,
            designation=designation,
        )
        return student

    def _create_faculty(self, username, first_name, last_name, department, designation):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": "{}@example.com".format(username.lower()),
            },
        )
        user.set_password("demo123")
        user.save()

        extra_id = "{}_id".format(username.replace(".", "_"))[:20]
        extrainfo, _ = ExtraInfo.objects.get_or_create(
            id=extra_id,
            defaults={
                "user": user,
                "user_type": "faculty",
                "department": department,
                "title": "Dr.",
                "sex": "F",
            },
        )
        if extrainfo.user_id != user.id:
            extrainfo.user = user
            extrainfo.user_type = "faculty"
            extrainfo.department = department
            extrainfo.save()

        Faculty.objects.get_or_create(id=extrainfo)
        HoldsDesignation.objects.get_or_create(
            user=user,
            working=user,
            designation=designation,
        )
        return user
