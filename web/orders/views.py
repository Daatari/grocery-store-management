import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from catalog.models import Inventory, Store
from accounts.customers import request_customer
from .forms import CheckoutForm, QuantityForm
from .models import Cart, Order
from . import services


def cart_context(user, store, checkout_key=None):
    cart = Cart.objects.filter(customer=user, store=store).first()
    lines = list(cart.lines.filter(quantity__gt=0).select_related("inventory__product")) if cart else []
    cents = sum(line.quantity * line.inventory.price_cents for line in lines)
    return {"store": store, "cart_state": cart.state if cart else "open", "lines": lines, "total": f"{cents // 100}.{cents % 100:02d}",
            "checkout_form": CheckoutForm(initial={"checkout_key": checkout_key or uuid.uuid4()})}


@require_GET
def cart(request, slug):
    store = get_object_or_404(Store, slug=slug, is_active=True)
    return render(request, "orders/cart.html", cart_context(request_customer(request), store))


@require_POST
def cart_item(request, slug, pk):
    store = get_object_or_404(Store, slug=slug, is_active=True)
    get_object_or_404(Inventory, pk=pk, store=store)
    form = QuantityForm(request.POST)
    if form.is_valid():
        try:
            services.set_quantity(request_customer(request), store, pk, **form.cleaned_data)
            messages.success(request, "Cart updated.")
            return redirect("cart", slug=slug)
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "error.html", {"message": " ".join(error for errors in form.errors.values() for error in errors),
                                          "back_url": f"/stores/{slug}/"}, status=400)


@require_POST
def checkout(request, slug):
    store = get_object_or_404(Store, slug=slug, is_active=True)
    form = CheckoutForm(request.POST)
    if form.is_valid():
        try:
            order = services.checkout(request_customer(request), store, **form.cleaned_data)
            messages.success(request, "Order queued. Payments use simulation or Stripe test mode only.")
            return redirect("order", pk=order.pk)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
    else:
        messages.error(request, "Invalid checkout request. Please try again.")
    return render(request, "orders/cart.html", cart_context(request_customer(request), store), status=409)


@require_GET
def order_list(request):
    return render(request, "orders/list.html", {"orders": Order.objects.filter(customer=request_customer(request)).select_related("store").order_by("-created_at")})


@require_GET
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("store"), pk=pk, customer=request_customer(request))
    return render(request, "orders/detail.html", {"order": order, "lines": order.lines.all()})
