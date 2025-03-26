from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.decorators import business_required
from .forms import BillForm, BillItemFormSet
from .models import BillItem

from .models import Bill

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
                return redirect('business_dashboard', business_slug=business.slug)
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

