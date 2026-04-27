from django.urls import path
from user.views import UserListView
from .views import DashboardChartsView, DashboardStatsView

urlpatterns = [
    path("admin/user-list/", UserListView.as_view(), name="admin-user-list"),
    path("admin/dashboard-stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("admin/dashboard-charts/", DashboardChartsView.as_view(), name="dashboard-charts"),
]
