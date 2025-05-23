# Generated by Django 4.2.20 on 2025-04-24 17:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_bill_payment_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='payment_mode_locked_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='locked_bills', to='billing.billparticipant'),
        ),
    ]
