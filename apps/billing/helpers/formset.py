from django.forms import inlineformset_factory
from ..models import Bill, BillItem

def get_bill_item_formset(creating_new=False):
    return inlineformset_factory(
        Bill,
        BillItem,
        fields=['name', 'price'],
        extra=1 if creating_new else 0,
        can_delete=True
    )
