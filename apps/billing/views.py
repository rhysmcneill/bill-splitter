import base64
import os
import qrcode
import tempfile
from io import BytesIO

from billing.ocr.service import extract_items_from_receipt
from core.decorators import business_required
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from qrcode.image.pil import PilImage

from .forms import BillForm
from .helpers.formset import get_bill_item_formset
from .helpers.pagination import paginate_queryset
from .models import Bill
from .ocr.service import extract_items_from_receipt


@login_required
@business_required
def list_bill_view(request, business_slug):
    business = request.business
    bills = Bill.objects.filter(business=business).order_by('-created_at')

    # Apply filters
    status = request.GET.get('status')
    table = request.GET.get('table')
    min_total = request.GET.get('min_total')
    max_total = request.GET.get('max_total')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if status:
        bills = bills.filter(status=status)
    if table:
        bills = bills.filter(table_number__icontains=table)
    if start_date:
        bills = bills.filter(created_at__date__gte=start_date)
    if end_date:
        bills = bills.filter(created_at__date__lte=end_date)
    if table:
        bills = bills.filter(table_number=table)

    # Calculate total_paid and total_due per bill
    for bill in bills:
        bill.total_paid = sum(p.amount for p in bill.payments.filter(status='confirmed'))
        bill.total_due = sum(i.price for i in bill.items.all())

    # Filter by total price after computing it
    if min_total:
        bills = [b for b in bills if b.total_due >= float(min_total)]
    if max_total:
        bills = [b for b in bills if b.total_due <= float(max_total)]

    # Quick stats
    unpaid_bills = [b for b in bills if b.status == 'unpaid']
    unpaid_count = len(unpaid_bills)
    unpaid_total = sum(b.total_due for b in unpaid_bills)

    filters_applied = any(
        param in request.GET for param in ['status', 'table', 'min_total', 'max_total', 'start_date', 'end_date']
    )

    # Pagination
    per_page = int(request.GET.get('per_page', 5))  # default to 5
    page_obj, querystring = paginate_queryset(request, bills, per_page=per_page)

    return render(request, 'billing/bill_list.html', {
        'bills': page_obj.object_list,
        'business': business,
        'unpaid_count': unpaid_count,
        'unpaid_total': unpaid_total,
        'filters_applied': filters_applied,
        'page_obj': page_obj,
        'querystring': querystring,
        'per_page': per_page,
    })


@login_required
@business_required
def create_bill_view(request, business_slug):
    business = request.business

    if not business.stripe_account_id:
        messages.error(request, "❌ You need to set up a Stripe account before creating bills - Go to"
                                " Business Settings and configure your Stripe account")
        return redirect('business_dashboard', business_slug=business.slug)

    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.business = business
            bill.save()

            BillItemFormSet = get_bill_item_formset(creating_new=True)
            formset = BillItemFormSet(request.POST, instance=bill)

            if formset.is_valid():
                items = formset.save(commit=False)
                for item in items:
                    item.business = business
                    item.bill = bill
                    item.save()

                formset.save_m2m()
                return redirect('bill_qr', business_slug=business.slug, uuid=bill.uuid)
        else:
            BillItemFormSet = get_bill_item_formset(creating_new=True)
            formset = BillItemFormSet(request.POST or None)
    else:
        form = BillForm()
        bill = Bill(business=business)  # Unsaved parent
        BillItemFormSet = get_bill_item_formset(creating_new=True)
        formset = BillItemFormSet(instance=bill)

    return render(request, 'billing/bill_create.html', {
        'form': form,
        'formset': formset
    })


@require_POST
@login_required
@business_required
def delete_bill_view(request, business_slug, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid, business=request.business)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    bill.delete()
    return redirect('list_bill', business_slug=business_slug)


@login_required
@business_required
def update_bill_view(request, business_slug, uuid):
    business = request.business

    try:
        bill = Bill.objects.get(uuid=uuid, business=business)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    if bill.business != request.user.business:
        return render(request, 'core/error/403.html', status=403)

    BillItemFormSet = get_bill_item_formset(creating_new=False)

    if request.method == 'POST':
        form = BillForm(request.POST, instance=bill)
        formset = BillItemFormSet(request.POST, instance=bill, prefix='items')

        if form.is_valid() and formset.is_valid():
            form.save()

            # Save without committing to add business manually
            items = formset.save(commit=False)

            # Save new/changed items
            for item in items:
                item.business = bill.business
                item.save()

            # Delete items marked for deletion
            for obj in formset.deleted_objects:
                obj.delete()

            messages.success(request, f"The bill for table {bill.table_number} was updated successfully! ✅")
            return redirect('list_bill', business_slug=business.slug)

    else:
        form = BillForm(instance=bill)
        formset = BillItemFormSet(instance=bill, prefix='items')

    return render(request, 'billing/bill_update.html', {
        'form': form,
        'formset': formset,
        'bill': bill,
    })


@login_required
@business_required
def view_bill_view(request, business_slug, uuid):
    business = request.business
    bills = Bill.objects.filter(business=business)
    try:
        bill = Bill.objects.get(uuid=uuid, business=request.business)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    if bill.business != request.user.business:
        return render(request, 'core/error/403.html', status=403)

    # Calculate totals only for this bill
    bill.total_paid = sum(p.amount for p in bill.payments.filter(status='confirmed'))
    bill.total_due = bill.total_amount

    return render(request, 'billing/bill_view.html', {
        'bill': bill,
        'items': bill.items.all()
    })


def upload_receipt_view(request):
    if request.method == "POST" and request.FILES.get("receipt"):
        try:
            uploaded_file = request.FILES["receipt"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            try:
                result = extract_items_from_receipt(tmp_path)
                return JsonResponse({
                    "items": result["items"],
                    "low_confidence": result["low_confidence"],
                    "total_confidence": result["total_confidence"],
                })
            except ValueError as ve:
                print(f"🔥 OCR Upload Error: {ve}")
                return JsonResponse({"error": str(ve)}, status=400)
            except Exception as e:
                print(f"🔥 OCR Upload Error: {e}")
                return JsonResponse({"error": "Unexpected error during OCR."}, status=500)
            finally:
                os.remove(tmp_path)

        except Exception as e:
            print(f"🔥 File Save Error: {e}")
            return JsonResponse({"error": "Failed to upload file."}, status=500)

    return JsonResponse({"error": "No file uploaded."}, status=400)


@business_required
def bill_qr_view(request, business_slug, uuid):
    try:
        bill = Bill.objects.get(uuid=uuid)
    except Bill.DoesNotExist:
        return render(request, 'core/error/404.html', status=404)

    # Ensure the bill belongs to the correct business
    if bill.business.slug != business_slug:
        return render(request, 'core/error/403.html', status=403)

    # Build absolute URL to /pay/<uuid> page
    qr_url = f"{settings.SITE_DOMAIN}/pay/{bill.uuid}/"

    # Generate QR Code using the latest qrcode library style
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(image_factory=PilImage)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'qr/bill_qr.html', {
        'bill': bill,
        'qr_code_base64': qr_base64,
        'qr_url': qr_url,
    })

