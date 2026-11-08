
from rest_framework.routers import DefaultRouter

from .api_views import (
    CategoryViewSet,
    ProductViewSet,
    SupplierViewSet,
    WarehouseViewSet,
    StorageLocationViewSet,
    StockTransactionViewSet,
    PurchaseOrderViewSet,
    SalesOrderViewSet
)

router = DefaultRouter()

# Inventory APIs
router.register("categories", CategoryViewSet)
router.register("products", ProductViewSet)
router.register("suppliers", SupplierViewSet)
router.register("warehouses", WarehouseViewSet)
router.register("storage-locations", StorageLocationViewSet)
router.register("stock-transactions", StockTransactionViewSet)

# Purchase Order API
router.register(
    "purchase-orders",
    PurchaseOrderViewSet,
    basename="purchase-order"
)

# Sales Order API
router.register(
    "sales-orders",
    SalesOrderViewSet,
    basename="sales-order"
)

urlpatterns = router.urls
