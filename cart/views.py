from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from .cart import Cart
from store.models import Product
from django.http import JsonResponse


def cart_summary(request):
    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    international_status = cart.get_international_status()  # Nuevo
    total = cart.cart_total()
    
    # Agregar rango de stock para cada producto
    products_with_stock = []
    for product in cart_products:
        # Determinar rango según si es internacional
        is_international = international_status.get(str(product.id), False)
        
        if is_international:
            product.stock_range = range(1, product.stock_international + 1)
            product.is_international_item = True
        else:
            product.stock_range = range(1, product.stock + 1)
            product.is_international_item = False
            
        products_with_stock.append(product)
    
    return render(request, "cart_summary.html", {
        "cart_products": products_with_stock, 
        "quantities": quantities,
        "international_status": international_status,
        "has_international": cart.has_international_items(),
        "total": total
    })


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
