from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class Profile(models.Model):
    ROLE_CHOICES = (
        ('member', 'Участник'),
        ('captain', 'Капитан команды'),
        ('judge', 'Жюри'),
        ('admin', 'Администратор'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    team_name = models.CharField(max_length=100, blank=True, null=True)

    # Дополнительные поля
    first_name = models.CharField(max_length=50, blank=True, verbose_name="Имя")
    last_name = models.CharField(max_length=50, blank=True, verbose_name="Фамилия")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Аватар")
    bio = models.TextField(blank=True, verbose_name="О себе")
    city = models.CharField(max_length=100, blank=True, verbose_name="Город")

    # Даты
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.user.username

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    captain = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='captain_of_team',
        limit_choices_to={'profile__role': 'captain'}
    )
    members = models.ManyToManyField(User, related_name='teams', blank=True)

    def __str__(self):
        return self.name


class Case(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    materials = models.FileField(
        upload_to='cases/materials/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'zip', 'docx', 'xlsx'])],
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Submission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'На проверке'),
        ('reviewed', 'Проверено'),
    )
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='submissions')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='cases/submissions/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('case', 'team')


class Review(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='review')
    judge = models.ForeignKey(User, on_delete=models.CASCADE)

    score_technology = models.IntegerField(default=0, verbose_name="Технологичность (0-10)")
    score_economics = models.IntegerField(default=0, verbose_name="Экономика (0-10)")
    score_ecology = models.IntegerField(default=0, verbose_name="Экология (0-10)")
    score_realizability = models.IntegerField(default=0, verbose_name="Реализуемость (0-10)")

    comment = models.TextField(verbose_name="Комментарий жюри")
    reviewed_at = models.DateTimeField(auto_now=True)

    def get_scores_dict(self):
        return {
            'labels': ['Технологичность', 'Экономика', 'Экология', 'Реализуемость'],
            'data': [
                self.score_technology,
                self.score_economics,
                self.score_ecology,
                self.score_realizability,
            ]
        }

class Notification(models.Model):
    """Уведомления для пользователей."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Уведомление для {self.user.username}: {self.message[:50]}"

class Training(models.Model):
    """Тренинг с материалами."""
    title = models.CharField(max_length=200)
    description = models.TextField()
    materials = models.FileField(upload_to='trainings/materials/', blank=True, null=True)
    duration = models.CharField(max_length=50, help_text="Например: 15 мин")
    order = models.IntegerField(default=0, help_text="Порядок отображения")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title


class TrainingProgress(models.Model):
    """Прогресс прохождения тренинга пользователем."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='training_progress')
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='progress')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'training')

    def __str__(self):
        status = "Пройден" if self.is_completed else "В процессе"
        return f"{self.user.username} - {self.training.title} ({status})"

class Schedule(models.Model):
    """Расписание событий."""
    EVENT_TYPE_CHOICES = (
        ('training', 'Тренинг'),
        ('webinar', 'Вебинар'),
        ('deadline', 'Дедлайн кейса'),
        ('presentation', 'Презентация'),
        ('other', 'Другое'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='training')
    event_date = models.DateField()
    event_time = models.TimeField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, help_text="Место проведения или ссылка")
    is_online = models.BooleanField(default=False)
    related_case = models.ForeignKey(Case, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='schedule_events')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event_date', 'event_time']

    def __str__(self):
        time_str = self.event_time.strftime('%H:%M') if self.event_time else 'Весь день'
        return f"{self.title} ({self.event_date} {time_str})"