import stripe
from django.conf import settings
from django.shortcuts import redirect, render, reverse
from django.contrib.auth.decorators import login_required
from core.decorators import business_required, admin_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from .forms import IdentifyParticipantForm
from billing.models import Bill, BillParticipant
from .decorators import require_participant
from django.template.loader import render_to_string

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

    return render(request, 'payment/customer_bill.html', {
        'bill': bill,
    })


# @require_GET
# def identify_participant_modal(request, uuid):
#     try:
#         bill = Bill.objects.get(uuid=uuid)
#     except Bill.DoesNotExist:
#         return render(request, 'core/error/404.html', status=404)
#
#     return render(request, "partials/_identify_participant_modal.html", {"bill": bill})
#
#
# @require_POST
# def identify_participant_submit(request, uuid):
#     try:
#         bill = Bill.objects.get(uuid=uuid)
#     except Bill.DoesNotExist:
#         return render(request, 'core/error/404.html', status=404)
#
#     form = IdentifyParticipantForm(request.POST)
#
#     if form.is_valid():
#         participant = form.save(commit=False)
#         participant.bill = bill
#         participant.save()
#
#         # Store participant ID in session
#         request.session[f"participant_id_{bill.uuid}"] = participant.id
#         request.session.modified = True
#
#         # Return HTMX redirect to /pay/<uuid>/choose/
#         response = HttpResponse(status=204)
#         response["HX-Redirect"] = f"/pay/{bill.uuid}/choose/"
#         return response
#     else:
#         # Return just the modal, again
#         return render(request, "payment/partials/_identify_participant_modal.html", {
#             "form": form,
#             "bill": bill
#         }, status=400)
#
#     # If invalid, return the modal again with form errors
#     return render(request, "payment/customer_bill.html", {
#         "form": form,
#         "bill": bill
#     }, status=400)
#


@require_participant
def choose_payment_mode_view(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    participant = request.participant

    # If already locked into a mode, redirect
    if bill.payment_mode:
        return redirect("pay_for_bill", uuid=bill.uuid)

    return render(request, "payment/choose_mode.html", {
        "bill": bill,
        "participant": participant,
    })


@require_POST
@require_participant
def set_payment_mode(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    payment_modes = {
        'equal': 'Equally',
        'custom': 'Unequally',
        'items': 'Itemised'
    }

    participant = request.participant

    # Prevent override if locked
    if bill.payment_mode:
        return redirect('pay_for_bill', uuid=bill.uuid)

    # Get mode from POST
    mode = request.POST.get('mode')
    if mode not in payment_modes:
        return redirect('choose_payment_mode', uuid=bill.uuid)

    # Lock the bill
    bill.payment_mode = mode
    bill.payment_mode_locked_by = participant
    bill.save()

    # Redirect to the chosen mode's flow (placeholder for now)

    return redirect('pay_for_bill', uuid=bill.uuid)


def pay_for_bill(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    # Check if participant is identified (in session)
    participant_id = request.session.get(f"participant_id_{bill.uuid}")
    if not participant_id:
        # Redirect to the combined identify/choose flow
        return redirect('identify_user_and_choose', uuid=bill.uuid)

    chosen_by = bill.payment_mode_locked_by  # Participant who locked the mode

    if bill.payment_mode == 'equal':
        return redirect('split_equally', uuid=bill.uuid)
    elif bill.payment_mode == 'custom':
        return redirect('split_unequally', uuid=bill.uuid)
    elif bill.payment_mode == 'items':
        return redirect('select_items', uuid=bill.uuid)
    else:
        # No mode set? Redirect back to choose
        return redirect('choose_payment_mode', uuid=bill.uuid)


@require_GET
def check_payment_mode(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    # Always return the polling partial
    return render(request, "partials/_payment_mode_polling.html", {
        "bill": bill,
        "payment_modes": Bill.PAYMENT_MODES,
    })



def payment_mode_confirmation_modal(request, uuid, mode):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    return HttpResponse(render_to_string('payment/partials/payment_mode_modal.html', {
        'bill': bill,
        'mode': mode
    }))


def split_equally(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    chosen_by = bill.payment_mode_locked_by
    return render(request, 'payment/split_equally.html', {'bill': bill, 'chosen_by': chosen_by})


def split_unequally(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    chosen_by = bill.payment_mode_locked_by
    return render(request, 'payment/split_unequally.html', {'bill': bill, 'chosen_by': chosen_by})


def select_items(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    chosen_by = bill.payment_mode_locked_by
    return render(request, 'payment/select_items.html', {'bill': bill, 'chosen_by': chosen_by})


def identify_user_and_choose(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    if request.method == 'POST':
        # 🔥 Handle POST FIRST!
        name = request.POST.get('name')
        email = request.POST.get('email')
        mode = request.POST.get('mode')

        print("MODE RECEIVED:", mode)

        # Create participant
        participant = BillParticipant.objects.create(bill=bill, name=name, email=email)
        request.session[f"participant_id_{bill.uuid}"] = participant.id

        # Lock payment mode if needed
        if mode and not bill.payment_mode:
            bill.payment_mode = mode
            bill.payment_mode_locked_by = participant
            bill.save()

        return redirect('pay_for_bill', uuid=bill.uuid)

    # ✅ Only check session on GET requests
    participant_id = request.session.get(f"participant_id_{bill.uuid}")
    if participant_id:
        return redirect('pay_for_bill', uuid=bill.uuid)

    return render(request, 'payment/identify_user_and_choose.html', {
        'bill': bill,
        'payment_modes': Bill.PAYMENT_MODES,
    })


