
from rest_framework import serializers
from .models import SalesOrder, SalesOrderItem

from .models import (
    Category,
    Product,
    Supplier,
    Warehouse,
    StorageLocation,
    PurchaseOrder,
    PurchaseOrderItem,
    StockTransaction
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('quantity',)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'


class StorageLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageLocation
        fields = '__all__'


class StockTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransaction
        fields = '__all__'


class PurchaseOrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    total_price = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "unit_price",
            "total_price"
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True
    )

    items = PurchaseOrderItemSerializer(
        many=True,
        read_only=True
    )

    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "order_date",
            "expected_delivery",
            "status",
            "notes",
            "items",
            "total_amount"
        ]

    def get_total_amount(self, obj):
        return sum(
            item.total_price
            for item in obj.items.all()
        )

class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    total_price = serializers.ReadOnlyField()

    class Meta:
        model = SalesOrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "unit_price",
            "total_price"
        ]


class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, read_only=True)

    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "customer_name",
            "customer_email",
            "customer_phone",
            "delivery_address",
            "order_date",
            "status",
            "notes",
            "items",
            "total_amount"
        ]

    def get_total_amount(self, obj):
        return sum(
            item.total_price for item in obj.items.all()
        )