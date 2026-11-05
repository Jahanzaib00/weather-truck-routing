from django.urls import include, path, re_path

from routing import views

urlpatterns = [
    path("api/", include("routing.urls")),
    re_path(r"^(?!api/).*$", views.spa),
]
