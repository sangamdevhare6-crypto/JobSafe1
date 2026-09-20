import requests

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from scanner.models import JobCheck, CompanyCheck
from reports.models import ScamReport
from .forms import SignupForm


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url="/admin-login/")(view)


def home(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard" if request.user.is_staff else "dashboard")
    return render(request, "home.html")


def _do_login(request, admin_only=False):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user and (not admin_only or user.is_staff):
            login(request, user)
            return redirect("admin_dashboard" if user.is_staff else "dashboard")
        messages.error(request, "Invalid credentials or admin access required.")
    return render(request, "admin-login.html" if admin_only else "login.html")


def login_view(request):
    return _do_login(request, False)


def admin_login(request):
    return _do_login(request, True)


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignupForm()
    return render(request, "signup.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    checks = JobCheck.objects.filter(user=request.user).order_by("-created_at")[:6]
    total = JobCheck.objects.filter(user=request.user).count()
    safe = JobCheck.objects.filter(user=request.user, risk_level="Safe").count()
    suspicious = JobCheck.objects.filter(user=request.user, risk_level="Suspicious").count()
    high = JobCheck.objects.filter(user=request.user, risk_level="High Risk").count()
    reports = ScamReport.objects.filter(user=request.user).count()
    companies = CompanyCheck.objects.filter(user=request.user).count()
    return render(request, "dashboard.html", {"checks": checks, "total": total, "safe": safe, "suspicious": suspicious, "high": high, "reports": reports, "companies": companies, "active": "dashboard"})


@staff_required
def admin_dashboard(request):
    recent_company_checks = CompanyCheck.objects.select_related("user").order_by("-created_at")[:8]
    return render(request, "admin-dashboard.html", {
        "users": User.objects.count(), "checks": JobCheck.objects.count(), "reports": ScamReport.objects.count(), "companies": CompanyCheck.objects.count(),
        "recent_reports": ScamReport.objects.order_by("-created_at")[:6], "recent_company_checks": recent_company_checks, "active": "admin"
    })


@staff_required
def admin_users(request):
    users = User.objects.all().order_by("-date_joined")
    return render(request, "admin-users.html", {"users": users, "active": "users"})


@staff_required
def admin_companies(request):
    companies = CompanyCheck.objects.select_related("user").order_by("-created_at")
    return render(request, "admin-companies.html", {"companies": companies, "active": "companies"})


@login_required
def safety_guide(request):
    return render(request, "safety-guide.html", {"active": "guide"})


def _wikidata(company_id):
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{company_id}.json"
    response = requests.get(url, timeout=8, headers={"User-Agent": "JobSafe/2.0"})
    response.raise_for_status()
    data = response.json()
    return data.get("entities", {}).get(company_id, {})


def _claim(entity, prop):
    values = entity.get("claims", {}).get(prop, [])
    if not values:
        return ""
    try:
        value = values[0]["mainsnak"]["datavalue"]["value"]
        if isinstance(value, dict):
            return value.get("id", "")
        return str(value)
    except (KeyError, TypeError, IndexError):
        return ""


def company_search_api(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"success": False, "results": []})
    try:
        response = requests.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities", "search": query, "language": "en", "format": "json", "limit": 8, "type": "item"}, timeout=8, headers={"User-Agent": "JobSafe/2.0"})
        response.raise_for_status()
        data = response.json()
        results = [{"id": item.get("id"), "name": item.get("label", ""), "description": item.get("description", "") or "Public knowledge result"} for item in data.get("search", [])]
        return JsonResponse({"success": True, "results": results})
    except requests.RequestException:
        return JsonResponse({"success": True, "results": [], "offline": True, "message": "Live company search is temporarily unavailable. You can still run a local trust assessment."})


def company_details_api(request):
    company_id = request.GET.get("id", "").strip()
    if not company_id:
        return JsonResponse({"success": False, "error": "Company ID is required."}, status=400)
    try:
        entity = _wikidata(company_id)
        labels = entity.get("labels", {})
        descriptions = entity.get("descriptions", {})
        company_name = labels.get("en", {}).get("value") or company_id
        description = descriptions.get("en", {}).get("value") or "Public knowledge profile available."
        website = _claim(entity, "P856")
        founded = _claim(entity, "P571")
        employees = _claim(entity, "P1128")
        ticker = _claim(entity, "P414")
        return JsonResponse({"success": True, "company": {"id": company_id, "name": company_name, "description": description, "website": website, "founded": founded, "employees": employees, "ticker": ticker, "source": "Wikidata"}})
    except requests.RequestException:
        return JsonResponse({"success": False, "error": "Live company information is unavailable right now."}, status=503)


@login_required
def analytics(request):
    jobs = JobCheck.objects.filter(user=request.user)
    companies = CompanyCheck.objects.filter(user=request.user)
    reports = ScamReport.objects.filter(user=request.user)
    return render(request, "analytics.html", {"active": "analytics", "jobs": jobs.count(), "companies": companies.count(), "reports": reports.count(), "high": jobs.filter(risk_level="High Risk").count(), "suspicious": jobs.filter(risk_level="Suspicious").count(), "safe": jobs.filter(risk_level="Safe").count()})


@login_required
def activity(request):
    job_events = JobCheck.objects.filter(user=request.user).order_by("-created_at")[:12]
    company_events = CompanyCheck.objects.filter(user=request.user).order_by("-created_at")[:12]
    report_events = ScamReport.objects.filter(user=request.user).order_by("-created_at")[:12]
    events = []
    for item in job_events: events.append((item.created_at, "Job scan", item.title, item.risk_level))
    for item in company_events: events.append((item.created_at, "Company check", item.company, item.status))
    for item in report_events: events.append((item.created_at, "Scam report", item.company, item.status))
    events.sort(key=lambda x: x[0], reverse=True)
    return render(request, "activity.html", {"events": events[:24], "active": "activity"})


@login_required
def profile(request):
    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.email = request.POST.get("email", "").strip()
        request.user.save(update_fields=["first_name", "email"])
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")
    return render(request, "profile.html", {"active": "profile"})


@login_required
def notifications(request):
    pending = ScamReport.objects.filter(user=request.user, status="Pending").count()
    high = JobCheck.objects.filter(user=request.user, risk_level="High Risk").count()
    return render(request, "notifications.html", {"pending": pending, "high": high, "active": "notifications"})

@login_required
def settings_page(request):
    return render(request, "settings.html", {"active": "settings"})


@staff_required
def admin_analytics(request):
    return render(request, "admin-analytics.html", {
        "active": "analytics", "users": User.objects.count(), "jobs": JobCheck.objects.count(), "companies": CompanyCheck.objects.count(), "reports": ScamReport.objects.count(),
        "high": JobCheck.objects.filter(risk_level="High Risk").count(), "suspicious": JobCheck.objects.filter(risk_level="Suspicious").count(), "safe": JobCheck.objects.filter(risk_level="Safe").count(),
    })


@staff_required
def system_monitor(request):
    return render(request, "system-monitor.html", {"active": "monitor", "users": User.objects.count(), "jobs": JobCheck.objects.count(), "companies": CompanyCheck.objects.count(), "reports": ScamReport.objects.count()})


@login_required
def threat_center(request):
    jobs=JobCheck.objects.filter(user=request.user); companies=CompanyCheck.objects.filter(user=request.user)
    return render(request,"threat-center.html",{"active":"threat","high_jobs":jobs.filter(risk_level="High Risk").order_by("-created_at")[:8],"review_companies":companies.filter(status__in=["High Risk","Needs Review","Suspicious"]).order_by("-created_at")[:8],"high_count":jobs.filter(risk_level="High Risk").count(),"review_count":companies.filter(status__in=["High Risk","Needs Review","Suspicious"]).count()})

@login_required
def scan_history(request):
    return render(request,"scan-history.html",{"active":"history","jobs":JobCheck.objects.filter(user=request.user).order_by("-created_at")[:30],"companies":CompanyCheck.objects.filter(user=request.user).order_by("-created_at")[:30]})

@login_required
def resources(request):
    return render(request,"resources.html",{"active":"resources","resources":[("Recruiter verification","Compare recruiter contact details with the company official website."),("Payment red flags","Review registration, training, processing and security-deposit requests carefully."),("Credential protection","Never share OTPs, UPI PINs, card security codes or banking passwords for recruitment."),("Evidence checklist","Keep screenshots, URLs, payment requests and recruiter messages for reports."),("Safer application flow","Prefer official career pages and independently verify unusual instructions."),("After a suspected scam","Stop communication, preserve evidence and use appropriate official reporting channels.")]})

@staff_required
def admin_jobs(request):
    return render(request,"admin-jobs.html",{"active":"jobs","jobs":JobCheck.objects.select_related("user").order_by("-created_at")[:100]})

@staff_required
def admin_threats(request):
    jobs=JobCheck.objects.select_related("user").filter(risk_level="High Risk").order_by("-created_at")
    companies=CompanyCheck.objects.select_related("user").filter(status__in=["High Risk","Needs Review","Suspicious"]).order_by("-created_at")
    return render(request,"admin-threats.html",{"active":"threats","jobs":jobs[:50],"companies":companies[:50],"high_jobs":jobs.count(),"review_companies":companies.count()})

@staff_required
def admin_resources(request):
    return render(request,"admin-resources.html",{"active":"resources"})
