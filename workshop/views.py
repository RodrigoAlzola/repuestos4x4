from django.shortcuts import render
from cart.cart import Cart
from workshop.models import Workshop

# Create your views here.
def workshop(request):
     # Get the cart
    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    total = cart.cart_total()

    # Get all the Workshops availbale
    workshops = Workshop.objects.all()

    if request.user.is_authenticated:
        return render(request, "workshop.html", {"cart_products": cart_products, "quantities":quantities, "total": total, "workshops": workshops})
    else:
        return render(request, "workshop.html", {"cart_products": cart_products, "quantities":quantities, "total": total, "workshops": workshops})
