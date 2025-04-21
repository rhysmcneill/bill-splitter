# forms.py
from django import forms
from billing.models import BillParticipant


class IdentifyParticipantForm(forms.ModelForm):
    class Meta:
        model = BillParticipant
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your email'}),
        }