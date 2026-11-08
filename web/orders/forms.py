from django import forms
from django.conf import settings


class QuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, max_value=99)
    replace = forms.BooleanField(required=False)


class CheckoutForm(forms.Form):
    contact_name = forms.CharField(max_length=100, required=False, label="Name for pickup")
    contact_email = forms.EmailField(required=False, label="Email (optional in this demo)")
    provider = forms.ChoiceField(choices=[("simulator", "Local simulator")], initial="simulator")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.STRIPE_SECRET_KEY.startswith("sk_test_"):
            self.fields["provider"].choices += [("stripe", "Stripe test checkout")]

    checkout_key = forms.UUIDField(widget=forms.HiddenInput)
    scenario = forms.ChoiceField(choices=[("approve", "Approve payment"), ("decline", "Decline payment"),
        ("timeout", "Delayed response (retry safely)")], initial="approve", label="Payment simulation")
