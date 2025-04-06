from django.contrib.auth.decorators import login_required
from django.views import View
from django.shortcuts import render, redirect, reverse
from .forms import BusinessSignupForm, BusinessLoginForm, BusinessInfoForm, InviteUserForm
from .models import CustomUser as User, Business
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .decorators import business_required, admin_required
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .utils.password_generator import generate_temp_password
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash


#######################################
#       Dashboard/Business views
#######################################

def landing_view(request):
    # Session-aware redirect
    if request.user.is_authenticated and getattr(request, 'business', None):
        return redirect('business_dashboard', business_slug=request.business.slug)
    return render(request, 'core/landing.html')


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
        return render(request, 'core/error/404.html', status=404)

    if business != request.business:
        return render(request, 'core/error/403.html', status=403)

    return render(request, 'core/settings.html', {
        'business': business,
    })


@login_required
@business_required
def update_business_info_view(request, slug):
    try:
        business = Business.objects.get(slug=slug)
    except Business.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    if business != request.business:
        return render(request, 'core/error/403.html', status=403)

    if request.method == 'POST':
        form = BusinessInfoForm(request.POST, instance=business)
        if form.is_valid():
            form.save()
            messages.success(request, "Business details were updated successfully ✅")
            return redirect('business_settings', slug=slug)
        else:
            # Return partial with errors (form stays open)
            return render(request, 'core/partials/_update_business.html', {
                'form': form,
                'business': business,
            }, status=400)  # Helps HTMX detect error
    else:
        form = BusinessInfoForm(instance=business)

    return render(request, 'core/partials/_update_business.html', {
        'form': form,
        'business': business,
    })

@login_required
@business_required
def team_management_view(request, slug):
    try:
        business = Business.objects.get(slug=slug)
    except Business.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    if business != request.business:
        return render(request, 'core/error/403.html', status=403)

    team_members = User.objects.filter(business=business)

    return render(request, 'core/team.html', {
        'business': business,
        'team_members': team_members,
    })


#######################################
#       Login/Signup/Password views
#######################################
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
            user.role = 'business_owner'
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
                    user = User.objects.filter(business=business).first()
                    if user:
                        user = authenticate(request, username=user.username, password=password)
                except Business.DoesNotExist:
                    pass

            if user is not None and user.business:
                login(request, user)

                #  Check if it is a new user and must change their password
                if getattr(user, 'must_change_password', False):
                    request.session['must_change_password'] = True
                    return redirect('force_password_change')

                messages.success(request, "Login Success. Welcome to dividr! 🎉")
                return redirect('business_dashboard', business_slug=user.business.slug)
            else:
                messages.error(request, "Login failed ⛔ <br><br> Check that your details are correct and try again.")
                return render(request, 'core/login.html', {'form': form})

        return render(request, 'core/login.html', {'form': form})


@login_required
@business_required
@admin_required
def invite_team_member_view(request, slug):
    business = request.business

    if request.method == 'POST':
        form = InviteUserForm(request.POST, request_user=request.user)
        if form.is_valid():
            email = form.cleaned_data['email']
            role = form.cleaned_data['role']

            # Prevent assigning business_owner unless the requester is also one
            if role == 'business_owner' and request.user.role != 'business_owner':
                messages.error(request, "Only the business owner can assign the 'Owner' role.")
                return redirect('team_management', slug=business.slug)

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                messages.warning(request, f"{email} is already a member.")
                return redirect('team_management', slug=business.slug)

            # Create the new user
            temp_password = generate_temp_password()
            username = email.split('@')[0]

            user = User.objects.create_user(
                username=username,
                email=email,
                password=temp_password,
                role=role,
                business=business,
                must_change_password=True
            )

            # Send HTML email invite
            context = {
                'business': business,
                'user': user,
                'temp_password': temp_password,
                'login_url': request.build_absolute_uri(reverse('login'))
            }

            subject = f"You've been invited to join {business.name} on Dividr 🎉"
            from_email = "no-reply@dividr.com"
            to_email = [email]

            text_content = render_to_string('core/emails/invite_user.txt', context)
            html_content = render_to_string('core/emails/invite_user.html', context)

            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            try:
                msg.send()
            except Exception as e:
                print("Email send failed:", e)

            return redirect('team_management', slug=business.slug)
    else:
        form = InviteUserForm(request_user=request.user)

    return render(request, 'core/partials/_invite_user.html', {
        'form': form,
        'business': business,
    })



@login_required
def force_password_change_view(request):
    if not request.session.get('must_change_password'):
        return redirect('business_dashboard', business_slug=request.user.business.slug)

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            user.must_change_password = False
            user.save()
            update_session_auth_hash(request, user)  # Keeps them logged in
            request.session.pop('must_change_password', None)
            messages.success(request, "Password updated. You're all set!  ✅")
            return redirect('business_dashboard', business_slug=user.business.slug)
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'core/change_password.html', {
        'form': form
    })
