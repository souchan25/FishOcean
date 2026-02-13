from .models import Notification

def unread_notifications(request):
    """Make unread notification count and recent notifications available in all templates"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
        return {
            'unread_notifications_count': unread_count,
            'notifications': notifications,
        }
    return {
        'unread_notifications_count': 0,
        'notifications': [],
    }
