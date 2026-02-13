from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_buyer = models.BooleanField(default=False)
    is_seller = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username

class SellerProfile(models.Model):
    LOCATION_CHOICES = (
        ('Kabankalan', 'Kabankalan'),
        ('Ilog', 'Ilog'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    shop_name = models.CharField(max_length=100)
    municipality = models.CharField(max_length=50, choices=LOCATION_CHOICES, default='Kabankalan')
    address = models.TextField(help_text="Barangay and specific location")
    
    # Direct Payment QR Codes
    # Using specific names for clarity
    gcash_qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="GCash QR")
    maya_qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="Maya QR")
    
    # PayMongo Integration (Future proofing)
    paymongo_integrator_id = models.CharField(max_length=100, blank=True, null=True)
    
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.shop_name} ({self.municipality})"

