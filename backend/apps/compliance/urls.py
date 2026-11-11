from django.urls import path

from apps.compliance.views import ComplianceView

app_name = "compliance"

urlpatterns = [
    path("business/compliance", ComplianceView.as_view(), name="compliance"),
]
