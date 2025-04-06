from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser as User, Business


class BusinessSignupForm(UserCreationForm):
    business_name = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'business_name']


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


class InviteUserForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'w-full border border-gray-300 rounded-md px-3 py-2 shadow-sm'
    }))
    role = forms.ChoiceField(widget=forms.Select(attrs={
        'class': 'w-full border border-gray-300 rounded-md px-3 py-2 shadow-sm'
    }))

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)

        if request_user and request_user.role != 'business_owner':
            filtered_roles = [
                role for role in User.ROLE_CHOICES if role[0] != 'business_owner'
            ]
        else:
            filtered_roles = User.ROLE_CHOICES

        self.fields['role'].choices = filtered_roles

