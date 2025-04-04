import stripe
from django.conf import settings
from django.shortcuts import redirect, render, reverse
from django.contrib.auth.decorators import login_required
from core.decorators import business_required

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.publish_key = settings.STRIPE_PUBLISHABLE_KEY


@login_required
@business_required
def connect_stripe_view(request, slug):
    business = request.business

    if not business.stripe_account_id:
        # Create a new Stripe connected account
        account = stripe.Account.create(
            type='express',
            country='GB',  # or your target country
            email=business.email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        )
        business.stripe_account_id = account.id
        business.save()

    # Generate an onboarding link
    account_link = stripe.AccountLink.create(
        account=business.stripe_account_id,
        refresh_url=request.build_absolute_uri(
            reverse('connect_stripe', kwargs={'slug': business.slug})
        ),
        return_url=request.build_absolute_uri(
            reverse('business_settings', kwargs={'slug': business.slug})
        ),
        type='account_onboarding',
    )

    return redirect(account_link.url)


@login_required
@business_required
def manage_stripe_account_view(request, slug):
    business = request.business

    if not business.stripe_account_id:
        # If they haven't connected yet
        return redirect('connect_stripe', slug=slug)

    # Create a login link to the Stripe Express dashboard
    try:
        login_link = stripe.Account.create_login_link(business.stripe_account_id)
        return redirect(login_link.url)
    except stripe.error.InvalidRequestError as e:
        # Optional: handle expired/nonexistent account
        return render(request, 'payment/error/stripe_error.html', {
            'message': str(e)
        }, status=400)
