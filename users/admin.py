from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SellerProfile

class SellerProfileInline(admin.StackedInline):
    model = SellerProfile
    can_delete = False
    verbose_name_plural = 'Seller Profile'

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_seller', 'is_buyer', 'is_staff')
    inlines = [SellerProfileInline]
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

admin.site.register(User, CustomUserAdmin)
admin.site.register(SellerProfile)

