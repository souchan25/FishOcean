from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_list, name='chat_list'),
    path('<int:pk>/', views.chat_detail, name='chat_detail'),
    path('start/<int:seller_id>/', views.start_chat, name='start_chat'),
]
