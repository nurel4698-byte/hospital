from datetime import time, timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .models import (Appointment, Doctor, DoctorReview, MedicalRecord,
                     Schedule, Specialization, UserProfile)

# =====================================================================
#                              ФОРМЫ
# =====================================================================
DT_FORMAT = '%Y-%m-%dT%H:%M'
DATE_WIDGET = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')


class StyledForm:
    """Добавляет CSS-класс ко всем полям формы."""

    def style(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class RegisterForm(StyledForm, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = UserProfile
        fields = ('username', 'first_name', 'last_name', 'email',
                  'birth_date', 'phone_number', 'address', 'blood_group')
        widgets = {'birth_date': DATE_WIDGET}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()


class ProfileForm(StyledForm, forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'email',
                  'birth_date', 'phone_number', 'address', 'blood_group')
        widgets = {'birth_date': DATE_WIDGET}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()


class DoctorForm(StyledForm, forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ('last_name', 'first_name', 'patronymic', 'photo',
                  'experience_years', 'price', 'specialization')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()


class AppointmentForm(StyledForm, forms.ModelForm):
    date_time = forms.DateTimeField(
        label='Дата и время',
        input_formats=[DT_FORMAT],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format=DT_FORMAT),
    )

    class Meta:
        model = Appointment
        fields = ('doctor', 'date_time', 'complaint')
        widgets = {'complaint': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()

    def clean(self):
        cleaned = super().clean()
        doctor = cleaned.get('doctor')
        dt = cleaned.get('date_time')
        if doctor and dt:
            local = timezone.localtime(dt)
            if local <= timezone.localtime():
                raise ValidationError('Выберите время в будущем.')
            fits = doctor.schedules.filter(
                day_of_week=local.weekday(),
                start_time__lte=local.time(),
                end_time__gt=local.time(),
            ).exists()
            if not fits:
                raise ValidationError('Врач в это время не принимает. Посмотрите расписание врача.')
            busy = (Appointment.objects.filter(doctor=doctor, date_time=dt)
                    .exclude(status='cancelled').exclude(pk=self.instance.pk))
            if busy.exists():
                raise ValidationError('Это время уже занято, выберите другое.')
        return cleaned


class ReviewForm(StyledForm, forms.ModelForm):
    class Meta:
        model = DoctorReview
        fields = ('stars', 'comment')
        widgets = {'comment': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


# =====================================================================
#                     ГЛАВНАЯ, РЕГИСТРАЦИЯ, ПРОФИЛЬ
# =====================================================================
def home(request):
    return render(request, 'home.html', {
        'specializations': Specialization.objects.annotate(doctors_count=Count('doctors')),
        'doctors': Doctor.objects.select_related('specialization')[:4],
    })


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Регистрация прошла успешно!')
        return redirect('home')
    return render(request, 'form.html', {'form': form, 'title': 'Регистрация пациента', 'button': 'Зарегистрироваться'})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Профиль обновлён.')
        return redirect('profile')
    return render(request, 'form.html', {'form': form, 'title': 'Мой профиль'})


# =====================================================================
#                            ВРАЧИ (CRUD)
# =====================================================================
class DoctorListView(ListView):
    template_name = 'doctors.html'
    context_object_name = 'doctors'

    def get_queryset(self):
        qs = Doctor.objects.select_related('specialization')
        spec = self.request.GET.get('spec')
        q = self.request.GET.get('q', '').strip()
        if spec:
            qs = qs.filter(specialization_id=spec)
        if q:
            qs = qs.filter(Q(last_name__icontains=q) | Q(first_name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['specializations'] = Specialization.objects.all()
        ctx['current_spec'] = self.request.GET.get('spec', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class DoctorDetailView(DetailView):
    model = Doctor
    template_name = 'doctor_detail.html'
    context_object_name = 'doctor'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schedules'] = self.object.schedules.all()
        ctx['reviews'] = self.object.reviews.select_related('patient')
        ctx['review_form'] = ReviewForm()
        return ctx


class DoctorCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Doctor
    form_class = DoctorForm
    template_name = 'form.html'
    extra_context = {'title': 'Новый врач'}


class DoctorUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Doctor
    form_class = DoctorForm
    template_name = 'form.html'
    extra_context = {'title': 'Изменить врача'}


class DoctorDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Doctor
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('doctor_list')


@login_required
@require_POST
def add_review(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    was_patient = Appointment.objects.filter(
        patient=request.user, doctor=doctor, status='completed').exists()
    if not was_patient:
        messages.error(request, 'Оставить отзыв можно после завершённого приёма у этого врача.')
        return redirect('doctor_detail', pk=pk)
    form = ReviewForm(request.POST)
    if form.is_valid():
        DoctorReview.objects.update_or_create(
            doctor=doctor, patient=request.user, defaults=form.cleaned_data)
        messages.success(request, 'Спасибо за отзыв!')
    else:
        messages.error(request, 'Проверьте форму отзыва.')
    return redirect('doctor_detail', pk=pk)


# =====================================================================
#                       ЗАПИСИ НА ПРИЁМ (CRUD)
# =====================================================================
class AppointmentListView(LoginRequiredMixin, ListView):
    template_name = 'appointments.html'
    context_object_name = 'appointments'

    def get_queryset(self):
        qs = Appointment.objects.select_related(
            'doctor', 'doctor__specialization', 'patient', 'medical_record')
        if not self.request.user.is_staff:
            qs = qs.filter(patient=self.request.user)
        return qs


class AppointmentCreateView(LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'form.html'
    success_url = reverse_lazy('my_appointments')
    extra_context = {'title': 'Запись на приём',
                     'hint': 'Время должно попадать в расписание врача (см. страницу врача).'}

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get('doctor'):
            initial['doctor'] = self.request.GET['doctor']
        return initial

    def form_valid(self, form):
        form.instance.patient = self.request.user
        messages.success(self.request, 'Вы записаны на приём! Ожидайте подтверждения.')
        return super().form_valid(form)


class AppointmentUpdateView(LoginRequiredMixin, UpdateView):
    form_class = AppointmentForm
    template_name = 'form.html'
    success_url = reverse_lazy('my_appointments')
    extra_context = {'title': 'Изменить запись'}

    def get_queryset(self):  # менять можно только свою запись, пока она ожидает
        return Appointment.objects.filter(patient=self.request.user, status='pending')


class AppointmentDeleteView(LoginRequiredMixin, DeleteView):
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('my_appointments')

    def get_queryset(self):
        qs = Appointment.objects.exclude(status='completed')
        return qs if self.request.user.is_staff else qs.filter(patient=self.request.user)


@login_required
@require_POST
def appointment_status(request, pk, status):
    appointment = get_object_or_404(Appointment, pk=pk)
    is_owner = appointment.patient_id == request.user.id
    staff = request.user.is_staff

    if status == 'cancelled' and (is_owner or staff) and appointment.status in ('pending', 'confirmed'):
        pass
    elif status in ('confirmed', 'completed') and staff and appointment.status != 'cancelled':
        pass
    else:
        messages.error(request, 'Это действие недоступно.')
        return redirect('my_appointments')

    appointment.status = status
    appointment.save(update_fields=['status'])
    messages.success(request, f'Статус записи: {appointment.get_status_display()}.')
    return redirect('my_appointments')


# =====================================================================
#              ТЕСТОВЫЕ ДАННЫЕ: откройте http://127.0.0.1:8000/seed/
# =====================================================================
SPECS = [
    ('Кардиолог', 'Диагностика и лечение болезней сердца и сосудов.'),
    ('Хирург', 'Хирургическое лечение и консультации перед операциями.'),
    ('Терапевт', 'Первичный приём, диагностика и лечение общих заболеваний.'),
    ('Невролог', 'Заболевания нервной системы, головные боли, головокружения.'),
    ('Педиатр', 'Здоровье детей от рождения до 18 лет.'),
    ('Офтальмолог', 'Проверка зрения и лечение заболеваний глаз.'),
]
# (фамилия, имя, отчество, специализация, опыт, цена)
DOCTORS = [
    ('Иванов', 'Алексей', 'Петрович', 'Кардиолог', 15, 1500),
    ('Сыдыкова', 'Айгуль', 'Бакировна', 'Кардиолог', 8, 1200),
    ('Петров', 'Сергей', 'Иванович', 'Хирург', 20, 2000),
    ('Асанов', 'Эрлан', 'Маратович', 'Терапевт', 10, 800),
    ('Каримова', 'Нургуль', 'Асановна', 'Терапевт', 5, 700),
    ('Смирнова', 'Елена', 'Викторовна', 'Невролог', 12, 1400),
    ('Токтогулова', 'Айжан', 'Эсеновна', 'Педиатр', 9, 900),
    ('Орлов', 'Дмитрий', 'Андреевич', 'Офтальмолог', 7, 1000),
]


def seed(request):
    if not settings.DEBUG:
        return HttpResponse('Только в режиме DEBUG', status=403)

    if not UserProfile.objects.filter(username='admin').exists():
        UserProfile.objects.create_superuser('admin', 'admin@example.com', 'admin12345')
    patient, created = UserProfile.objects.get_or_create(
        username='patient',
        defaults=dict(first_name='Айбек', last_name='Жумабаев', email='patient@example.com',
                      birth_date='1995-05-20', phone_number='+996 555 123 456',
                      address='г. Бишкек, ул. Ахунбаева 1', blood_group='A+'))
    if created:
        patient.set_password('patient12345')
        patient.save()

    specs = {}
    for name, desc in SPECS:
        specs[name], _ = Specialization.objects.get_or_create(name=name, defaults={'description': desc})

    doctors = []
    for i, (last, first, pat, spec, exp, price) in enumerate(DOCTORS):
        doctor, new = Doctor.objects.get_or_create(
            last_name=last, first_name=first,
            defaults=dict(patronymic=pat, specialization=specs[spec],
                          experience_years=exp, price=price))
        if new:
            for d in [(0, 2, 4), (1, 3, 5)][i % 2]:  # пн/ср/пт или вт/чт/сб
                Schedule.objects.create(doctor=doctor, day_of_week=d,
                                        start_time=time(9, 0), end_time=time(17, 0))
        doctors.append(doctor)

    if not Appointment.objects.filter(patient=patient).exists():
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        past = [
            (doctors[0], 30, 'Боли в груди при нагрузке', 'Гипертоническая болезнь I степени',
             'Эналаприл 5 мг утром, контроль давления, ЭКГ через месяц.'),
            (doctors[3], 14, 'Кашель и температура 3 дня', 'ОРВИ',
             'Обильное питьё, парацетамол при температуре выше 38,5, постельный режим 5 дней.'),
        ]
        for doctor, days_ago, complaint, diagnosis, prescription in past:
            ap = Appointment.objects.create(patient=patient, doctor=doctor,
                                            date_time=now - timedelta(days=days_ago),
                                            complaint=complaint, status='completed')
            MedicalRecord.objects.create(appointment=ap, diagnosis=diagnosis, prescription=prescription)
        DoctorReview.objects.create(doctor=doctors[0], patient=patient, stars=5,
                                    comment='Очень внимательный врач, всё объяснил.')
        DoctorReview.objects.create(doctor=doctors[3], patient=patient, stars=4,
                                    comment='Быстро помог, но пришлось подождать в очереди.')
        Appointment.objects.create(patient=patient, doctor=doctors[5], date_time=now + timedelta(days=5),
                                   complaint='Частые головные боли', status='confirmed')
        Appointment.objects.create(patient=patient, doctor=doctors[7], date_time=now + timedelta(days=9),
                                   complaint='Проверка зрения', status='pending')

    messages.success(request, 'Тестовые данные загружены. Админ: admin / admin12345, пациент: patient / patient12345')
    return redirect('home')
