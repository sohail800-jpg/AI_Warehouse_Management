
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.db.models import F, Sum

from inventory.models import (
    Product,
    Supplier,
    Warehouse,
    Category,
    StockTransaction
)

from .gemini_service import ask_gemini


# ==========================================
# 1. LIVE WAREHOUSE INFORMATION
# ==========================================

def get_warehouse_data():

    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_suppliers = Supplier.objects.count()
    total_warehouses = Warehouse.objects.count()

    total_stock = Product.objects.aggregate(
        total=Sum('quantity')
    )['total'] or 0

    total_value = sum(
        product.unit_price * product.quantity
        for product in Product.objects.all()
    )

    low_stock = Product.objects.filter(
        quantity__lte=F('reorder_level')
    )

    # Supplier details
    suppliers = Supplier.objects.all()
    supplier_details = []

    for supplier in suppliers:
        supplier_details.append(
            f"Name: {supplier.name}, "
            f"Contact Person: {supplier.contact_person}, "
            f"Email: {supplier.email}, "
            f"Phone: {supplier.phone}, "
            f"Address: {supplier.address}"
        )

    # Warehouse details
    warehouses = Warehouse.objects.all()

    warehouse_details = [
        f"Name: {warehouse.name}, Location: {warehouse.location}"
        for warehouse in warehouses
    ]

    # Product details
    products = Product.objects.select_related(
        'category',
        'storage_location'
    ).all()

    product_details = []

    for product in products:
        product_details.append(
            f"Name: {product.name}, "
            f"SKU: {product.sku}, "
            f"Category: {product.category.name}, "
            f"Price: ₹{product.unit_price}, "
            f"Quantity: {product.quantity}, "
            f"Reorder Level: {product.reorder_level}"
        )

    # Low stock details
    low_stock_details = [
        f"{p.name}: {p.quantity} units "
        f"(Reorder level: {p.reorder_level})"
        for p in low_stock
    ]

    # Recent stock transactions
    recent_transactions = StockTransaction.objects.select_related(
        'product'
    ).order_by('-created_at')[:10]

    transaction_details = [
        f"{t.transaction_type}: {t.quantity} units of "
        f"{t.product.name}"
        for t in recent_transactions
    ]

    return f"""
    WAREHOUSE DATABASE INFORMATION

    Total Products: {total_products}
    Total Categories: {total_categories}
    Total Suppliers: {total_suppliers}
    Total Warehouses: {total_warehouses}

    SUPPLIER DETAILS:
    {supplier_details}

    WAREHOUSE DETAILS:
    {warehouse_details}

    Total Stock Units: {total_stock}
    Total Inventory Value: ₹{total_value}

    LOW STOCK PRODUCTS:
    {low_stock_details}

    PRODUCT DETAILS:
    {product_details}

    RECENT STOCK TRANSACTIONS:
    {transaction_details}
    """


# ==========================================
# 2. PRODUCT SEARCH
# ==========================================

def find_product_in_question(question):

    question = question.lower()

    for product in Product.objects.all():

        if (
            product.name.lower() in question
            or product.sku.lower() in question
        ):
            return product

    return None


# ==========================================
# 3. REORDER RECOMMENDATIONS
# ==========================================

def get_reorder_recommendations():

    low_stock_products = Product.objects.filter(
        quantity__lte=F('reorder_level')
    )

    if not low_stock_products.exists():

        return "All products have sufficient stock. No reorder is required."

    recommendations = []

    for item in low_stock_products:

        recommended_quantity = max(
            0,
            (item.reorder_level * 2) - item.quantity
        )

        recommendations.append(
            f"{item.name} (SKU: {item.sku}) - "
            f"Current Stock: {item.quantity}, "
            f"Reorder Level: {item.reorder_level}, "
            f"Suggested Order: {recommended_quantity} units"
        )

    return "\n".join(recommendations)


# ==========================================
# 4. STOCK MOVEMENT ANALYSIS
# ==========================================

