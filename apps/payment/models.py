from django.db import models
from billing.models import Bill, BillParticipant

class UnequalShare(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='unequal_shares')
    participant = models.ForeignKey(BillParticipant, on_delete=models.CASCADE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('bill', 'participant')
