from django.db import migrations

def repair_company_domain(apps,schema_editor):
    connection=schema_editor.connection; table="scanner_companycheck"
    with connection.cursor() as cursor:
        try: columns=[row[1] for row in connection.introspection.get_table_description(cursor,table)]
        except Exception: return
        if "domain" not in columns and "email_domain" in columns:
            q=connection.ops.quote_name
            cursor.execute(f"ALTER TABLE {q(table)} RENAME COLUMN {q("email_domain")} TO {q("domain")}")

class Migration(migrations.Migration):
    dependencies=[("scanner","0002_rename_email_domain_companycheck_domain_and_more")]
    operations=[migrations.RunPython(repair_company_domain,migrations.RunPython.noop)]
