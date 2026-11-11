from django.urls import path

from apps.businesses.views import BusinessView

app_name = "businesses"

urlpatterns = [
    path("business", BusinessView.as_view(), name="business"),
]
