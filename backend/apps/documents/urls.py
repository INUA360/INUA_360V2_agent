from django.urls import path

from apps.documents import views

app_name = "documents"

urlpatterns = [
    path("documents", views.DocumentListCreateView.as_view(), name="list"),
    path("documents/checklist", views.DocumentChecklistView.as_view(), name="checklist"),
    path("documents/<uuid:pk>", views.DocumentDetailView.as_view(), name="detail"),
    path(
        "documents/<uuid:pk>/download-url",
        views.DocumentDownloadURLView.as_view(),
        name="download-url",
    ),
    path("documents/<uuid:pk>/file", views.DocumentFileView.as_view(), name="file"),
]
