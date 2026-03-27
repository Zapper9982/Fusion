from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from applications.academic_information.models import Student
from applications.central_mess.models import (
    Feedback,
    MenuPoll,
    MenuPollVote,
    Mess_reg,
    Messinfo,
    Payments,
    RegistrationRequest,
    Rebate,
)
from applications.globals.models import DepartmentInfo, Designation, ExtraInfo, HoldsDesignation


class CentralMessApiTests(APITestCase):
    def setUp(self):
        self.department = DepartmentInfo.objects.create(name='CSE')

        self.student_user = User.objects.create_user(
            username='22BCS001',
            password='testpass123',
            first_name='Test',
            last_name='Student',
        )
        self.student_extra = ExtraInfo.objects.create(
            id='22BCS001',
            user=self.student_user,
            user_type='student',
            department=self.department,
        )
        self.student = Student.objects.create(
            id=self.student_extra,
            programme='B.Tech',
            category='GEN',
            curr_semester_no=4,
        )
        self.student_token = Token.objects.create(user=self.student_user)

        self.manager_user = User.objects.create_user(
            username='messmanager',
            password='testpass123',
        )
        self.manager_extra = ExtraInfo.objects.create(
            id='EMP001',
            user=self.manager_user,
            user_type='staff',
            department=self.department,
        )
        designation = Designation.objects.create(
            name='mess_committee_mess1',
            full_name='Mess Committee Mess 1',
            type='administrative',
        )
        HoldsDesignation.objects.create(
            user=self.manager_user,
            working=self.manager_user,
            designation=designation,
        )
        self.manager_token = Token.objects.create(user=self.manager_user)

        self.other_student_user = User.objects.create_user(
            username='22BCS002',
            password='testpass123',
            first_name='Other',
            last_name='Student',
        )
        self.other_student_extra = ExtraInfo.objects.create(
            id='22BCS002',
            user=self.other_student_user,
            user_type='student',
            department=self.department,
        )
        self.other_student = Student.objects.create(
            id=self.other_student_extra,
            programme='B.Tech',
            category='GEN',
            curr_semester_no=4,
        )
        self.other_student_token = Token.objects.create(user=self.other_student_user)

        self.registration_url = reverse('mess:registrationRequestApi')
        self.rebate_url = reverse('mess:rebateApi')
        self.feedback_url = reverse('mess:feedbackApi')
        self.menu_poll_url = reverse('mess:menuPollApi')
        self.menu_poll_vote_url = reverse('mess:menuPollVoteApi')

    def authenticate_student(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token {}'.format(self.student_token.key))

    def authenticate_manager(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token {}'.format(self.manager_token.key))

    def authenticate_other_student(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token {}'.format(self.other_student_token.key))

    def test_student_can_submit_registration_request(self):
        self.authenticate_student()
        Mess_reg.objects.create(
            sem=4,
            start_reg=timezone.now().date() - timedelta(days=1),
            end_reg=timezone.now().date() + timedelta(days=5),
        )

        response = self.client.post(self.registration_url, {
            'mess_option': 'mess1',
            'start_date': (timezone.now().date() + timedelta(days=1)).isoformat(),
            'payment_date': timezone.now().date().isoformat(),
            'amount': 3500,
            'Txn_no': 'TXN-001',
            'registration_remark': 'Joining from next cycle',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(RegistrationRequest.objects.count(), 1)
        self.assertEqual(RegistrationRequest.objects.first().status, 'pending')

    def test_manager_can_approve_registration_request(self):
        registration = RegistrationRequest.objects.create(
            student_id=self.student,
            mess_option='mess2',
            start_date=timezone.now().date() + timedelta(days=2),
            payment_date=timezone.now().date(),
            amount=4200,
            Txn_no='TXN-APPROVE',
        )
        Mess_reg.objects.create(
            sem=4,
            start_reg=timezone.now().date() - timedelta(days=2),
            end_reg=timezone.now().date() + timedelta(days=5),
        )

        self.authenticate_manager()
        response = self.client.put(self.registration_url, {
            'id': registration.id,
            'status': 'accept',
            'mess_option': 'mess2',
            'registration_remark': 'Approved',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        registration.refresh_from_db()
        self.assertEqual(registration.status, 'accept')
        self.assertTrue(Messinfo.objects.filter(student_id=self.student, mess_option='mess2').exists())
        self.assertTrue(Payments.objects.filter(student_id=self.student, Txn_no='TXN-APPROVE').exists())

    def test_rebate_rejects_when_cap_exceeded(self):
        Rebate.objects.create(
            student_id=self.student,
            start_date=timezone.now().date() + timedelta(days=1),
            end_date=timezone.now().date() + timedelta(days=20),
            purpose='Existing approved rebate',
            status='2',
        )

        self.authenticate_student()
        response = self.client.post(self.rebate_url, {
            'start_date': (timezone.now().date() + timedelta(days=25)).isoformat(),
            'end_date': (timezone.now().date() + timedelta(days=26)).isoformat(),
            'purpose': 'Family function',
            'leave_type': 'casual',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['status'], 3)

    def test_feedback_is_limited_to_one_per_day_and_can_be_marked_read(self):
        self.authenticate_student()
        first_response = self.client.post(self.feedback_url, {
            'feedback_type': 'Food',
            'description': 'Food quality needs improvement because dinner was consistently cold.',
            'mess_rating': 3,
        }, format='json')

        self.assertEqual(first_response.status_code, 200)
        second_response = self.client.post(self.feedback_url, {
            'feedback_type': 'Food',
            'description': 'Trying to submit second feedback on the same day.',
            'mess_rating': 4,
        }, format='json')
        self.assertEqual(second_response.status_code, 400)

        feedback = Feedback.objects.first()
        self.authenticate_manager()
        mark_read_response = self.client.delete(self.feedback_url, {
            'student_id': self.student_user.username,
            'mess': feedback.mess,
            'feedback_type': 'Food',
            'description': feedback.description,
            'fdate': feedback.fdate.isoformat(),
        }, format='json')

        self.assertEqual(mark_read_response.status_code, 200)
        feedback.refresh_from_db()
        self.assertTrue(feedback.is_read)

    def test_manager_can_create_menu_poll(self):
        self.authenticate_manager()
        response = self.client.post(self.menu_poll_url, {
            'question': 'What should be served for Monday breakfast?',
            'description': 'Pick the preferred dish for next week.',
            'mess_option': 'mess1',
            'meal_time': 'MB',
            'poll_date': timezone.now().date().isoformat(),
            'options': ['Poha', 'Idli', 'Upma'],
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(MenuPoll.objects.count(), 1)
        self.assertEqual(MenuPoll.objects.first().options.count(), 3)
        self.assertEqual(response.data['payload']['question'], 'What should be served for Monday breakfast?')

    def test_registered_student_can_vote_and_update_vote_on_menu_poll(self):
        Messinfo.objects.create(student_id=self.student, mess_option='mess1')
        poll = MenuPoll.objects.create(
            question='Choose Friday dinner',
            description='Menu selection poll',
            mess_option='mess1',
            meal_time='FD',
            status='open',
            created_by=self.manager_user,
        )
        option_one = poll.options.create(option_text='Paneer Butter Masala', display_order=0)
        option_two = poll.options.create(option_text='Chole Bhature', display_order=1)

        self.authenticate_student()
        first_response = self.client.post(self.menu_poll_vote_url, {
            'poll_id': poll.id,
            'option_id': option_one.id,
        }, format='json')

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(MenuPollVote.objects.count(), 1)
        self.assertEqual(MenuPollVote.objects.first().option, option_one)
        self.assertEqual(first_response.data['payload']['user_vote_option'], option_one.id)

        second_response = self.client.post(self.menu_poll_vote_url, {
            'poll_id': poll.id,
            'option_id': option_two.id,
        }, format='json')

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(MenuPollVote.objects.count(), 1)
        self.assertEqual(MenuPollVote.objects.first().option, option_two)
        self.assertEqual(second_response.data['payload']['user_vote_option'], option_two.id)

    def test_student_cannot_vote_for_other_mess_poll(self):
        Messinfo.objects.create(student_id=self.student, mess_option='mess1')
        poll = MenuPoll.objects.create(
            question='Choose Sunday lunch',
            mess_option='mess2',
            meal_time='SUL',
            status='open',
            created_by=self.manager_user,
        )
        option = poll.options.create(option_text='Biryani', display_order=0)
        poll.options.create(option_text='Pulao', display_order=1)

        self.authenticate_student()
        response = self.client.post(self.menu_poll_vote_url, {
            'poll_id': poll.id,
            'option_id': option.id,
        }, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(MenuPollVote.objects.exists())
