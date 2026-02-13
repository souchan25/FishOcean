from django.db import models
from django.conf import settings
from store.models import Product

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Seller Verification'), # For Direct QR
        ('paid', 'Paid (PayMongo verified)'),       # For PayMongo
        ('preparing', 'Preparing / Packed'),
        ('out_for_delivery', 'Out for Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Cash on Delivery'),
        ('direct_gcash', 'Direct GCash (Seller QR)'),
        ('direct_maya', 'Direct Maya (Seller QR)'),
        ('paymongo', 'Credit/Debit/E-wallet (PayMongo)'),
    )

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    
    # "One Seller per Order" rule implies we store the seller here for easy access
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_orders')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    
    # Delivery Info
    delivery_address = models.TextField()
    contact_number = models.CharField(max_length=15)
    
    # Direct Payment Proof
    proof_of_payment = models.ImageField(upload_to='payment_proofs/', blank=True, null=True, help_text="Upload screenshot for Direct GCash/Maya")
    
    # PayMongo Info
    paymongo_checkout_id = models.CharField(max_length=100, blank=True, null=True)
    paymongo_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.buyer.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity_kg = models.DecimalField(max_digits=5, decimal_places=2) # Weight ordered
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def get_cost(self):
        return self.price_at_purchase * self.quantity_kg

