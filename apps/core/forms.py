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


class ChangeRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role']

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        self.target_user = kwargs.get('instance')
        super().__init__(*args, **kwargs)

        all_choices = self.fields['role'].choices

        # Case 1: Admin – only allow 'admin' or 'staff'
        if self.current_user.role == 'admin':
            self.fields['role'].choices = [
                (value, label)
                for value, label in all_choices
                if value in ['admin', 'staff']
            ]

        # Case 2: Owner modifying another owner – only allow 'business_owner'
        elif (
            self.current_user.role == 'business_owner'
            and self.target_user.role == 'business_owner'
        ):
            self.fields['role'].choices = [
                (value, label)
                for value, label in all_choices
                if value == 'business_owner'
            ]

        # Case 3: Owner modifying non-owner – allow all roles
        else:
            self.fields['role'].choices = all_choices


class UpdateProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2 shadow-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2 shadow-sm'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2 shadow-sm'}),
        }
