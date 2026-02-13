from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('order_status', 'Order Status Update'),
        ('order_placed', 'New Order Placed'),
        ('low_stock', 'Low Stock Alert'),
        ('new_message', 'New Message'),
        ('payment_uploaded', 'Payment Proof Uploaded'),
        ('review_received', 'New Review Received'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True, null=True)  # URL to redirect when clicked
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} - {self.recipient.username}"
