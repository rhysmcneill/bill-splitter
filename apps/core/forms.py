from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class SignupForm(UserCreationForm):
    business_name = forms.CharField(max_length=100)

    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'business_name']


class BusinessLoginForm(forms.Form):
    identifier = forms.CharField(label="Username or Business Slug")
    password = forms.CharField(widget=forms.PasswordInput)
