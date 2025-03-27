from django import forms
from .models import Bill, BillItem
from django.forms import inlineformset_factory


class BillForm(forms.ModelForm):
    table_number = forms.IntegerField(label="Table Number")

    class Meta:
        model = Bill
        fields = ['table_number', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

BillItemFormSet = inlineformset_factory(
    Bill,
    BillItem,
    fields=['name', 'price'],
    extra=1,
    can_delete=True
)
