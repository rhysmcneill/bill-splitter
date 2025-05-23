# Generated by Django 4.2.20 on 2025-04-24 18:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0009_alter_bill_payment_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bill',
            name='payment_mode',
            field=models.CharField(blank=True, choices=[('equal', 'Equally'), ('custom', 'Unequally'), ('items', 'Itemised')], max_length=10, null=True),
        ),
    ]
