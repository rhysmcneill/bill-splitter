from django.db import models
import uuid
from core.models import Business


class Bill(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    table_number = models.CharField(max_length=10)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    PAYMENT_MODES = [
        ("equal", "Equally"),
        ("custom", "Unequally"),
        ("items", "Itemised"),
    ]
    ...
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODES, null=True, blank=True)
    participant_count = models.PositiveIntegerField(null=True, blank=True)
    payment_mode_locked_by = models.ForeignKey(
        'BillParticipant',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='locked_bills'
    )
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

    @property
    def progress_pct(self):
        total_paid = sum(p.amount for p in self.payments.filter(status='confirmed'))
        return (total_paid / self.total_amount * 100) if self.total_amount > 0 else 0

    def __str__(self):
        return f"Bill {self.uuid} - Table {self.table_number}"

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
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} payment of £{self.amount}"


class BillParticipant(models.Model):
    bill = models.ForeignKey("Bill", related_name="participants", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    is_initiator = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email}) - {'Initiator' if self.is_initiator else 'Guest'}"