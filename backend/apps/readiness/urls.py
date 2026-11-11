from django.urls import path

from apps.readiness.views import ReadinessRecomputeView, ReadinessView

app_name = "readiness"

urlpatterns = [
    path("readiness", ReadinessView.as_view(), name="readiness"),
    path("readiness/recompute", ReadinessRecomputeView.as_view(), name="recompute"),
]