def get_stock_movement(product=None):

    transactions = StockTransaction.objects.all()

    if product:
        transactions = transactions.filter(product=product)

    stock_in = transactions.filter(
        transaction_type='IN'
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    stock_out = transactions.filter(
        transaction_type='OUT'
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    net_movement = stock_in - stock_out

    return (
        f"Stock In: {stock_in} units\n"
        f"Stock Out: {stock_out} units\n"
        f"Net Movement: {net_movement} units"
    )


# ==========================================
# 5. INVENTORY PERFORMANCE ANALYTICS
# ==========================================

def get_inventory_analytics():

    products = Product.objects.all()

    total_value = sum(
        item.unit_price * item.quantity
        for item in products
    )

    out_of_stock = products.filter(
        quantity=0
    ).count()

    most_expensive = products.order_by(
        '-unit_price'
    ).first()

    most_stocked = products.order_by(
        '-quantity'
    ).first()

    return {
        'total_value': total_value,
        'out_of_stock': out_of_stock,
        'most_expensive': most_expensive,
        'most_stocked': most_stocked
    }


# ==========================================
# 6. CHATBOT RESPONSE
# ==========================================

@csrf_exempt
@require_POST
def chatbot_response(request):

    try:

        data = json.loads(request.body)
        question = data.get('message', '').strip()

        if not question:
            return JsonResponse({
                'answer': 'Please enter a question.'
            }, status=400)

        question_lower = question.lower()

        product = find_product_in_question(question_lower)

        # SUPPLIER INFORMATION

        if any(word in question_lower for word in [
            'supplier', 'suppliers', 'vendor', 'vendors'
        ]):

            suppliers = Supplier.objects.all()

            if not suppliers.exists():
                answer = "There are no suppliers registered in the system."
            else:
                details = []

                for supplier in suppliers:
                    details.append(
                        f"Name: {supplier.name}\n"
                        f"Contact Person: {supplier.contact_person}\n"
                        f"Email: {supplier.email}\n"
                        f"Phone: {supplier.phone}\n"
                        f"Address: {supplier.address}"
                    )

                answer = (
                    f"TOTAL SUPPLIERS: {suppliers.count()}\n\n"
                    + "\n\n".join(details)
                )

            return JsonResponse({'answer': answer})

        # WAREHOUSE INFORMATION

        if any(word in question_lower for word in [
            'warehouse', 'warehouses'
        ]):

            warehouses = Warehouse.objects.all()

            if not warehouses.exists():
                answer = "There are no warehouses registered."
            else:
                details = [
                    f"{w.name} - {w.location}"
                    for w in warehouses
                ]

                answer = (
                    f"TOTAL WAREHOUSES: {warehouses.count()}\n\n"
                    + "\n".join(details)
                )

            return JsonResponse({'answer': answer})

        # PRODUCT STOCK CHECK

        if product and any(word in question_lower for word in [
            'stock', 'quantity', 'available', 'how many', 'in stock'
        ]):

            return JsonResponse({
                'answer': (
                    f"{product.name} has "
                    f"{product.quantity} units available."
                )
            })

        # PRODUCT PRICE CHECK

        if product and any(word in question_lower for word in [
            'price', 'cost'
        ]):

            return JsonResponse({
                'answer': (
                    f"The price of {product.name} is "
                    f"₹{product.unit_price}."
                )
            })

        # STOCK MOVEMENT

        if any(word in question_lower for word in [
            'movement',
            'stock in',
            'stock out',
            'stock transaction'
        ]):

            movement = get_stock_movement(product)

            return JsonResponse({
                'answer': (
                    "STOCK MOVEMENT ANALYSIS:\n\n"
                    + movement
                )
            })

        # REORDER RECOMMENDATIONS

        if any(word in question_lower for word in [
            'restock',
            'reorder',
            'low stock',
            'replenish'
        ]):

            recommendations = get_reorder_recommendations()

            return JsonResponse({
                'answer': (
                    "LOW STOCK AND REORDER RECOMMENDATIONS:\n\n"
                    + recommendations
                )
            })

        # INVENTORY PERFORMANCE ANALYTICS

        if any(word in question_lower for word in [
            'inventory value',
            'total value',
            'most expensive',
            'highest stock',
            'most stocked',
            'out of stock'
        ]):

            analytics = get_inventory_analytics()

            answer = (
                "INVENTORY PERFORMANCE ANALYTICS\n\n"
                f"Total Inventory Value: ₹{analytics['total_value']}\n"
                f"Out of Stock Products: {analytics['out_of_stock']}\n"
            )

            if analytics['most_expensive']:
                answer += (
                    f"Most Expensive Product: "
                    f"{analytics['most_expensive'].name}\n"
                )

            if analytics['most_stocked']:
                answer += (
                    f"Product with Highest Stock: "
                    f"{analytics['most_stocked'].name} "
                    f"({analytics['most_stocked'].quantity} units)"
                )

            return JsonResponse({'answer': answer})

        # GEMINI AI RESPONSE

        warehouse_data = get_warehouse_data()

        answer = ask_gemini(
            question,
            warehouse_data
        )

        return JsonResponse({'answer': answer})

    except json.JSONDecodeError:

        return JsonResponse({
            'answer': 'Invalid request data.'
        }, status=400)

    except Exception as error:

        print("Chatbot Error:", error)

        return JsonResponse({
            'answer': 'Sorry, something went wrong. Please try again.'
        }, status=500)


# ==========================================
# 7. CHATBOT PAGE
# ==========================================

def chatbot_page(request):

    return render(
        request,
        'chatbot/chat.html'
    )


# ==========================================
# 8. INVENTORY INSIGHTS
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

    out_of_stock = products.filter(quantity=0)

    highest_stock = products.order_by('-quantity')[:5]

    context = {
        'total_value': total_value,
        'total_stock': total_stock,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'highest_stock': highest_stock,
    }

    return render(
        request,
        'inventory/insights.html',
        context
    )
