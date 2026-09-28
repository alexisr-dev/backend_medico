from django.contrib.postgres.operations import BtreeGistExtension, CITextExtension
from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    run_before = [
        ("usuarios", "0001_initial"),
        ("citas", "0001_initial"),
        ("citas", "0002_initial"),
    ]

    operations = [
        CITextExtension(),
        BtreeGistExtension(),
    ]
