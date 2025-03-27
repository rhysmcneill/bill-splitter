from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.decorators import business_required
from django.views.decorators.http import require_POST
from .forms import BillForm, BillItemFormSet
from django.contrib import messages
from .models import Bill, Payment


@login_required
@business_required
def bill_list_view(request, business_slug):
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
            formset = BillItemFormSet(request.POST, instance=bill)

            if formset.is_valid():
                bill.save()
                items = formset.save(commit=False)
                for item in items:
                    item.business = business
                    item.save()
                formset.save_m2m()
                messages.success(request, "The bill was created successfully! 🎉")
                return redirect('bill_list', business_slug=business.slug)
        else:
            formset = BillItemFormSet(request.POST)
    else:
        form = BillForm()
        bill = Bill(business=business)  # Unsaved parent
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
    return redirect('bill_list', business_slug=business_slug)
