from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_history, name='order_history'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('reorder/<int:order_id>/', views.reorder, name='reorder'),
    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('upload-proof/<int:order_id>/', views.payment_upload, name='payment_upload'),
    path('paymongo/init/<int:order_id>/', views.paymongo_init, name='paymongo_init'),
]
