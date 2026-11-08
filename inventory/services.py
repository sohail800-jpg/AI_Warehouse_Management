
from django.db.models import F

from .models import (
    Product,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    StockTransaction
)


def get_low_stock_products():

    products = Product.objects.filter(
        quantity__lte=F("reorder_level")
    ).select_related("category")

    alerts = []

    for product in products:

        suggested_quantity = max(
            0,
            (product.reorder_level * 2) - product.quantity
        )

        alerts.append({
            "product": product.name,
            "sku": product.sku,
            "current_stock": product.quantity,
            "reorder_level": product.reorder_level,
            "suggested_quantity": suggested_quantity,
            "status": (
                "Out of Stock"
                if product.quantity == 0
                else "Low Stock"
            )
        })

    return alerts


from forecasting.services import forecast_product_demand


def generate_reorder_recommendations():

    products = Product.objects.all()

    recommendations = []

    for product in products:

        forecast = forecast_product_demand(product.id)

        if "error" in forecast:
            continue

        forecast_demand = forecast["forecast_7_days"]

        # Maintain additional safety stock equal to reorder level
        target_stock = forecast_demand + product.reorder_level

        reorder_quantity = max(
            0,
            target_stock - product.quantity
        )

        if reorder_quantity > 0:

            estimated_cost = (
                reorder_quantity * product.unit_price
            )

            recommendations.append({
                "product": product.name,
                "sku": product.sku,
                "current_stock": product.quantity,
                "forecast_demand": forecast_demand,
                "reorder_quantity": reorder_quantity,
                "estimated_cost": round(float(estimated_cost), 2)
            })

    return recommendations


from django.db import transaction
from .models import Supplier, PurchaseOrder, PurchaseOrderItem


@transaction.atomic
def create_purchase_order(supplier_id):

    # Get supplier
    supplier = Supplier.objects.get(id=supplier_id)

    # Generate ML reorder recommendations
    recommendations = generate_reorder_recommendations()

    if not recommendations:
        raise ValueError("No products require reordering.")

    # Create purchase order
    purchase_order = PurchaseOrder.objects.create(
        supplier=supplier,
        status="PENDING",
        notes="Generated from ML reorder recommendations"
    )

    order_items = []

    for item in recommendations:

        product = Product.objects.get(sku=item["sku"])

        order_items.append(
            PurchaseOrderItem(
                purchase_order=purchase_order,
                product=product,
                quantity=item["reorder_quantity"],
                unit_price=product.unit_price
            )
        )

    PurchaseOrderItem.objects.bulk_create(order_items)

    return purchase_order


def approve_purchase_order(order_id):

    with transaction.atomic():

        order = PurchaseOrder.objects.select_for_update().get(
            id=order_id
        )

        if order.status != "PENDING":
            raise ValidationError(
                "Only pending orders can be approved."
            )

        order.status = "APPROVED"
        order.save(update_fields=["status"])

        return order


def receive_purchase_order(order_id):

    with transaction.atomic():

        order = PurchaseOrder.objects.select_for_update().get(
            id=order_id
        )

        if order.status != "APPROVED":
            raise ValidationError(
                "Only approved orders can be received."
            )

        items = order.items.select_related("product").all()

        if not items.exists():
            raise ValidationError(
                "Purchase order has no items."
            )

        for item in items:

            product = Product.objects.select_for_update().get(
                id=item.product_id
            )

            product.quantity += item.quantity
            product.save(update_fields=["quantity", "updated_at"])

            StockTransaction.objects.create(
                product=product,
                transaction_type="IN",
                quantity=item.quantity,
                reference=f"PO-{order.id}",
                notes="Stock received against purchase order"
            )

        order.status = "RECEIVED"
        order.save(update_fields=["status"])

        return order

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    Product,
    StockTransaction,
    SalesOrder,
    SalesOrderItem
)


@transaction.atomic
def create_sales_order(customer_name, delivery_address, items,
                       customer_email="", customer_phone=""):

    order = SalesOrder.objects.create(
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        status="PENDING"
    )

    for item in items:
        product = Product.objects.get(id=item["product_id"])

        if item["quantity"] <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        SalesOrderItem.objects.create(
            sales_order=order,
            product=product,
            quantity=item["quantity"],
            unit_price=product.unit_price
        )

    return order


@transaction.atomic
def approve_sales_order(order_id):

    order = SalesOrder.objects.select_for_update().get(id=order_id)

    if order.status != "PENDING":
        raise ValidationError("Only pending orders can be approved.")

    if not order.items.exists():
        raise ValidationError("Sales order has no items.")

    order.status = "APPROVED"
    order.save(update_fields=["status"])

    return order


@transaction.atomic
def dispatch_sales_order(order_id):

    order = SalesOrder.objects.select_for_update().get(id=order_id)

    if order.status != "APPROVED":
        raise ValidationError("Only approved orders can be dispatched.")

    items = order.items.select_related("product").all()

    if not items.exists():
        raise ValidationError("Sales order has no items.")

    # Check stock availability for every item first.
    for item in items:
        product = Product.objects.select_for_update().get(id=item.product_id)

        if product.quantity < item.quantity:
            raise ValidationError(
                f"Insufficient stock for {product.name}. "
                f"Available: {product.quantity}, Required: {item.quantity}"
            )

    # Reduce stock and create transactions.
    for item in items:
        product = Product.objects.select_for_update().get(id=item.product_id)

        product.quantity -= item.quantity
        product.save(update_fields=["quantity", "updated_at"])

        StockTransaction.objects.create(
            product=product,
            transaction_type="OUT",
            quantity=item.quantity,
            reference=f"SO-{order.id}",
            notes="Stock dispatched against sales order"
        )

    order.status = "DISPATCHED"
    order.save(update_fields=["status"])

    return order



@transaction.atomic
def adjust_stock(product_id, transaction_type, quantity, reference="", notes=""):

    if transaction_type not in ["IN", "OUT"]:
        raise ValidationError("Transaction type must be IN or OUT.")

    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    product = Product.objects.select_for_update().get(id=product_id)

    if transaction_type == "OUT" and product.quantity < quantity:
        raise ValidationError(
            f"Insufficient stock. Available: {product.quantity}"
        )

    if transaction_type == "IN":
        product.quantity += quantity
    else:
        product.quantity -= quantity

    product.save(update_fields=["quantity", "updated_at"])

    stock_transaction = StockTransaction.objects.create(
        product=product,
        transaction_type=transaction_type,
        quantity=quantity,
        reference=reference,
        notes=notes
    )

    return stock_transaction

