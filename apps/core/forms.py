from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Business

class BusinessSignupForm(UserCreationForm):
    business_name = forms.CharField(max_length=100)

    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'business_name']


class BusinessLoginForm(forms.Form):
    identifier = forms.CharField(label="Username or Business Slug")
    password = forms.CharField(widget=forms.PasswordInput)

class BusinessInfoForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['name', 'address', 'email', 'phone_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300'}),
            'address': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300'}),
            'email': forms.EmailInput(attrs={'class': 'w-full rounded border-gray-300'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300'}),
        }
