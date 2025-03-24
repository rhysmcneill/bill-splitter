from django.db import models
from django.contrib.auth.models import AbstractUser


class Business(models.Model):
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, unique=True)

    # Business payment configuration
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('stripe', 'Stripe Connect'),
            ('paypal', 'Paypal Business'),
            ('bank', 'Bank Transfer')
        ],
        default='bank'
    )

    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_email = models.CharField(max_length=255, blank=True, null=True)
    bank_account_name = models.CharField(max_length=255, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    bank_sort_code = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    # Business User
    business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.username


