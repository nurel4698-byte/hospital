from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (Appointment, Doctor, DoctorReview, MedicalRecord,
                     Schedule, Specialization, UserProfile)


@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Данные пациента', {'fields': ('birth_date', 'phone_number', 'address', 'blood_group')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Данные пациента', {'fields': ('birth_date', 'phone_number', 'address', 'blood_group')}),
    )
    list_display = ('username', 'first_name', 'last_name', 'phone_number', 'blood_group', 'date_register')


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'specialization', 'experience_years', 'price')
    list_filter = ('specialization',)
    search_fields = ('last_name', 'first_name')
    inlines = [ScheduleInline]


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'doctor')


class MedicalRecordInline(admin.StackedInline):
    model = MedicalRecord
    extra = 0
    max_num = 1


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date_time', 'status', 'created_date')
    list_filter = ('status', 'doctor')
    list_editable = ('status',)
    search_fields = ('patient__username', 'doctor__last_name', 'complaint')
    inlines = [MedicalRecordInline]


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'diagnosis', 'created_date')


@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'patient', 'stars', 'created_date')
    list_filter = ('stars', 'doctor')
