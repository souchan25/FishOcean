from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Users
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    
    # Sellers
    path('sellers/', views.seller_list, name='seller_list'),
    path('sellers/<int:seller_id>/verify/', views.verify_seller, name='verify_seller'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/toggle/', views.product_toggle, name='product_toggle'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    
    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Reviews
    path('reviews/', views.review_list, name='review_list'),
    path('reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    
    # Notifications
    path('send-notification/', views.send_notification, name='send_notification'),
]
