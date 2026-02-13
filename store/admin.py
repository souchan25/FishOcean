from django.contrib import admin
from .models import Category, Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'price_per_kg', 'stocks_kg', 'is_live')
    list_filter = ('is_live', 'category')
    search_fields = ('name', 'seller__username')

admin.site.register(Category)

