from django.db import models
from django.conf import settings
from django.db.models import Avg

class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=10, default='🐟', help_text="Emoji icon for category")
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=200) # e.g., "Fresh Bangus (Milkfish)"
    description = models.TextField(blank=True)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Original price before discount")
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # Inventory Management
    stocks_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_live = models.BooleanField(default=True, help_text="Uncheck when out of stock naturally")
    is_featured = models.BooleanField(default=False, help_text="Feature this product on homepage")
    
    # Tags for filtering
    is_fresh_catch = models.BooleanField(default=True, help_text="Today's fresh catch")
    is_bestseller = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.seller.seller_profile.shop_name}"

    @property
    def is_available(self):
        return self.is_live and self.stocks_kg > 0
    
    @property
    def discount_percent(self):
        if self.original_price and self.original_price > self.price_per_kg:
            return int(((self.original_price - self.price_per_kg) / self.original_price) * 100)
        return 0
    
    @property
    def average_rating(self):
        avg = self.reviews.aggregate(avg=Avg('rating'))['avg']
        return round(avg, 1) if avg else 0
    
    @property
    def review_count(self):
        return self.reviews.count()

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='products/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.product.name} - Gallery Image"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)]) # 1-5 Stars
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user') # One review per product per user
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.rating}* - {self.product.name}'


class Wishlist(models.Model):
    """User's wishlist/favorites"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s wishlist - {self.product.name}"

