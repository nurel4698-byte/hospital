from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Avg


class UserProfile(AbstractUser):
    BLOOD_GROUPS = [
        ('O+', 'O (I) Rh+'), ('O-', 'O (I) Rh-'),
        ('A+', 'A (II) Rh+'), ('A-', 'A (II) Rh-'),
        ('B+', 'B (III) Rh+'), ('B-', 'B (III) Rh-'),
        ('AB+', 'AB (IV) Rh+'), ('AB-', 'AB (IV) Rh-'),
    ]

    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    phone_number = models.CharField('Телефон', max_length=20, blank=True)
    address = models.CharField('Адрес', max_length=255, blank=True)
    blood_group = models.CharField('Группа крови', max_length=3, choices=BLOOD_GROUPS, blank=True)
    date_register = models.DateTimeField('Дата регистрации', auto_now_add=True)

    class Meta:
        verbose_name = 'Пациент'
        verbose_name_plural = 'Пациенты'

    def __str__(self):
        return self.get_full_name() or self.username


class Specialization(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Изображение', upload_to='specializations/', blank=True, null=True)

    class Meta:
        verbose_name = 'Специализация'
        verbose_name_plural = 'Специализации'
        ordering = ['name']

    def __str__(self):
        return self.name


class Doctor(models.Model):
    first_name = models.CharField('Имя', max_length=50)
    last_name = models.CharField('Фамилия', max_length=50)
    patronymic = models.CharField('Отчество', max_length=50, blank=True)
    photo = models.ImageField('Фото', upload_to='doctors/', blank=True, null=True)
    experience_years = models.PositiveIntegerField('Опыт (лет)', default=0)
    price = models.DecimalField('Цена приёма', max_digits=8, decimal_places=2)
    specialization = models.ForeignKey(
        Specialization, on_delete=models.CASCADE,
        related_name='doctors', verbose_name='Специализация',
    )

    class Meta:
        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return ' '.join(p for p in (self.last_name, self.first_name, self.patronymic) if p)

    def get_avg_rating(self):
        """Средний рейтинг врача (0, если отзывов нет)."""
        avg = self.reviews.aggregate(avg=Avg('stars'))['avg']
        return round(avg, 1) if avg else 0

    def get_appointment_count(self):
        """Количество записей к врачу."""
        return self.appointments.count()


class Schedule(models.Model):
    DAYS = [
        (0, 'Понедельник'), (1, 'Вторник'), (2, 'Среда'), (3, 'Четверг'),
        (4, 'Пятница'), (5, 'Суббота'), (6, 'Воскресенье'),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules', verbose_name='Врач')
    day_of_week = models.PositiveSmallIntegerField('День недели', choices=DAYS)
    start_time = models.TimeField('Начало')
    end_time = models.TimeField('Конец')

    class Meta:
        verbose_name = 'Расписание'
        verbose_name_plural = 'Расписание'
        ordering = ['doctor', 'day_of_week', 'start_time']

    def __str__(self):
        return f'{self.doctor}: {self.get_day_of_week_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}'


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждена'),
        ('cancelled', 'Отменена'),
        ('completed', 'Завершена'),
    ]

    patient = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='appointments', verbose_name='Пациент')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments', verbose_name='Врач')
    date_time = models.DateTimeField('Дата и время')
    complaint = models.TextField('Жалоба')
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='pending')
    created_date = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись на приём'
        verbose_name_plural = 'Записи на приём'
        ordering = ['-date_time']

    def __str__(self):
        return f'{self.patient} → {self.doctor} ({self.date_time:%d.%m.%Y %H:%M})'


class MedicalRecord(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='medical_record', verbose_name='Запись на приём')
    diagnosis = models.TextField('Диагноз')
    prescription = models.TextField('Назначения')
    created_date = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Медицинская запись'
        verbose_name_plural = 'Медицинские записи'

    def __str__(self):
        return f'Мед. запись #{self.pk} — {self.appointment}'


class DoctorReview(models.Model):
    STARS = [(i, '★' * i + '☆' * (5 - i)) for i in range(1, 6)]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='reviews', verbose_name='Врач')
    patient = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='reviews', verbose_name='Пациент')
    stars = models.PositiveSmallIntegerField('Оценка', choices=STARS)
    comment = models.TextField('Комментарий', blank=True)
    created_date = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_date']

    def __str__(self):
        return f'{self.doctor} — {self.stars}/5 от {self.patient}'
