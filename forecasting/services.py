
from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import TruncDate

from sklearn.linear_model import LinearRegression

from inventory.models import Product, StockTransaction


def forecast_product_demand(product_id):

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return {
            "error": "Product not found."
        }

    # Get historical stock-out transactions grouped by date
    daily_transactions = (
        StockTransaction.objects
        .filter(
            product=product,
            transaction_type="OUT"
        )
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(demand=Sum("quantity"))
        .order_by("day")
    )

    history = list(daily_transactions)

    # No historical demand
    if not history:
        return {
            "product": product.name,
            "current_stock": product.quantity,
            "daily_average": 0,
            "forecast_7_days": 0,
            "estimated_days_left": None,
            "message": "Not enough historical demand data."
        }

    demands = [
        float(item["demand"])
        for item in history
    ]

    # Average daily demand
    daily_average = sum(demands) / len(demands)

    # Machine learning prediction
    if len(history) >= 3:

        X = [
            [index]
            for index in range(len(demands))
        ]

        y = demands

        model = LinearRegression()
        model.fit(X, y)

        future_days = [
            [index]
            for index in range(len(demands), len(demands) + 7)
        ]

        predictions = model.predict(future_days)

        forecast_7_days = max(
            0,
            round(float(predictions.sum()))
        )

        method = "Linear Regression"

    else:

        # Fallback when there are fewer than 3 days of data
        forecast_7_days = round(daily_average * 7)

        method = "Average Demand"

    # Estimate remaining stock duration
    estimated_days_left = None

    if daily_average > 0:
        estimated_days_left = round(
            product.quantity / daily_average,
            1
        )

    return {
        "product": product.name,
        "sku": product.sku,
        "current_stock": product.quantity,
        "daily_average": round(daily_average, 2),
        "forecast_7_days": forecast_7_days,
        "estimated_days_left": estimated_days_left,
        "method": method
    }
