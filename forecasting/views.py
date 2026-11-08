
from django.shortcuts import render

from inventory.models import Product
from .services import forecast_product_demand


def forecast_dashboard(request):

    products = Product.objects.all()

    forecast_results = []

    for product in products:
        result = forecast_product_demand(product.id)
        forecast_results.append(result)

    context = {
        "forecast_results": forecast_results,
    }

    return render(
        request,
        "forecasting/forecast.html",
        context
    )

