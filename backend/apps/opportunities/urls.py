from django.urls import path

from apps.opportunities import views

app_name = "opportunities"

urlpatterns = [
    path("opportunities/matches", views.MatchListView.as_view(), name="matches"),
    path(
        "opportunities/matches/<uuid:pk>",
        views.MatchDetailView.as_view(),
        name="match-detail",
    ),
    path(
        "opportunities/<uuid:pk>/checklist",
        views.OpportunityChecklistView.as_view(),
        name="checklist",
    ),
    path("opportunities/<uuid:pk>", views.OpportunityDetailView.as_view(), name="detail"),
]
