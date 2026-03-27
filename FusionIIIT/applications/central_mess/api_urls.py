from django.conf.urls import url
from . import api_views

urlpatterns = [
    url(r'^menuApi/$', api_views.menu_api, name='menuApi'),
    url(r'^menuPollApi/$', api_views.menu_poll_api, name='menuPollApi'),
    url(r'^menuPollVoteApi/$', api_views.menu_poll_vote_api, name='menuPollVoteApi'),
    url(r'^checkRegistrationStatusApi/$', api_views.check_registration_status_api, name='checkRegistrationStatusApi'),
    url(r'^registrationRequestApi/$', api_views.registration_request_api, name='registrationRequestApi'),
    url(r'^get_student_bill/$', api_views.get_student_bill_api, name='get_student_bill_api'),
    url(r'^rebateApi/$', api_views.rebate_api, name='rebateApi'),
    url(r'^specialRequestApi/$', api_views.special_request_api, name='specialRequestApi'),
    url(r'^feedbackApi/$', api_views.feedback_api, name='feedbackApi'),
    url(r'^paymentsApi/$', api_views.payments_api, name='paymentsApi'),

    # Manager endpoints
    url(r'^get_mess_students/$', api_views.get_mess_students_api, name='get_mess_students_api'),
    url(r'^deRegistrationRequestApi/$', api_views.deregistration_request_api, name='deregistrationRequestApi'),
    url(r'^updatePaymentRequestApi/$', api_views.update_payment_request_api, name='updatePaymentRequestApi'),
    url(r'^messRegApi/$', api_views.mess_reg_api, name='messRegApi'),
    url(r'^get_mess_balance_statusApi/$', api_views.get_mess_balance_status_api, name='get_mess_balance_statusApi'),
]
