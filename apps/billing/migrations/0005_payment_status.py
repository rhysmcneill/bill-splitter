# Generated by Django 4.2.20 on 2025-03-27 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_payment_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('failed', 'Failed')], default='pending', max_length=20),
        ),
    ]
