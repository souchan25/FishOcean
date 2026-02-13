from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('register/buyer/', views.register_buyer, name='register_buyer'),
    path('register/seller/', views.register_seller, name='register_seller'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Seller Dashboard Urls
    path('dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('product/add/', views.add_product, name='add_product'),
    path('product/toggle/<int:product_id>/', views.toggle_product_status, name='toggle_product_status'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
]
