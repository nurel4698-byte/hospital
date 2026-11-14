from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from store_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('seed/', views.seed, name='seed'),  # загрузка тестовых данных

    # аккаунты
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='form.html', extra_context={'title': 'Вход', 'button': 'Войти'}), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),

    # врачи
    path('doctors/', views.DoctorListView.as_view(), name='doctor_list'),
    path('doctors/add/', views.DoctorCreateView.as_view(), name='doctor_add'),
    path('doctors/<int:pk>/', views.DoctorDetailView.as_view(), name='doctor_detail'),
    path('doctors/<int:pk>/edit/', views.DoctorUpdateView.as_view(), name='doctor_edit'),
    path('doctors/<int:pk>/delete/', views.DoctorDeleteView.as_view(), name='doctor_delete'),
    path('doctors/<int:pk>/review/', views.add_review, name='add_review'),

    # записи на приём
    path('appointments/', views.AppointmentListView.as_view(), name='my_appointments'),
    path('appointments/new/', views.AppointmentCreateView.as_view(), name='appointment_add'),
    path('appointments/<int:pk>/edit/', views.AppointmentUpdateView.as_view(), name='appointment_edit'),
    path('appointments/<int:pk>/delete/', views.AppointmentDeleteView.as_view(), name='appointment_delete'),
    path('appointments/<int:pk>/status/<str:status>/', views.appointment_status, name='appointment_status'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
