import stripe
from django.conf import settings
from django.shortcuts import redirect, render, reverse
from django.contrib.auth.decorators import login_required
from core.decorators import business_required, admin_required
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from .forms import IdentifyParticipantForm
from billing.models import Bill
from .decorators import require_participant

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.publish_key = settings.STRIPE_PUBLISHABLE_KEY


@login_required
@business_required
@admin_required
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
@admin_required
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


def customer_bill_view(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    # Calculate bill totals
    bill.total_paid = sum(p.amount for p in bill.payments.filter(status='confirmed'))
    bill.total_due = sum(i.price for i in bill.items.all())

    return render(request, 'billing/customer_bill.html', {
        'bill': bill,
    })


@require_GET
def identify_participant_modal(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    return render(request, "partials/_identify_participant_modal.html", {"bill": bill})


@require_POST
def identify_participant_submit(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    form = IdentifyParticipantForm(request.POST)

    if form.is_valid():
        participant = form.save(commit=False)
        participant.bill = bill
        participant.save()

        # Store participant ID in session
        request.session[f"participant_id_{bill.uuid}"] = participant.id

        # Return HTMX redirect to /pay/<uuid>/choose/
        response = HttpResponse(status=204)
        response["HX-Redirect"] = f"/pay/{bill.uuid}/choose/"
        return response

    # If invalid, return the modal again with form errors
    return render(request, "billing/partials/_identify_participant_modal.html", {
        "form": form,
        "bill": bill
    }, status=400)
