from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies=[("scanner","0001_initial"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.AlterField(model_name="companycheck",name="domain",field=models.CharField(max_length=200,blank=True)),
        migrations.AlterField(model_name="companycheck",name="risk_score",field=models.IntegerField(default=0)),
        migrations.AlterField(model_name="companycheck",name="status",field=models.CharField(max_length=30,default="Low Risk")),
        migrations.AlterField(model_name="companycheck",name="user",field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="company_checks",to=settings.AUTH_USER_MODEL)),
    ]
