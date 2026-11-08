from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from accounts import views as accounts
from catalog import views as catalog
from orders import views as orders
from orders.webhooks import stripe_event
from operations import views as operations

urlpatterns = [
    path("payments/stripe/webhook/", stripe_event, name="stripe-webhook"),
    path("health/", operations.health, name="health"),
    path("operations/logs/", operations.logs, name="event-logs"),
    path("operations/payments/<uuid:pk>/retry/", operations.retry_payment, name="retry-payment"),
    path("admin/", admin.site.urls),
    path("accounts/login/", accounts.SignIn.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/register/", accounts.register, name="register"),
    path("", catalog.stores, name="stores"),
    path("stores/<slug:slug>/", catalog.store_detail, name="store"),
    path("warehouses/", catalog.warehouses, name="warehouses"),
    path("manage/<slug:slug>/import/", catalog.import_product, name="catalog-import"),
    path("manage/", catalog.management, name="management"),
    path("manage/<slug:slug>/", catalog.manage_store, name="manage-store"),
    path("manage/<slug:slug>/inventory/<int:pk>/", catalog.edit_inventory, name="inventory-edit"),
    path("cart/<slug:slug>/", orders.cart, name="cart"),
    path("cart/<slug:slug>/items/<int:pk>/", orders.cart_item, name="cart-item"),
    path("cart/<slug:slug>/checkout/", orders.checkout, name="checkout"),
    path("orders/", orders.order_list, name="orders"),
    path("orders/<uuid:pk>/", orders.order_detail, name="order"),
    path("api/stores/", catalog.store_api, name="api-stores"),
    path("api/stores/<slug:slug>/inventory/", catalog.inventory_api, name="api-inventory"),
]
