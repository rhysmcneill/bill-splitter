from django.db import models
import uuid
from core.models import Business


class Bill(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    table_number = models.CharField(max_length=10)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('unpaid', 'Unpaid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Paid in Full')
        ],
        default='unpaid'
    )

    @property
    def total_amount(self):
        return sum(item.price for item in self.items.all())


class BillItem(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.name


class Payment(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payer_email = models.EmailField(blank=True, null=True)
    # Business payment configuration
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('stripe', 'Stripe'),
            ('paypal', 'Paypal'),
            ('bank', 'Bank Transfer')
        ],
        default='bank'
    ),
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('failed', 'Failed')
        ]
    ),
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} payment of £{self.amount}"
