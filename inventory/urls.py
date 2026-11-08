
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('insights/', views.inventory_insights, name='inventory_insights'),
    path('low-stock-alerts/', views.low_stock_alerts, name='low_stock_alerts'),
]

