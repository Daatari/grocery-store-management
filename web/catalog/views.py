from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from .forms import InventoryForm
from .models import Inventory, Store, InventoryEvent
from .services import managed_store, update_inventory


@require_GET
def stores(request):
    return render(request, "catalog/stores.html", {"stores": Store.objects.filter(is_active=True).order_by("name")})


@require_GET
def store_detail(request, slug):
    store = get_object_or_404(Store, slug=slug, is_active=True)
    inventory = store.inventory.filter(is_active=True).select_related("product").order_by("product__category", "product__name")
    return render(request, "catalog/store.html", {"store": store, "inventory": inventory})


@login_required
@require_GET
def management(request):
    stores = Store.objects.filter(is_active=True)
    if not request.user.is_superuser:
        stores = stores.filter(managers__user=request.user)
    return render(request, "catalog/management.html", {"stores": stores})


@login_required
@require_GET
def manage_store(request, slug):
    get_object_or_404(Store, slug=slug, is_active=True)
    store = managed_store(request.user, slug)
    return render(request, "catalog/manage_store.html", {"store": store,
        "ledger": InventoryEvent.objects.filter(inventory__store=store).select_related("inventory__product").order_by("-pk")[:30],
        "inventory": store.inventory.select_related("product").order_by("product__name"),
        "orders": store.orders.order_by("-created_at")[:20]})


@login_required
@require_http_methods(["GET", "POST"])
def edit_inventory(request, slug, pk):
    get_object_or_404(Store, slug=slug, is_active=True)
    store = managed_store(request.user, slug)
    item = get_object_or_404(Inventory.objects.select_related("product"), pk=pk, store=store)
    form = InventoryForm(request.POST if request.method == "POST" else None,
                         initial={"price_cents": item.price_cents, "stock": item.stock,
                                  "version": item.version, "is_active": item.is_active})
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            update_inventory(request.user, slug, pk, **form.cleaned_data)
            messages.success(request, "Inventory updated.")
            return redirect("manage-store", slug=slug)
        except ValidationError as error:
            form.add_error(None, error)
            status = 409
    return render(request, "catalog/edit_inventory.html", {"store": store, "item": item, "form": form}, status=status)


@require_GET
def store_api(request):
    return JsonResponse({"stores": list(Store.objects.filter(is_active=True).values("id", "slug", "name", "address"))})


@require_GET
def inventory_api(request, slug):
    store = get_object_or_404(Store, slug=slug, is_active=True)
    rows = store.inventory.filter(is_active=True).select_related("product").order_by("id")
    return JsonResponse({"store": store.slug, "currency": "CAD", "inventory": [
        {"id": row.pk, "product": row.product.name, "category": row.product.category,
         "price_cents": row.price_cents, "available": row.available} for row in rows]})


@login_required
@require_http_methods(["GET", "POST"])
def import_product(request, slug):
    from django.core import signing
    from django.db import IntegrityError
    from .forms import SearchForm, ListingForm
    from .providers import PROVIDERS
    from .importing import add_listing
    store = managed_store(request.user, slug)
    search = SearchForm(request.GET or None)
    listing = ListingForm(request.POST if request.method == "POST" else None)
    results = []
    if request.method == "GET" and search.is_valid():
        try:
            for data in PROVIDERS["openfoodfacts"].search(search.cleaned_data["query"]):
                results.append({"data": data, "form": ListingForm(initial={**data,
                    "token": signing.dumps(data, salt="catalog-preview", compress=True)})})
        except ValidationError as error:
            search.add_error(None, error)
    if request.method == "POST" and listing.is_valid():
        try:
            add_listing(request.user, slug, **listing.cleaned_data)
            messages.success(request, "Product added to this store.")
            return redirect("manage-store", slug=slug)
        except ValidationError as error:
            listing.add_error(None, error)
        except IntegrityError:
            listing.add_error(None, "Another manager imported this barcode. Search again to use that product.")
    return render(request, "catalog/import.html", {"store": store, "search": search, "listing": listing, "results": results})


@login_required
@require_http_methods(["GET", "POST"])
def warehouses(request):
    import uuid
    from django import forms
    from django.core.exceptions import PermissionDenied
    from .models import WarehouseStock, WarehouseMovement
    from .warehouse import move
    if not request.user.is_superuser:
        raise PermissionDenied
    class MovementForm(forms.Form):
        stock = forms.ModelChoiceField(queryset=WarehouseStock.objects.select_related("warehouse", "product"))
        destination = forms.ModelChoiceField(queryset=Inventory.objects.select_related("store", "product"), required=False,
            help_text="Leave blank to receive new warehouse stock. Select a store listing to transfer stock there.")
        quantity = forms.IntegerField(min_value=1, max_value=1000000)
        key = forms.UUIDField(widget=forms.HiddenInput)
    form = MovementForm(request.POST if request.method == "POST" else None, initial={"key": uuid.uuid4()})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        destination = data["destination"]
        if destination and destination.product_id != data["stock"].product_id:
            form.add_error("destination", "Select the same product at the destination store.")
        else:
            try:
                move(request.user, data["stock"].pk, data["quantity"], data["key"], destination.pk if destination else None)
                return redirect("warehouses")
            except ValidationError as error:
                form.add_error(None, error)
    return render(request, "catalog/warehouses.html", {"form": form,
        "stock": WarehouseStock.objects.select_related("warehouse", "product"),
        "movements": WarehouseMovement.objects.select_related("stock__product", "destination__store").order_by("-pk")[:30]})
