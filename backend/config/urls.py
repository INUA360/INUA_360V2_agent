"""Root URL configuration."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(_request):  # type: ignore[no-untyped-def]
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.businesses.urls")),
    path("api/v1/", include("apps.compliance.urls")),
    path("api/v1/", include("apps.ingestion.urls")),
    path("api/v1/", include("apps.financials.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.readiness.urls")),
    path("api/v1/", include("apps.opportunities.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
