from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderItem
from .models import SalesOrder, SalesOrderItem
from .models import (
    Category,
    Product,
    Supplier,
    Warehouse,
    StorageLocation,
    StockTransaction
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'sku', 'category', 'unit_price', 'quantity')
    search_fields = ('name', 'sku')
    list_filter = ('category',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'contact_person', 'email', 'phone')
    search_fields = ('name', 'contact_person')


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location', 'manager_name', 'capacity')
    search_fields = ('name', 'location')


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'warehouse', 'rack_number', 'bin_number')
    list_filter = ('warehouse',)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'product',
        'transaction_type',
        'quantity',
        'reference',
        'created_at'
    )

    search_fields = ('product__name', 'reference')
    list_filter = ('transaction_type', 'created_at')

    def save_model(self, request, obj, form, change):

        with transaction.atomic():

            product = Product.objects.select_for_update().get(
                pk=obj.product_id
            )

            if obj.transaction_type == 'IN':
                product.quantity += obj.quantity

            elif obj.transaction_type == 'OUT':

                if obj.quantity > product.quantity:
                    raise ValidationError(
                        f'Only {product.quantity} units are available.'
                    )

                product.quantity -= obj.quantity

            product.save(update_fields=['quantity'])

            super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return obj is None

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'supplier',
        'order_date',
        'expected_delivery',
        'status'
    )
    list_filter = ('status', 'order_date')
    search_fields = ('supplier__name',)


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'purchase_order',
        'product',
        'quantity',
        'unit_price'
    )
    search_fields = (
        'product__name',
        'purchase_order__supplier__name'
    )

class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 1


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "customer_phone",
        "order_date",
        "status",
    )

    list_filter = ("status", "order_date")
    search_fields = ("customer_name", "customer_email")
    inlines = [SalesOrderItemInline]