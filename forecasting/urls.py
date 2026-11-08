
from django.urls import path
from . import views

urlpatterns = [
    path("", views.forecast_dashboard, name="forecast_dashboard"),
]
