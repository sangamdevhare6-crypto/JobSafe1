from django.urls import path
from . import views
from scanner import views as scanner_views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-users/", views.admin_users, name="admin_users"),
    path("admin-companies/", views.admin_companies, name="admin_companies"),
    path("safety-guide/", views.safety_guide, name="safety_guide"),
    path("company-check/", scanner_views.company_check, name="company_check"),
    path("analytics/", views.analytics, name="analytics"),
    path("activity/", views.activity, name="activity"),
    path("profile/", views.profile, name="profile"),
    path("notifications/", views.notifications, name="notifications"),
    path("settings/", views.settings_page, name="settings"),
    path("admin-analytics/", views.admin_analytics, name="admin_analytics"),
    path("system-monitor/", views.system_monitor, name="system_monitor"),
    path("threat-center/", views.threat_center, name="threat_center"),
    path("scan-history/", views.scan_history, name="scan_history"),
    path("resources/", views.resources, name="resources"),
    path("admin-jobs/", views.admin_jobs, name="admin_jobs"),
    path("admin-threats/", views.admin_threats, name="admin_threats"),
    path("admin-resources/", views.admin_resources, name="admin_resources"),
    path("api/company-search/", views.company_search_api, name="company_search_api"),
    path("api/company-details/", views.company_details_api, name="company_details_api"),
]
