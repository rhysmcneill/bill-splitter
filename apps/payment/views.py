import stripe
from django.conf import settings
from django.shortcuts import redirect, render, reverse
from django.contrib.auth.decorators import login_required
from core.decorators import business_required, admin_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from billing.models import Bill, BillParticipant, Payment
from .models import UnequalShare
from .decorators import require_participant
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal, InvalidOperation

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

    if bill.payment_mode == 'equal':
        return redirect('equal_split', uuid=bill.uuid)
    elif bill.payment_mode == 'custom':
        return redirect('unequal_split', uuid=bill.uuid)
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


from django.db.models import Sum
from decimal import Decimal, InvalidOperation
from billing.models import Bill, BillParticipant, Payment
from .models import UnequalShare

def split_unequally_view(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    participant_id = request.session.get(f"participant_id_{str(bill.uuid)}")
    if not participant_id:
        return redirect('identify_user_and_choose', uuid=bill.uuid)

    try:
        participant = BillParticipant.objects.get(id=participant_id)
    except BillParticipant.DoesNotExist:
        del request.session[f"participant_id_{str(bill.uuid)}"]
        return redirect('identify_user_and_choose', uuid=bill.uuid)

    error_message = None

    # Handle share submission
    if request.method == 'POST':
        percentage = request.POST.get('percentage')
        try:
            percentage = Decimal(percentage)
            if not (0 < percentage <= 100):
                raise InvalidOperation()

            # Calculate how much is already claimed (excluding this user)
            existing_total = UnequalShare.objects.filter(bill=bill).exclude(participant=participant).aggregate(
                total=Sum('percentage'))['total'] or 0

            if existing_total + percentage > 100:
                remaining = 100 - existing_total
                error_message = f"You can only claim up to {remaining:.2f}% more."
            else:
                UnequalShare.objects.update_or_create(
                    bill=bill,
                    participant=participant,
                    defaults={'percentage': percentage}
                )
                return redirect('unequal_split', uuid=bill.uuid)

        except (InvalidOperation, TypeError):
            error_message = "Please enter a valid percentage between 1 and 100."

    # Check if this user already submitted a share
    user_has_submitted_share = UnequalShare.objects.filter(
        bill=bill,
        participant=participant
    ).exists()

    has_paid = Payment.objects.filter(
        bill=bill,
        payer_email=participant.email
    ).exists()

    # Prepare data for rendering (if error occurred)
    shares = []
    total_percentage = 0
    total_amount = bill.total_amount or 0

    for share in UnequalShare.objects.filter(bill=bill):
        amount = round(Decimal(share.percentage) / 100 * total_amount, 2)
        shares.append({
            'participant': share.participant,
            'percentage': share.percentage,
            'amount': amount
        })
        total_percentage += float(share.percentage)

    return render(request, 'payment/unequal_split.html', {
        'bill': bill,
        'participant': participant,
        'participant_id': participant_id,
        'has_paid': has_paid,
        'user_has_submitted_share': user_has_submitted_share if not error_message else False,
        'error_message': error_message,
        'shares': shares,
        'total_percentage': total_percentage,
    })



def unequal_shares_partial(request, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    shares = []
    total_percentage = 0
    total_amount = bill.total_amount or 0

    for share in UnequalShare.objects.filter(bill=bill):
        amount = round(Decimal(share.percentage) / 100 * total_amount, 2)
        shares.append({
            'participant': share.participant,
            'percentage': share.percentage,
            'amount': amount
        })
        total_percentage += float(share.percentage)

    participant_id = request.session.get(f"participant_id_{str(bill.uuid)}")
    has_paid = False

    if participant_id:
        try:
            participant = BillParticipant.objects.get(id=participant_id)
            has_paid = Payment.objects.filter(bill=bill, payer_email=participant.email).exists()
            confirmed_total = bill.payments.filter(status='confirmed').aggregate(total=Sum('amount'))['total'] or 0
            paid_percentage = round(confirmed_total / total_amount * 100, 2) if total_amount else 0
        except BillParticipant.DoesNotExist:
            pass

    return render(request, 'partials/_participant_shares.html', {
        'participant': participant,
        'participant_id': participant_id,
        'shares': shares,
        'total_percentage': total_percentage,
        'bill': bill,
        'has_paid': has_paid,
        'paid_percentage': paid_percentage,
    })



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

    # Already joined? Redirect them.
    participant_id = request.session.get(f"participant_id_{bill.uuid}")
    if participant_id:
        return redirect('pay_for_bill', uuid=bill.uuid)

    # Enforce participant limit
    current_count = bill.participants.count()
    if bill.participant_count and current_count >= bill.participant_count:
        return render(request, 'payment/user_limit_reached.html', {
            'bill': bill,
            'qr_url': reverse('bill_qr', kwargs={
                'business_slug': bill.business.slug,
                'uuid': bill.uuid
            }),
            'message': "This bill already has the maximum number of participants. If you believe this is a mistake "
                       "speak to a staff member.",
        })

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        mode = request.POST.get('mode')

        if not name or not email or not mode:
            return render(request, 'payment/customer_bill.html', {
                'bill': bill,
                'payment_modes': Bill.PAYMENT_MODES,
            })

        # Re-check in POST (race condition safety)
        current_count = bill.participants.count()
        if bill.participant_count and current_count >= bill.participant_count:
            return render(request, 'payment/user_limit_reached.html', {
                'bill': bill,
                'qr_url': reverse('bill_qr', kwargs={
                    'business_slug': bill.business.slug,
                    'uuid': bill.uuid
                }),
                'message': "Sorry, this bill is already full. If you believe this is a mistake speak to a staff member.",
            })

        # Create participant
        participant = BillParticipant.objects.create(
            bill=bill,
            name=name,
            email=email
        )
        request.session[f"participant_id_{bill.uuid}"] = participant.id

        # Lock mode if not set
        if not bill.payment_mode:
            bill.payment_mode = mode
            bill.payment_mode_locked_by = participant
            bill.save()

        # Redirect by mode
        if mode == 'equal':
            return redirect('equal_split', uuid=bill.uuid)
        elif mode == 'custom':
            return redirect('unequal_split', uuid=bill.uuid)
        elif mode == 'items':
            return redirect('itemized_split', uuid=bill.uuid)
        else:
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

    # Safely pass the participant_id into the template directly
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

    # Determine the amount based on the payment mode
    if bill.payment_mode == 'equal':
        # Equal split logic
        per_person = round(bill.total_amount / (bill.participant_count or 1), 2)
        amount = per_person
    elif bill.payment_mode == 'custom':
        # Unequal split logic
        try:
            share = UnequalShare.objects.get(bill=bill, participant=participant)
            share_percentage = Decimal(share.percentage)
            amount = round((share_percentage / 100) * bill.total_amount, 2)
        except UnequalShare.DoesNotExist:
            return redirect('unequal_split', uuid=bill.uuid)
    else:
        # Unsupported mode fallback
        return redirect('pay_for_bill', uuid=bill.uuid)

    # Stripe requires amount in pence
    stripe_amount = int(amount * 100)

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'gbp',
                'product_data': {
                    'name': f'Hi {participant.name.title() }, this is for share of bill {bill.uuid}',
                    'description': f'Fill in your details to pay your share securely!',
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
            reverse('pay_for_bill', kwargs={'uuid': bill.uuid})
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

    # Determine payment amount based on mode
    if bill.payment_mode == 'equal':
        amount = round(bill.total_amount / (bill.participant_count or 1), 2)
    elif bill.payment_mode == 'custom':
        try:
            share = UnequalShare.objects.get(bill=bill, participant=participant)
            amount = round((Decimal(share.percentage) / 100) * bill.total_amount, 2)
        except UnequalShare.DoesNotExist:
            return redirect('unequal_split', uuid=bill.uuid)
    else:
        return redirect('pay_for_bill', uuid=bill.uuid)

    # Record payment
    Payment.objects.create(
        business=bill.business,
        bill=bill,
        amount=amount,
        payer_email=participant.email,
        payment_method='stripe',
        status='confirmed',
    )

    # Update bill status
    confirmed_total = bill.payments.filter(status='confirmed').aggregate(total=Sum('amount'))['total'] or 0
    if confirmed_total >= bill.total_amount:
        bill.status = 'paid'
    elif confirmed_total > 0:
        bill.status = 'partial'
    else:
        bill.status = 'unpaid'
    bill.save()

    # Redirect to correct view
    if bill.payment_mode == 'equal':
        return redirect('equal_split', uuid=bill.uuid)
    elif bill.payment_mode == 'custom':
        return redirect('unequal_split', uuid=bill.uuid)
    else:
        return redirect('pay_for_bill', uuid=bill.uuid)

