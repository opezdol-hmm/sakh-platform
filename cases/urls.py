from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Главная страница (лендинг для гостей, редирект в кабинет для авторизованных)
    path('', views.home, name='home'),
    #Личный кабинет (теперь доступен по явному адресу)
    path('dashboard/', views.dashboard, name='dashboard'),
    # Кейсы
    path('cases/', views.case_list, name='case_list'),
    path('cases/<int:case_id>/', views.case_detail, name='case_detail'),
    path('cases/<int:case_id>/submit/', views.submit_solution, name='submit_solution'),
    # Проверка жюри
    path('review/<int:submission_id>/', views.judge_review, name='judge_review'),
    # Профиль и команда
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('team-management/', views.team_management, name='team_management'),
    # Достижения и рейтинг
    path('achievements/', views.achievements, name='achievements'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    # Поиск и уведомления
    path('search/', views.search, name='search'),
    path('notifications/', views.notifications, name='notifications'),
    # Обучение
    path('training/', views.training, name='training'),
    path('training/<int:training_id>/', views.training_detail, name='training_detail'),
    path('training/<int:training_id>/complete/', views.complete_training, name='complete_training'),
    path('schedule/', views.schedule, name='schedule'),
    # Решения и сообщения
    path('my-solutions/', views.my_solutions, name='my_solutions'),
    path('messages/', views.messages, name='messages'),
    # Авторизация
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='cases/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('api/dashboard-analytics/', views.dashboard_analytics, name='dashboard_analytics'),
]