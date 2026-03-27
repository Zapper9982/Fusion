from django.conf.urls import url

from . import views

urlpatterns = [

    url(r'^auth/login/', views.login, name='login-api'),
    url(r'^auth/logout/', views.logout, name='logout-api'),
    url(r'^auth/me/', views.auth_me, name='auth-me-api'),
    url(r'^update-role/', views.update_role, name='update-role-api'),
    # generic profile endpoint
    url(r'^profile/(?P<username>.+)/', views.profile, name='profile-api'),
    # current user profile
    url(r'^profile/', views.profile, name='profile-api'),
    url(r'^profile_update/', views.profile_update, name='update-profile-api'),
    url(r'^profile_delete/(?P<id>[0-9]+)/', views.profile_delete, name='delete-profile-api'),

    url(r'^dashboard/',views.dashboard,name='dashboard-api'),
    url(r'^notification/read',views.NotificationRead,name='notifications-read'),
    url(r'^notification/', views.NotificationRead, name='notifications-list-api')

]
