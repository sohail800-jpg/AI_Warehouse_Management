
from django.db import models
from django.shortcuts import render

from .models import (
    Product,
    Category,
    Supplier,
    Warehouse,
    StockTransaction,
    PurchaseOrder,
    SalesOrder
)


# ==========================================
# MAIN DASHBOARD
# ==========================================

def dashboard(request):

    # General Statistics
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_suppliers = Supplier.objects.count()
    total_warehouses = Warehouse.objects.count()

    total_stock = sum(
        product.quantity
        for product in Product.objects.all()
    )

    # Purchase Order Statistics
    total_purchase_orders = PurchaseOrder.objects.count()

    pending_purchase_orders = PurchaseOrder.objects.filter(
        status='PENDING'
    ).count()

    received_purchase_orders = PurchaseOrder.objects.filter(
        status='RECEIVED'
    ).count()

    # Sales Order Statistics
    total_sales_orders = SalesOrder.objects.count()

    pending_sales_orders = SalesOrder.objects.filter(
        status='PENDING'
    ).count()

    dispatched_sales_orders = SalesOrder.objects.filter(
        status='DISPATCHED'
    ).count()

    # Recent Purchase Orders
    recent_purchase_orders = PurchaseOrder.objects.select_related(
        'supplier'
    ).order_by('-order_date')[:5]

    # Recent Sales Orders
    recent_sales_orders = SalesOrder.objects.order_by(
        '-order_date'
    )[:5]

    # Total Inventory Value
    total_inventory_value = sum(
        product.quantity * product.unit_price
        for product in Product.objects.all()
    )

    # Active Products
    active_products = Product.objects.filter(
        quantity__gt=0
    ).count()

    # Low Stock Products
    low_stock_products = Product.objects.filter(
        quantity__lte=models.F('reorder_level')
    )

    # Recent Stock Transactions
    recent_transactions = StockTransaction.objects.order_by(
        '-created_at'
    )[:5]

    # Inventory Category Chart
    category_data = Category.objects.annotate(
        product_count=models.Count('products')
    )

    category_labels = [
        category.name for category in category_data
    ]

    category_values = [
        category.product_count for category in category_data
    ]

    # Stock Movement Statistics
    stock_in = StockTransaction.objects.filter(
        transaction_type='IN'
    ).aggregate(
        total=models.Sum('quantity')
    )['total'] or 0

    stock_out = StockTransaction.objects.filter(
        transaction_type='OUT'
    ).aggregate(
        total=models.Sum('quantity')
    )['total'] or 0

    # Dashboard Context
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_suppliers': total_suppliers,
        'total_warehouses': total_warehouses,
        'total_stock': total_stock,

        'total_purchase_orders': total_purchase_orders,
        'pending_purchase_orders': pending_purchase_orders,
        'received_purchase_orders': received_purchase_orders,

        'total_sales_orders': total_sales_orders,
        'pending_sales_orders': pending_sales_orders,
        'dispatched_sales_orders': dispatched_sales_orders,

        'recent_purchase_orders': recent_purchase_orders,
        'recent_sales_orders': recent_sales_orders,

        'total_inventory_value': total_inventory_value,
        'active_products': active_products,

        'low_stock_products': low_stock_products,
        'recent_transactions': recent_transactions,

        'category_labels': category_labels,
        'category_values': category_values,

        'stock_in': stock_in,
        'stock_out': stock_out,
    }

    return render(
        request,
        'inventory/dashboard.html',
        context
    )


# ==========================================
# INVENTORY INSIGHTS
# ==========================================

def inventory_insights(request):

    products = Product.objects.all()

    total_value = sum(
        product.unit_price * product.quantity
        for product in products
    )

    total_stock = products.aggregate(
        total=models.Sum('quantity')
    )['total'] or 0

    low_stock = products.filter(
        quantity__lte=models.F('reorder_level'),
        quantity__gt=0
    )

    out_of_stock = products.filter(
        quantity=0
    )

    highest_stock = products.order_by(
        '-quantity'
    )[:5]

    # Top 5 Product Chart Data
    stock_labels = [
        product.name for product in highest_stock
    ]

    stock_values = [
        product.quantity for product in highest_stock
    ]

    # Stock Status Counts
    low_stock_count = low_stock.count()
    out_of_stock_count = out_of_stock.count()

    healthy_stock_count = products.filter(
        quantity__gt=models.F('reorder_level')
    ).count()

    # Active Products
    active_products = products.filter(
        quantity__gt=0
    ).count()

    context = {
        'total_value': total_value,
        'total_stock': total_stock,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'highest_stock': highest_stock,
        'stock_labels': stock_labels,
        'stock_values': stock_values,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'healthy_stock_count': healthy_stock_count,
        'active_products': active_products,
    }

    return render(
        request,
        'inventory/insights.html',
        context
    )


# ==========================================
# LOW STOCK ALERTS
# ==========================================

def low_stock_alerts(request):

    products = Product.objects.filter(
        quantity__lte=models.F('reorder_level')
    ).select_related(
        'category'
    ).order_by('quantity')

    alert_products = []

    for product in products:

        suggested_quantity = max(
            0,
            (product.reorder_level * 2) - product.quantity
        )

        alert_products.append({
            'name': product.name,
            'sku': product.sku,
            'category': product.category.name,
            'current_stock': product.quantity,
            'reorder_level': product.reorder_level,
            'suggested_quantity': suggested_quantity,
            'status': (
                'Out of Stock'
                if product.quantity == 0
                else 'Low Stock'
            )
        })

    context = {
        'alert_products': alert_products,
        'total_alerts': len(alert_products),
    }

    return render(
        request,
        'inventory/low_stock_alerts.html',
        context
    )
