import json
import re

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import JobCheck, CompanyCheck


def normalize_text(text):
    text = str(text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def analyze(text, url=""):
    t = normalize_text(f"{text} {url}")
    flags = []
    score = 5
    patterns = [
        (["registration fee", "registration fees", "registration charge", "joining fee", "joining charges", "application fee", "application charges", "processing fee", "processing charges", "training fee", "training charges", "security deposit", "refundable deposit", "pay first", "pay before joining", "pay to get job", "pay to get internship"], 35, "Payment or registration fee requested"),
        (["deposit money", "send money", "transfer money", "pay money", "make a payment", "payment required", "pay rs", "pay ₹", "pay inr", "upi payment", "send payment"], 30, "Money transfer or payment requirement detected"),
        (["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "rediffmail.com"], 15, "Personal or non-corporate email domain detected"),
        (["whatsapp only", "whatsapp me", "contact on whatsapp", "contact us on whatsapp", "message on whatsapp", "telegram only", "telegram me", "contact on telegram", "contact us on telegram"], 18, "Off-platform messaging pressure detected"),
        (["urgent", "immediately", "today only", "limited seats", "limited vacancies", "act now", "apply now", "within 24 hours", "last chance", "hurry", "offer expires"], 12, "Urgency or pressure language detected"),
        (["guaranteed job", "guaranteed internship", "guaranteed placement", "100% placement", "100% job guarantee", "job guaranteed", "easy money", "quick money", "earn money easily", "work from home guaranteed", "fixed income guaranteed"], 25, "Unrealistic job or income promise detected"),
        (["no interview", "without interview", "no interview required", "direct selection", "direct joining", "instant joining", "instant job", "selected without interview"], 18, "Unusual or unrealistic hiring claim detected"),
        (["otp", "one time password", "upi pin", "bank password", "net banking password", "atm pin", "cvv", "card details", "credit card number", "debit card number", "verification code", "login password"], 40, "Sensitive credential or banking information requested"),
        (["crypto", "bitcoin", "cryptocurrency", "gift card", "usdt", "wallet address"], 25, "Suspicious cryptocurrency or gift-card request detected"),
        (["lottery", "prize", "reward", "claim your money", "claim reward", "you have won", "winner", "lucky winner"], 20, "Suspicious reward or prize language detected"),
        (["registration link", "verify your account", "verify immediately", "click this link", "click the link", "download this app", "install this app", "download apk"], 15, "Suspicious verification or external-link instruction detected"),
        (["send your documents", "send documents immediately", "send aadhaar", "aadhaar card", "pan card", "passport copy", "bank statement", "bank account details"], 15, "Sensitive personal or financial document request detected"),
        (["referral fee", "membership fee", "membership charge", "course fee", "certificate fee", "verification fee", "background verification fee"], 25, "Employment-related fee or charge detected"),
        (["paytm", "phonepe", "google pay", "gpay", "upi id"], 10, "Payment-platform information detected"),
    ]
    for words, points, reason in patterns:
        if any(word in t for word in words):
            score += points
            flags.append(reason)
    url_text = normalize_text(url)
    if url_text and any(item in url_text for item in ["bit.ly", "tinyurl.com", "t.co/", "cutt.ly", "is.gd", "shorturl.at", "rebrand.ly", "rb.gy"]):
        score += 15
        flags.append("URL shortener detected; verify the destination before applying")
    if re.search(r"(₹|rs\.?|inr)\s?\d[\d,]*", t) and any(word in t for word in ["pay", "fee", "charge", "deposit", "payment", "registration", "joining"]):
        score += 20
        flags.append("Specific monetary amount associated with a job-related request detected")
    if "whatsapp" in t and any(word in t for word in ["pay", "fee", "deposit", "money"]):
        score += 10
        flags.append("Payment request combined with WhatsApp communication detected")
    flags = list(dict.fromkeys(flags))
    score = min(score, 99)
    level = "High Risk" if score >= 70 else "Suspicious" if score >= 35 else "Safe"
    if not flags:
        flags = ["No major scam signals detected by the JobSafe rule engine"]
    return score, level, flags


@login_required
def check_job(request):
    result = None
    if request.method == "POST":
        title = request.POST.get("title", "Untitled Job").strip() or "Untitled Job"
        company = request.POST.get("company", "").strip()
        url = request.POST.get("url", "").strip()
        description = request.POST.get("description", "").strip()
        score, level, flags = analyze(description, url)
        obj = JobCheck.objects.create(user=request.user, title=title, company=company, url=url, description=description, risk_score=score, risk_level=level, reasons="|".join(flags))
        result = {"obj": obj, "flags": flags}
    return render(request, "check-job.html", {"result": result, "active": "job"})


@login_required
@ensure_csrf_cookie
def screenshot_scanner(request):
    return render(request, "screenshot-scanner.html", {"active": "scan"})


@login_required
@require_POST
def analyze_screenshot(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "Invalid request data."}, status=400)
    text = str(data.get("text", "")).strip()
    url = str(data.get("url", "")).strip()
    if not text:
        return JsonResponse({"success": False, "error": "No text was provided for analysis."}, status=400)
    score, level, flags = analyze(text, url)
    return JsonResponse({"success": True, "risk_score": score, "risk_level": level, "reasons": flags, "extracted_text": text})


@login_required
def company_check(request):
    result = None
    if request.method == "POST":
        company = request.POST.get("company", "Unknown Company").strip() or "Unknown Company"
        website = request.POST.get("website", "").strip()
        domain = request.POST.get("domain", "").strip()
        score = 10
        signals = []
        if not website:
            score += 25
            signals.append("No official website supplied")
        elif not website.lower().startswith("https://"):
            score += 15
            signals.append("Website does not use HTTPS")
        else:
            signals.append("HTTPS website supplied")
        free_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "rediffmail.com"]
        if not domain:
            score += 20
            signals.append("Recruiter email domain was not supplied")
        elif any(domain.lower().endswith("@" + x) or domain.lower() == x or x in domain.lower() for x in free_domains):
            score += 35
            signals.append("Recruiter contact uses a free email provider")
        else:
            signals.append("Recruiter domain appears corporate")
        if any(x in website.lower() for x in ["bit.ly", "tinyurl.com", "cutt.ly", "rb.gy"]):
            score += 20
            signals.append("Shortened website URL detected")
        score = min(score, 95)
        status = "High Risk" if score >= 60 else "Needs Review" if score >= 35 else "Low Risk"
        record = CompanyCheck.objects.create(user=request.user, company=company, website=website, domain=domain, risk_score=score, status=status)
        result = {"company": company, "website": website, "domain": domain, "risk": score, "status": status, "signals": signals, "id": record.id}
    return render(request, "company-check.html", {"result": result, "active": "company"})
