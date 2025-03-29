from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.decorators import business_required
from django.views.decorators.http import require_POST
from .forms import BillForm, BillItemFormSet
from django.contrib import messages
from .models import Bill, Payment
from .helpers.formset import get_bill_item_formset

@login_required
@business_required
def list_bill_view(request, business_slug):
    business = request.business
    bills = Bill.objects.filter(business=business).order_by('-created_at')

    for bill in bills:
        bill.total_paid = sum(p.amount for p in bill.payments.filter(status='confirmed'))
        bill.total_due = bill.total_amount

    return render(request, 'billing/bill_list.html', {
        'bills': bills,
        'business': business
    })


@login_required
@business_required
def create_bill_view(request, business_slug):
    business = request.business

    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.business = business
            BillItemFormSet = get_bill_item_formset(creating_new=True)
            formset = BillItemFormSet(request.POST or None)

            if formset.is_valid():
                bill.save()
                items = formset.save(commit=False)
                for item in items:
                    item.business = business
                    item.save()
                formset.save_m2m()
                messages.success(request, "The bill was created successfully! 🎉")
                return redirect('list_bill', business_slug=business.slug)
        else:
            BillItemFormSet = get_bill_item_formset(creating_new=True)
            formset = BillItemFormSet(request.POST or None)
    else:
        form = BillForm()
        bill = Bill(business=business)  # Unsaved parent
        BillItemFormSet = get_bill_item_formset(creating_new=True)
        formset = BillItemFormSet(instance=bill)

    return render(request, 'billing/create_bill.html', {
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

