# Generated by Django 4.2.20 on 2025-03-26 18:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('billing', '0002_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Item',
            new_name='BillItem',
        ),
        migrations.AddField(
            model_name='bill',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]
