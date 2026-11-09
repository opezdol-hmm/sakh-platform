from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.contrib.auth.models import User  # <--- ДОБАВИЛИ ЭТО
from .models import Case, Submission, Review, Team, Notification, Training, TrainingProgress, Schedule


@login_required
def dashboard(request):
    return render(request, 'cases/dashboard.html')


@login_required
def case_list(request):
    cases = Case.objects.filter(is_active=True)
    return render(request, 'cases/case_list.html', {'cases': cases})


@login_required
def case_detail(request, case_id):
    import json
    case = get_object_or_404(Case, id=case_id)
    profile = request.user.profile

    team = Team.objects.filter(captain=request.user).first() or Team.objects.filter(members=request.user).first()

    submission = None
    review = None
    review_json = None

    if team:
        submission = Submission.objects.filter(case=case, team=team).first()
        if submission and submission.status == 'reviewed':
            review = Review.objects.filter(submission=submission).first()
            if review:
                review_json = json.dumps(review.get_scores_dict(), ensure_ascii=False)

    return render(request, 'cases/case_detail.html', {
        'case': case,
        'is_captain': profile.role == 'captain',
        'team': team,
        'submission': submission,
        'review': review,
        'review_json': review_json,
    })


@login_required
def submit_solution(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    profile = request.user.profile

    if profile.role != 'captain':
        return HttpResponseForbidden("Только капитан может загружать решения.")

    team = Team.objects.filter(captain=request.user).first()
    if not team:
        return HttpResponseForbidden("Вы не являетесь капитаном команды.")

    if request.method == 'POST' and request.FILES.get('solution_file'):
        submission, created = Submission.objects.get_or_create(
            case=case, team=team,
            defaults={'file': request.FILES['solution_file']}
        )
        if not created:
            submission.file = request.FILES['solution_file']
            submission.status = 'pending'
            submission.save()
        return redirect('case_detail', case_id=case.id)

    return redirect('case_detail', case_id=case.id)


@login_required
def judge_review(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    profile = request.user.profile

    if profile.role != 'judge':
        return HttpResponseForbidden("Доступ разрешен только жюри.")

    review = Review.objects.filter(submission=submission).first()

    if request.method == 'POST':
        score_tech = int(request.POST.get('score_technology', 0))
        score_econ = int(request.POST.get('score_economics', 0))
        score_eco = int(request.POST.get('score_ecology', 0))
        score_real = int(request.POST.get('score_realizability', 0))
        comment = request.POST.get('comment', '')

        if review:
            review.score_technology = score_tech
            review.score_economics = score_econ
            review.score_ecology = score_eco
            review.score_realizability = score_real
            review.comment = comment
            review.save()
        else:
            Review.objects.create(
                submission=submission,
                judge=request.user,
                score_technology=score_tech,
                score_economics=score_econ,
                score_ecology=score_eco,
                score_realizability=score_real,
                comment=comment
            )

        submission.status = 'reviewed'
        submission.save()

        # Создаём уведомление для капитана
        captain = submission.team.captain
        Notification.objects.create(
            user=captain,
            message=f'Жюри проверило решение вашей команды "{submission.team.name}" по кейсу "{submission.case.title}"'
        )

        # Создаём уведомление для всех участников команды
        for member in submission.team.members.all():
            Notification.objects.create(
                user=member,
                message=f'Жюри проверило решение вашей команды "{submission.team.name}" по кейсу "{submission.case.title}"'
            )

        return redirect('case_detail', case_id=submission.case.id)

    return render(request, 'cases/judge_review.html', {
        'submission': submission,
        'review': review,
    })


@login_required
def profile(request):
    profile_obj = request.user.profile
    team = Team.objects.filter(captain=request.user).first() or Team.objects.filter(members=request.user).first()

    if team:
        submissions_count = Submission.objects.filter(team=team).count()
        reviewed_count = Submission.objects.filter(team=team, status='reviewed').count()
    else:
        submissions_count = 0
        reviewed_count = 0

    return render(request, 'cases/profile.html', {
        'profile_obj': profile_obj,
        'team': team,
        'submissions_count': submissions_count,
        'reviewed_count': reviewed_count,
    })


@login_required
def achievements(request):
    team = Team.objects.filter(captain=request.user).first() or Team.objects.filter(members=request.user).first()

    achievements_list = []

    if team:
        submissions = Submission.objects.filter(team=team, status='reviewed')
        total_score = 0
        cases_count = 0

        for sub in submissions:
            review = Review.objects.filter(submission=sub).first()
            if review:
                score = review.score_technology + review.score_economics + review.score_ecology + review.score_realizability
                total_score += score
                cases_count += 1

        avg_score = total_score / cases_count if cases_count > 0 else 0

        if cases_count >= 1:
            achievements_list.append({'icon': '🏆', 'title': 'Первый кейс', 'desc': 'Пройден первый кейс'})
        if cases_count >= 3:
            achievements_list.append({'icon': '🔥', 'title': 'Опытный участник', 'desc': 'Пройдено 3 кейса'})
        if avg_score >= 30:
            achievements_list.append({'icon': '⭐', 'title': 'Отличник', 'desc': 'Средний балл выше 30'})
        if avg_score >= 35:
            achievements_list.append({'icon': '💎', 'title': 'Эксперт', 'desc': 'Средний балл выше 35'})

    return render(request, 'cases/achievements.html', {
        'team': team,
        'achievements': achievements_list,
    })


@login_required
def search(request):
    query = request.GET.get('q', '')
    results = []

    if query:
        results = Case.objects.filter(title__icontains=query, is_active=True)

    return render(request, 'cases/search.html', {
        'query': query,
        'results': results,
    })


@login_required
def notifications(request):
    user_notifications = Notification.objects.filter(user=request.user)

    mark_read_id = request.GET.get('mark_read')
    if mark_read_id:
        try:
            notif = Notification.objects.get(id=mark_read_id, user=request.user)
            notif.is_read = True
            notif.save()
        except Notification.DoesNotExist:
            pass

    notifications_list = []
    for notif in user_notifications:
        from django.utils import timezone
        time_diff = timezone.now() - notif.created_at
        if time_diff.seconds < 60:
            time_str = 'Только что'
        elif time_diff.seconds < 3600:
            time_str = f'{time_diff.seconds // 60} мин назад'
        elif time_diff.days == 0:
            time_str = f'{time_diff.seconds // 3600} ч назад'
        else:
            time_str = f'{time_diff.days} дн назад'

        notifications_list.append({
            'id': notif.id,
            'text': notif.message,
            'time': time_str,
            'unread': not notif.is_read,
        })

    return render(request, 'cases/notifications.html', {
        'notifications': notifications_list,
    })


@login_required
def training(request):
    """Страница тренингов."""
    trainings_qs = Training.objects.filter(is_active=True).order_by('order')

    trainings_list = []
    completed_count = 0

    for t in trainings_qs:
        progress = TrainingProgress.objects.filter(user=request.user, training=t).first()
        is_completed = progress.is_completed if progress else False

        if is_completed:
            completed_count += 1

        # ВАЖНО: ключ 'id' должен быть здесь обязательно!
        trainings_list.append({
            'id': t.id,  # <--- ВОТ ЭТА СТРОКА РЕШАЕТ ПРОБЛЕМУ
            'title': t.title,
            'desc': t.description,
            'duration': t.duration,
            'is_completed': is_completed,
        })

    total_count = len(trainings_list)
    progress_percent = (completed_count / total_count * 100) if total_count > 0 else 0

    return render(request, 'cases/training.html', {
        'trainings': trainings_list,
        'completed_count': completed_count,
        'total_count': total_count,
        'progress_percent': progress_percent,
    })


@login_required
def messages(request):
    messages_list = [
        {'from': 'Администратор', 'text': 'Добро пожаловать!', 'time': 'Вчера', 'unread': True},
    ]

    return render(request, 'cases/messages.html', {
        'messages': messages_list,
    })


@login_required
def training_detail(request, training_id):
    """Страница деталей тренинга."""
    training = get_object_or_404(Training, id=training_id)
    progress = TrainingProgress.objects.filter(user=request.user, training=training).first()

    return render(request, 'cases/training_detail.html', {
        'training': training,
        'is_completed': progress.is_completed if progress else False,
    })


@login_required
def complete_training(request, training_id):
    """Отметить тренинг как пройденный."""
    training = get_object_or_404(Training, id=training_id)

    progress, created = TrainingProgress.objects.get_or_create(
        user=request.user,
        training=training,
        defaults={'is_completed': True, 'completed_at': timezone.now()}
    )

    if not created and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save()

    return redirect('training_detail', training_id=training.id)


@login_required
def my_solutions(request):
    """Страница истории всех решений пользователя."""
    # Находим все команды, где пользователь состоит (как капитан или участник)
    teams = Team.objects.filter(captain=request.user) | Team.objects.filter(members=request.user)

    # Получаем все загрузки для этих команд, сортируем по дате (сначала новые)
    submissions = Submission.objects.filter(team__in=teams).select_related('case', 'team').order_by('-uploaded_at')

    solutions_list = []
    for sub in submissions:
        # Если решение проверено, подтягиваем оценку
        review = Review.objects.filter(submission=sub).first()
        solutions_list.append({
            'submission': sub,
            'case': sub.case,
            'team': sub.team,
            'review': review,
        })

    return render(request, 'cases/my_solutions.html', {
        'solutions': solutions_list,
    })


@login_required
def schedule(request):
    """Страница расписания."""
    from datetime import datetime, timedelta

    # Получаем все будущие события
    today = datetime.now().date()
    upcoming_events = Schedule.objects.filter(event_date__gte=today).select_related('related_case')

    # Получаем прошедшие события (последние 5)
    past_events = Schedule.objects.filter(event_date__lt=today).order_by('-event_date')[:5]

    # Форматируем события для шаблона
    def format_event(event):
        event_types = {
            'training': ('🎓', 'Тренинг'),
            'webinar': ('', 'Вебинар'),
            'deadline': ('⏰', 'Дедлайн'),
            'presentation': ('🎤', 'Презентация'),
            'other': ('📅', 'Событие'),
        }
        icon, type_name = event_types.get(event.event_type, ('📅', 'Событие'))

        time_str = event.event_time.strftime('%H:%M') if event.event_time else 'Весь день'

        return {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'type': type_name,
            'icon': icon,
            'date': event.event_date,
            'time': time_str,
            'location': event.location,
            'is_online': event.is_online,
            'case': event.related_case,
        }

    return render(request, 'cases/schedule.html', {
        'upcoming_events': [format_event(e) for e in upcoming_events],
        'past_events': [format_event(e) for e in past_events],
    })


from django.contrib.auth import login
from .forms import CustomUserCreationForm


def register(request):
    """Страница регистрации."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Автоматически логиним после регистрации
            login(request, user)
            # Вместо прямого редиректа на edit_profile, кидаем на главную или профиль,
            # где пользователь уже залогинен и имеет свежий токен.
            return redirect('profile')
    else:
        form = CustomUserCreationForm()

    return render(request, 'cases/register.html', {'form': form})


@login_required
def edit_profile(request):
    """Редактирование профиля."""
    profile_obj = request.user.profile

    if request.method == 'POST':
        # Обновляем данные пользователя
        request.user.first_name = request.POST.get('first_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()

        # Обновляем профиль
        profile_obj.first_name = request.POST.get('first_name', '')
        profile_obj.last_name = request.POST.get('last_name', '')
        profile_obj.phone = request.POST.get('phone', '')
        profile_obj.city = request.POST.get('city', '')
        profile_obj.bio = request.POST.get('bio', '')

        # Загрузка аватара
        if request.FILES.get('avatar'):
            profile_obj.avatar = request.FILES.get('avatar')

        profile_obj.save()

        return redirect('profile')

    return render(request, 'cases/edit_profile.html', {
        'profile_obj': profile_obj,
    })


@login_required
def leaderboard(request):
    """Рейтинг команд."""
    # Получаем все команды с их капитанами
    teams = Team.objects.all().prefetch_related('members')

    teams_rating = []
    for team in teams:
        submissions = Submission.objects.filter(team=team, status='reviewed')
        total_score = 0
        cases_count = 0

        for sub in submissions:
            review = Review.objects.filter(submission=sub).first()
            if review:
                score = review.score_technology + review.score_economics + review.score_ecology + review.score_realizability
                total_score += score
                cases_count += 1

        avg_score = total_score / cases_count if cases_count > 0 else 0

        teams_rating.append({
            'team': team,
            'avg_score': round(avg_score, 1),
            'cases_count': cases_count,
            'total_score': total_score,
            'members_count': team.members.count() + 1,  # +1 капитан
        })

    # Сортируем по среднему баллу (по убыванию)
    teams_rating.sort(key=lambda x: x['avg_score'], reverse=True)

    return render(request, 'cases/leaderboard.html', {
        'teams_rating': teams_rating,
    })


@login_required
def team_management(request):
    """Управление командой (только для капитана)."""
    profile = request.user.profile

    if profile.role != 'captain':
        return HttpResponseForbidden("Только капитан может управлять командой.")

    team = Team.objects.filter(captain=request.user).first()

    if not team:
        return render(request, 'cases/team_management.html', {
            'no_team': True,
        })

    members = team.members.all()

    # Обработка добавления участника
    add_error = None
    success_message = None

    if request.method == 'POST' and 'add_member' in request.POST:
        username = request.POST.get('username', '').strip()
        try:
            new_member = User.objects.get(username=username)
            if new_member == request.user:
                add_error = "Нельзя добавить самого себя."
            elif new_member in members:
                add_error = "Этот пользователь уже в команде."
            else:
                team.members.add(new_member)
                success_message = f"Пользователь {username} добавлен в команду!"

                # Уведомление новому участнику
                Notification.objects.create(
                    user=new_member,
                    message=f'Капитан "{request.user.username}" добавил вас в команду "{team.name}"'
                )
        except User.DoesNotExist:
            add_error = f"Пользователь '{username}' не найден."

    # Обработка удаления участника
    if request.method == 'POST' and 'remove_member' in request.POST:
        member_id = request.POST.get('member_id')
        try:
            member_to_remove = User.objects.get(id=member_id)
            team.members.remove(member_to_remove)
            success_message = f"Пользователь {member_to_remove.username} удалён из команды."

            Notification.objects.create(
                user=member_to_remove,
                message=f'Вы были исключены из команды "{team.name}" капитаном "{request.user.username}"'
            )
        except User.DoesNotExist:
            pass

    return render(request, 'cases/team_management.html', {
        'team': team,
        'members': members,
        'add_error': add_error,
        'success_message': success_message,
    })

def home(request):
    """Главная страница: лендинг для гостей, редирект в кабинет для авторизованных."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'cases/landing.html')


@login_required
def dashboard_analytics(request):
    """Данные для графиков на дашборде."""
    profile = request.user.profile
    team = Team.objects.filter(captain=request.user).first() or Team.objects.filter(members=request.user).first()

    if not team:
        return JsonResponse({'has_team': False})

    # Получаем все проверенные решения команды
    submissions = Submission.objects.filter(team=team, status='reviewed').select_related('case')

    # Данные для графика прогресса по кейсам
    cases_data = []
    scores_data = []

    for sub in submissions:
        review = Review.objects.filter(submission=sub).first()
        if review:
            total_score = review.score_technology + review.score_economics + review.score_ecology + review.score_realizability
            cases_data.append(sub.case.title[:20])  # Обрезаем длинные названия
            scores_data.append(total_score)

    # Данные для радарной диаграммы (средние баллы по критериям)
    if submissions:
        avg_tech = sum(r.score_technology for s in submissions if
                       (r := Review.objects.filter(submission=s).first())) / submissions.count()
        avg_econ = sum(r.score_economics for s in submissions if
                       (r := Review.objects.filter(submission=s).first())) / submissions.count()
        avg_eco = sum(r.score_ecology for s in submissions if
                      (r := Review.objects.filter(submission=s).first())) / submissions.count()
        avg_real = sum(r.score_realizability for s in submissions if
                       (r := Review.objects.filter(submission=s).first())) / submissions.count()
    else:
        avg_tech = avg_econ = avg_eco = avg_real = 0

    return JsonResponse({
        'has_team': True,
        'cases': cases_data,
        'scores': scores_data,
        'radar': {
            'technology': round(avg_tech, 1),
            'economics': round(avg_econ, 1),
            'ecology': round(avg_eco, 1),
            'realizability': round(avg_real, 1),
        }
    })