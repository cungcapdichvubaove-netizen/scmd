from django.urls import path


urlpatterns = [
    path("healthz/", lambda request: None),
]
