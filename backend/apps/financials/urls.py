from django.urls import path

from apps.financials import views

app_name = "financials"

urlpatterns = [
    path("financials/summary", views.FinancialSummaryView.as_view(), name="summary"),
    path("financials/monthly", views.MonthlyFinancialView.as_view(), name="monthly"),
    path("loans", views.LoanListCreateView.as_view(), name="loans"),
    path("loans/<uuid:pk>", views.LoanDetailView.as_view(), name="loan-detail"),
    path("funding-need", views.FundingNeedView.as_view(), name="funding-need"),
]
