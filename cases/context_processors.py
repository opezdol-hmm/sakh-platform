def unread_notifications(request):
    """Добавляет количество непрочитанных уведомлений в контекст."""
    if request.user.is_authenticated:
        from .models import Notification
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}