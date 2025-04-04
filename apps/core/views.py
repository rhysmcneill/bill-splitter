from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views import View
from django.shortcuts import render, redirect
from .forms import BusinessSignupForm, BusinessLoginForm
from .models import CustomUser, Business
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import HttpResponseForbidden
from .decorators import business_required


@business_required
@login_required
def dashboard_view(request, business_slug):
    business = request.business
    return render(request, 'core/dashboard.html', {
        'business': business
    })


@login_required
@business_required
def business_settings_view(request, slug):
    try:
        business = Business.objects.get(slug=slug)
    except Business.DoesNotExist:
        return render(request, 'core/error/404.html', {
            'message': "Business not found."
        }, status=404)

    if business != request.business:
        return render(request, 'core/error/403.html', {
            'message': "You don’t have permission to access this business’s settings."
        }, status=403)

    return render(request, 'core/settings.html', {
        'business': business,
    })


def landing_view(request):
    # Session-aware redirect
    if request.user.is_authenticated and getattr(request, 'business', None):
        return redirect('business_dashboard', business_slug=request.business.slug)
    return render(request, 'core/landing.html')


# Sign up view
class SignupView(View):
    def get(self, request):
        form = BusinessSignupForm()
        return render(request, 'core/signup.html', {'form': form})

    def post(self, request):
        form = BusinessSignupForm(request.POST)
        if form.is_valid():
            # Create business
            business = Business.objects.create(
                name=form.cleaned_data['business_name'],
                slug=form.cleaned_data['business_name'].lower().replace(' ', '-')
            )

            # Create user and link to business
            user = form.save(commit=False)
            user.business = business
            user.save()

            login(request, user)
            messages.success(request, "Account created successfully. Welcome to dividr! 🎉")
            return redirect('business_dashboard', business_slug=business.slug)

        # Pass form errors back to template
        return render(request, 'core/signup.html', {'form': form})



class LoginView(View):
    def get(self, request):
        form = BusinessLoginForm()
        return render(request, 'core/login.html', {'form': form})

    def post(self, request):
        form = BusinessLoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier']
            password = form.cleaned_data['password']

            # First try matching a username
            user = authenticate(request, username=identifier, password=password)

            # If no user found, try resolving the business slug
            if user is None:
                try:
                    business = Business.objects.get(slug=identifier)
                    user = CustomUser.objects.filter(business=business).first()
                    if user:
                        user = authenticate(request, username=user.username, password=password)
                except Business.DoesNotExist:
                    pass

            if user is not None and user.business:
                login(request, user)
                messages.success(request, "Login Success. Welcome to dividr! 🎉")
                return redirect('business_dashboard', business_slug=user.business.slug)
            else:
                messages.error(request, "Login failed ⛔ <br><br> Check that your details are correct and try again.")
                return render(request, 'core/login.html', {'form': form})

        return render(request, 'core/login.html', {'form': form})

