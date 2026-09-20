# JobSafe — Premium Job Fraud Intelligence & Protection Platform

A fresh premium JobSafe build with **header navigation instead of a sidebar**. The dashboard and all major modules are available from the top navigation.

## Main modules
- Dashboard
- Job Safety Scanner
- Company Intelligence
- Screenshot / Evidence Scanner
- Scam Reports
- Scan History
- Analytics
- Threat Center
- Safety Guide
- Resources
- Activity
- Notifications
- Profile
- Settings
- Admin Dashboard
- Admin Users
- Admin Jobs
- Admin Companies
- Admin Reports
- Admin Analytics
- Admin Threats
- System Monitor
- Admin Resources

## Run
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver
```

## GitHub deployment
Push this folder to GitHub. For a Django hosting service, use:

Build command:
`pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`

Start command:
`gunicorn jobsafe.wsgi:application`

Set `SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS` in production.

## Important
The risk engine is rule-based and explainable. Company checks use the submitted company, website and recruiter-domain signals; public company lookup remains a separate optional Wikidata integration.
