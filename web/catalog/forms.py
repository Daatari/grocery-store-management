from django import forms


class InventoryForm(forms.Form):
    price_cents = forms.IntegerField(min_value=0, max_value=10000000, label="Price in cents")
    stock = forms.IntegerField(min_value=0, max_value=1000000)
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    is_active = forms.BooleanField(required=False, label="Available to customers")


class SearchForm(forms.Form):
    query = forms.CharField(min_length=2, max_length=80, label="Product, brand or category")

class ListingForm(forms.Form):
    name = forms.CharField(max_length=100)
    category = forms.CharField(max_length=80)
    price_cents = forms.IntegerField(min_value=0, max_value=10000000, label="Store price (CAD cents)")
    stock = forms.IntegerField(min_value=0, max_value=1000000, initial=0, label="Opening stock")
    token = forms.CharField(required=False, widget=forms.HiddenInput, max_length=16000)
