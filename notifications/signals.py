from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from orders.models import Order
from store.models import Review, Product
from chat.models import Message
from .models import Notification

@receiver(post_save, sender=Order)
def notify_order_created(sender, instance, created, **kwargs):
    """Notify seller when new order is placed"""
    if created:
        Notification.objects.create(
            recipient=instance.seller,
            notification_type='order_placed',
            title='New Order Received!',
            message=f'You have a new order #{instance.id} from {instance.buyer.username}. Total: ₱{instance.total_amount:,.2f}',
            link=reverse('orders:order_detail', kwargs={'order_id': instance.id})
        )

@receiver(pre_save, sender=Order)
def notify_order_status_change(sender, instance, **kwargs):
    """Notify buyer when order status changes"""
    if instance.pk:  # Only for updates, not creation
        try:
            old_order = Order.objects.get(pk=instance.pk)
            if old_order.status != instance.status:
                status_messages = {
                    'pending': 'Your order is pending seller verification.',
                    'paid': 'Your payment has been verified!',
                    'preparing': 'Your order is being prepared.',
                    'out_for_delivery': 'Your order is out for delivery!',
                    'completed': 'Your order has been completed. Thank you!',
                    'cancelled': 'Your order has been cancelled.',
                }
                Notification.objects.create(
                    recipient=instance.buyer,
                    notification_type='order_status',
                    title=f'Order #{instance.id} Status Update',
                    message=status_messages.get(instance.status, 'Your order status has been updated.'),
                    link=reverse('orders:order_detail', kwargs={'order_id': instance.id})
                )
        except Order.DoesNotExist:
            pass

@receiver(post_save, sender=Order)
def notify_payment_uploaded(sender, instance, **kwargs):
    """Notify seller when payment proof is uploaded"""
    if not kwargs.get('created') and instance.proof_of_payment:
        # Check if notification already exists to avoid duplicates
        existing = Notification.objects.filter(
            recipient=instance.seller,
            notification_type='payment_uploaded',
            link=reverse('orders:order_detail', kwargs={'order_id': instance.id})
        ).exists()
        
        if not existing:
            Notification.objects.create(
                recipient=instance.seller,
                notification_type='payment_uploaded',
                title='Payment Proof Uploaded',
                message=f'Order #{instance.id} - {instance.buyer.username} has uploaded payment proof for verification.',
                link=reverse('orders:order_detail', kwargs={'order_id': instance.id})
            )

@receiver(post_save, sender=Review)
def notify_review_received(sender, instance, created, **kwargs):
    """Notify seller when product receives a review"""
    if created:
        Notification.objects.create(
            recipient=instance.product.seller,
            notification_type='review_received',
            title='New Review Received!',
            message=f'{instance.user.username} gave {instance.rating}★ to {instance.product.name}',
            link=reverse('store:product_detail', kwargs={'product_id': instance.product.id})
        )

@receiver(post_save, sender=Product)
def notify_low_stock(sender, instance, **kwargs):
    """Notify seller when product stock is low (< 5kg)"""
    from decimal import Decimal, InvalidOperation
    LOW_STOCK_THRESHOLD = Decimal('5')
    try:
        stocks_kg = Decimal(str(instance.stocks_kg))
    except (InvalidOperation, TypeError, ValueError):
        return
    if stocks_kg < LOW_STOCK_THRESHOLD and stocks_kg > 0:
        # Check if recent notification exists (within last 24 hours)
        from django.utils import timezone
        from datetime import timedelta
        recent = timezone.now() - timedelta(hours=24)
        
        existing = Notification.objects.filter(
            recipient=instance.seller,
            notification_type='low_stock',
            link=reverse('store:edit_product', kwargs={'product_id': instance.id}),
            created_at__gte=recent
        ).exists()
        
        if not existing:
            Notification.objects.create(
                recipient=instance.seller,
                notification_type='low_stock',
                title='Low Stock Alert',
                message=f'{instance.name} is running low! Only {stocks_kg}kg remaining.',
                link=reverse('store:edit_product', kwargs={'product_id': instance.id})
            )

@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    """Notify recipient when they receive a new message"""
    if created:
        # Determine recipient (opposite of sender)
        conversation = instance.conversation
        recipient = conversation.seller if instance.sender == conversation.buyer else conversation.buyer
        
        Notification.objects.create(
            recipient=recipient,
            notification_type='new_message',
            title='New Message',
            message=f'{instance.sender.username}: {instance.content[:50]}...' if len(instance.content) > 50 else f'{instance.sender.username}: {instance.content}',
            link=reverse('chat:chat_detail', kwargs={'pk': conversation.id})
        )
