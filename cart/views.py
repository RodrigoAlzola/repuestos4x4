from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from .cart import Cart
from store.models import Product
from django.http import JsonResponse

# Create your views here.
def cart_summary(request):
    # Get the cart
    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    total = cart.cart_total()
    return render(request, "cart_summary.html", {"cart_products": cart_products, "quantities":quantities, "total": total})

def cart_add(request):
    # Get the cart
    cart = Cart(request)

    # Test the post
    if request.POST.get('action') == 'post':
        # Get the stuff
        product_id = int(request.POST.get('product_id'))
        product_quantity = int(request.POST.get('product_quantity'))
        # Look product in DB
        product = get_object_or_404(Product, id=product_id)
        # Save to a session
        cart.add(product=product, quantity=product_quantity)

        # Get cart quantity
        cart_quantity = cart.__len__()

        # Return response
        # response = JsonResponse({'Product Name': product.name})
        response = JsonResponse({'quantity': cart_quantity})
        messages.success(request, ("Product added to Cart."))
        return response


def cart_delete(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        
        # Call delete func in Cart
        cart.delete(product=product_id)

        response = JsonResponse({'product': product_id})
        messages.success(request, ("Item deleted from your Cart."))
        return response
    

def cart_update(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        product_quantity = int(request.POST.get('product_quantity'))

        cart.update(product=product_id, quantity=product_quantity)

        response = JsonResponse({'quiantity': product_quantity})
        messages.success(request, ("Your Cart has been Updated."))
        return response
