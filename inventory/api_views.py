
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from .models import (
    Category,
    Product,
    Supplier,
    Warehouse,
    StorageLocation,
    StockTransaction,
    PurchaseOrder,
    SalesOrder
)

from .serializers import (
    CategorySerializer,
    ProductSerializer,
    SupplierSerializer,
    WarehouseSerializer,
    StorageLocationSerializer,
    StockTransactionSerializer,
    PurchaseOrderSerializer,
    SalesOrderSerializer
)

from .services import (
    create_purchase_order,
    approve_purchase_order,
    receive_purchase_order,
    create_sales_order,
    approve_sales_order,
    dispatch_sales_order,
    adjust_stock
)


# ==========================================
# CATEGORY API
# ==========================================

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


# ==========================================
# PRODUCT API
# ==========================================

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


# ==========================================
# SUPPLIER API
# ==========================================

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


# ==========================================
# WAREHOUSE API
# ==========================================

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer


# ==========================================
# STORAGE LOCATION API
# ==========================================

class StorageLocationViewSet(viewsets.ModelViewSet):
    queryset = StorageLocation.objects.all()
    serializer_class = StorageLocationSerializer


# ==========================================
# STOCK TRANSACTION API
# ==========================================

class StockTransactionViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            stock_transaction = adjust_stock(
                product_id=data["product"].id,
                transaction_type=data["transaction_type"],
                quantity=data["quantity"],
                reference=data.get("reference", ""),
                notes=data.get("notes", "")
            )

            response_serializer = self.get_serializer(
                stock_transaction
            )

            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except ValidationError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )


# ==========================================
# PURCHASE ORDER API
# ==========================================

class PurchaseOrderViewSet(viewsets.ModelViewSet):

    queryset = PurchaseOrder.objects.select_related(
        "supplier"
    ).prefetch_related("items__product")

    serializer_class = PurchaseOrderSerializer

    # GENERATE PURCHASE ORDER
    @action(detail=False, methods=["post"])
    def generate(self, request):

        supplier_id = request.data.get("supplier_id")

        if not supplier_id:
            return Response(
                {"error": "supplier_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = create_purchase_order(
                supplier_id=int(supplier_id)
            )

            return Response(
                self.get_serializer(order).data,
                status=status.HTTP_201_CREATED
            )

        except (Supplier.DoesNotExist, ValueError) as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # APPROVE PURCHASE ORDER
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):

        try:
            order = approve_purchase_order(pk)

            return Response(
                self.get_serializer(order).data
            )

        except PurchaseOrder.DoesNotExist:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # RECEIVE PURCHASE ORDER
    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):

        try:
            order = receive_purchase_order(pk)

            return Response(
                self.get_serializer(order).data
            )

        except PurchaseOrder.DoesNotExist:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ==========================================
# SALES ORDER API
# ==========================================

class SalesOrderViewSet(viewsets.ModelViewSet):

    queryset = SalesOrder.objects.prefetch_related(
        "items__product"
    ).all()

    serializer_class = SalesOrderSerializer

    # CREATE CUSTOMER SALES ORDER
    @action(detail=False, methods=["post"])
    def create_order(self, request):

        try:
            order = create_sales_order(
                customer_name=request.data.get("customer_name"),
                customer_email=request.data.get("customer_email", ""),
                customer_phone=request.data.get("customer_phone", ""),
                delivery_address=request.data.get("delivery_address"),
                items=request.data.get("items", [])
            )

            return Response(
                self.get_serializer(order).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # APPROVE SALES ORDER
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):

        try:
            order = approve_sales_order(pk)

            return Response(
                self.get_serializer(order).data
            )

        except SalesOrder.DoesNotExist:
            return Response(
                {"error": "Sales order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # DISPATCH SALES ORDER
    @action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch_order(self, request, pk=None):

        try:
            order = dispatch_sales_order(pk)

            return Response(
                self.get_serializer(order).data
            )

        except SalesOrder.DoesNotExist:
            return Response(
                {"error": "Sales order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )
