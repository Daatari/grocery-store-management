from django.core.exceptions import PermissionDenied
from .models import Customer

def customer_for(actor):
    if isinstance(actor, Customer):
        if actor.account_id and not actor.account.is_active:
            raise PermissionDenied
        return actor
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied
    return Customer.objects.get_or_create(account=actor)[0]

def request_customer(request):
    if request.user.is_authenticated:
        return customer_for(request.user)
    key = request.session.get("guest_customer")
    customer = Customer.objects.filter(guest_key=key, account__isnull=True).first() if key else None
    if customer is None:
        customer = Customer.objects.create()
        request.session["guest_customer"] = str(customer.guest_key)
    return customer
