from django.contrib import admin
from .models import Store, Product, Inventory, ManagerAssignment, ProductSource, Warehouse, WarehouseStock
admin.site.register([Store, Product, ManagerAssignment, Warehouse])
class ReadOnly(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
admin.site.register(Inventory, ReadOnly)
admin.site.register(ProductSource, ReadOnly)
class WarehouseStockAdmin(admin.ModelAdmin):
    readonly_fields = ["quantity"]
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
admin.site.register(WarehouseStock, WarehouseStockAdmin)
