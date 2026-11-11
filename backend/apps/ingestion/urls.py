from django.urls import path

from apps.ingestion import views

app_name = "ingestion"

urlpatterns = [
    path("statements/parse", views.StatementParseView.as_view(), name="parse"),
    path(
        "statements/<uuid:pending_id>/confirm",
        views.StatementConfirmView.as_view(),
        name="confirm",
    ),
    path("statements", views.StatementListView.as_view(), name="list"),
    path("statements/<uuid:pk>", views.StatementDetailView.as_view(), name="detail"),
]
