from django.urls import path

from . import views

urlpatterns = [
    path("plan", views.plan),
    path("plan/<str:plan_id>/heatmap", views.heatmap),
    path("geocode", views.geocode),
    path("health", views.health),
]
