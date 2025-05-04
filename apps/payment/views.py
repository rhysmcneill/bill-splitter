import stripe
from django.conf import settings
from django.shortcuts import redirect, render, reverse
from django.contrib.auth.decorators import login_required
from core.decorators import business_required, admin_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from billing.models import Bill, BillParticipant, Payment
from .decorators import require_participant
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
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

    participant_id = request.session.get(f"participant_id_{bill.uuid}")
    if not participant_id:
        return redirect('identify_user_and_choose', uuid=bill.uuid)

    # Check if participant still exists
    try:
        participant = BillParticipant.objects.get(id=participant_id)
    except BillParticipant.DoesNotExist:
        del request.session[f"participant_id_{bill.uuid}"]
        return redirect('identify_user_and_choose', uuid=bill.uuid)

    chosen_by = bill.payment_mode_locked_by
    print("Session contents in view:", dict(request.session))

    if bill.payment_mode == 'equal':
        return redirect('equal_split', uuid=bill.uuid)
    elif bill.payment_mode == 'custom':
        return redirect('custom_split', uuid=bill.uuid)
    elif bill.payment_mode == 'items':
        return redirect('itemized_split', uuid=bill.uuid)
    else:
        # INSTEAD of redirecting to self again, render a template or redirect to a safe fallback
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
        name = request.POST.get('name')
        email = request.POST.get('email')
        mode = request.POST.get('mode')

        print("MODE RECEIVED:", mode)

        if not name or not email or not mode:
            # Handle missing fields gracefully
            return render(request, 'payment/customer_bill.html', {
                'bill': bill,
                'payment_modes': Bill.PAYMENT_MODES,
            })

        # Create the participant
        participant = BillParticipant.objects.create(
            bill=bill,
            name=name,
            email=email
        )
        request.session[f"participant_id_{bill.uuid}"] = participant.id

        # Lock the payment mode if it isn't already set
        if not bill.payment_mode:
            bill.payment_mode = mode
            bill.payment_mode_locked_by = participant
            bill.save()

        # Redirect based on split mode
        if mode == 'equal':
            return redirect('equal_split', uuid=bill.uuid)
        elif mode == 'custom':
            return redirect('custom_split', uuid=bill.uuid)
        elif mode == 'items':
            return redirect('itemized_split', uuid=bill.uuid)
        else:
            # Fallback if somehow an invalid mode slips through
            return redirect('pay_for_bill', uuid=bill.uuid)

    # Handle GET request (session check)
    participant_id = request.session.get(f"participant_id_{bill.uuid}")
    if participant_id:
        return redirect('pay_for_bill', uuid=bill.uuid)

    return render(request, 'payment/customer_bill.html', {
        'bill': bill,
        'payment_modes': Bill.PAYMENT_MODES,
    })


@require_participant
def split_equal_view(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    if request.method == 'POST':
        # First user submits participant count
        participant_count = request.POST.get('participant_count')
        if participant_count and not bill.participant_count:
            bill.participant_count = int(participant_count)
            bill.save()
        return redirect('equal_split', uuid=bill.uuid)


    #  afely pass the participant_id into the template directly
    participant_id = request.session.get(f"participant_id_{str(bill.uuid)}")

    return render(request, 'payment/equal_split.html', {
        'bill': bill,
        'participant_id': participant_id,
    })


def check_participant_count(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    if bill.participant_count:
        return HttpResponse("set")

    return HttpResponse("unset")


def participant_list_partial(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    participants = BillParticipant.objects.filter(bill=bill)
    total_amount = bill.items.aggregate(total=Sum('price'))['total'] or 0

    participant_id = request.session.get(f"participant_id_{bill.uuid}")
    has_paid = False

    if bill.payment_mode == 'equal':
        participant_count = bill.participant_count or participants.count()
        per_person = round(total_amount / participant_count, 2) if participant_count else 0
        for p in participants:
            p.amount_owed = per_person

            # Sum their confirmed payments
            total_paid = bill.payments.filter(
                status='confirmed',
                payer_email=p.email  # or however you associate payments to participants
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Assign status
            if total_paid == 0:
                p.payment_status = 'unpaid'
            elif total_paid >= p.amount_owed:
                p.payment_status = 'paid'
            else:
                p.payment_status = 'partial'

            if str(p.id) == str(participant_id) and p.payment_status == "paid":
                has_paid = True



    return render(request, 'partials/_participant_list.html', {
        'bill': bill,
        'participants': participants,
        'participant_id': participant_id,
        'has_paid': has_paid,
    })


@require_POST
@require_participant
def pay_my_share(request, uuid, participant_id):
    try:
        bill = Bill.objects.get(uuid=uuid)
        participant = BillParticipant.objects.get(id=participant_id)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    participant_id = request.session.get(f"participant_id_{bill.uuid}")

    if not participant_id:
        return redirect('identify_user_and_choose', uuid=bill.uuid)

    # Calculate owed amount
    total_amount = bill.total_amount
    per_person = round(total_amount / (bill.participant_count or 1), 2)

    # Record a fake "confirmed" payment (replace with Stripe later)
    Payment.objects.create(
        business=bill.business,
        bill=bill,
        amount=per_person,
        payer_email=participant.email,
        payment_method='bank',  # or 'stripe'
        status='confirmed',
    )

    confirmed_total = bill.payments.filter(status='confirmed').aggregate(total=Sum('amount'))['total'] or 0
    if confirmed_total >= bill.total_amount:
        bill.status = 'paid'
    elif confirmed_total > 0:
        bill.status = 'partial'
    else:
        bill.status = 'unpaid'
    bill.save()

    return redirect('equal_split', uuid=bill.uuid)



@csrf_exempt
@require_POST
@require_participant
def create_checkout_session(request, uuid, participant_id):
    bill = Bill.objects.get(uuid=uuid)
    participant = BillParticipant.objects.get(id=participant_id)

    # Amount calculation
    total_amount = bill.total_amount
    per_person = round(total_amount / (bill.participant_count or 1), 2)

    # Stripe amount is in pence (for GBP)
    stripe_amount = int(per_person * 100)

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'gbp',
                'product_data': {
                    'name': f'Share of Bill {bill.uuid}',
                    'description': f'{participant.name} is paying their share',
                },
                'unit_amount': stripe_amount,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri(
            reverse('payment_success', kwargs={'uuid': bill.uuid, 'participant_id': participant.id})
        ),
        cancel_url=request.build_absolute_uri(
            reverse('equal_split', kwargs={'uuid': bill.uuid})
        ),
        metadata={
            'participant_id': participant.id,
            'bill_id': bill.id,
        }
    )

    return redirect(session.url, code=303)


@require_GET
def payment_success(request, uuid, participant_id):
    bill = Bill.objects.get(uuid=uuid)
    participant = BillParticipant.objects.get(id=participant_id)

    total_amount = bill.total_amount
    per_person = round(total_amount / (bill.participant_count or 1), 2)

    # Record the payment
    Payment.objects.create(
        business=bill.business,
        bill=bill,
        amount=per_person,
        payer_email=participant.email,
        payment_method='stripe',
        status='confirmed',
    )

    confirmed_total = bill.payments.filter(status='confirmed').aggregate(total=Sum('amount'))['total'] or 0
    if confirmed_total >= bill.total_amount:
        bill.status = 'paid'
    elif confirmed_total > 0:
        bill.status = 'partial'
    else:
        bill.status = 'unpaid'
    bill.save()

    return redirect('equal_split', uuid=bill.uuid)
