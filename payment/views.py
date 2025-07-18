from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress
from django.contrib import messages
from payment.models import Order, OrderItem
from django.contrib.auth.models import User
from store.models import Product, Profile
import datetime

def payment_success(request):
    return render(request, "payment/payment_success.html", {})

def checkout(request):
     # Get the cart
    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    total = cart.cart_total()

    if request.user.is_authenticated:
        # Checkout as logged in
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        return render(request, "payment/checkout.html", {"cart_products": cart_products, "quantities":quantities, "total": total, "shipping_form": shipping_form})
    else:
        #Checkout as guest
        shipping_form = ShippingForm(request.POST or None)
        return render(request, "payment/checkout.html", {"cart_products": cart_products, "quantities":quantities, "total": total, "shipping_form": shipping_form})


def billing_info(request):
    if request.POST:
        # Get the cart
        cart = Cart(request)
        cart_products = cart.get_products()
        quantities = cart.get_quants()
        total = cart.cart_total()

        # Create a session with shipping info
        my_shipping = request.POST
        request.session['my_shipping'] = my_shipping

        # Check if logged in
        if request.user.is_authenticated:
            # Lest get the Billing Form
            billing_form = PaymentForm()
            return render(request, "payment/billing_info.html", {"cart_products": cart_products, "quantities":quantities, "total": total, "shipping_info": request.POST, "billing_form": billing_form})
        else:
            # Not logged in
            billing_form = PaymentForm()
            return render(request, "payment/billing_info.html", {"cart_products": cart_products, "quantities":quantities, "total": total, "shipping_info": request.POST, "billing_form": billing_form})

        shipping_form = request.POST

    else:
        messages.success(request, "Access Denied.")
        return redirect('home')



def process_order(request):
    if request.POST:
        # Get the cart
        cart = Cart(request)
        cart_products = cart.get_products()
        quantities = cart.get_quants()
        total = cart.cart_total()

        # Get the billing info from the last page
        payment_form = PaymentForm(request.POST or None)

        # get shipping session data
        my_shipping = request.session.get('my_shipping')

        # Gather Order info
        full_name = my_shipping['shipping_full_name']
        email = my_shipping['shipping_email']
        phone = my_shipping['shipping_phone']
        # Create shipping address from session info
        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_commune']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
        amount_pay = total

        if request.user.is_authenticated:
            # logged in
            user = request.user

            # Create Order
            create_order = Order(user=user, full_name=full_name, email=email, phone=phone, shipping_address=shipping_address, amount_pay=amount_pay)
            create_order.save()

            # Add Order Item
            # Get the Order id
            order_id = create_order.pk

            # Get Product info
            for product in cart_products:
                product_id = product.id
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price

                # Get quantities
                for key, value in quantities.items():
                    if int(key) == product.id:
                        # Create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value, price=price)
                        create_order_item.save()

            # Delete the cart
            for key in list(request.session.keys()):
                if key == 'session_key':
                    del request.session[key]

            # Delete Cart from database
            current_user = Profile.objects.filter(user__id=request.user.id)
            current_user.update(old_cart="")

            messages.success(request, "Order Placed")
            return redirect('home')

        else:
            # not logged in
            # Create Order
            create_order = Order(full_name=full_name, email=email, phone=phone, shipping_address=shipping_address, amount_pay=amount_pay)
            create_order.save()

            # Add Order Item
            # Get the Order id
            order_id = create_order.pk

            # Get Product info
            for product in cart_products:
                product_id = product.id
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price

                # Get quantities
                for key, value in quantities.items():
                    if int(key) == product.id:
                        # Create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value, price=price)
                        create_order_item.save()

            # Delete the cart
            for key in list(request.session.keys()):
                if key == 'session_key':
                    del request.session[key]

            messages.success(request, "Order Placed")
            return redirect('home')

    else:
        messages.success(request, "Access Denied.")
        return redirect('home')


def not_shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=False)
        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
            order = Order.objects.filter(id=num)
            now = datetime.datetime.now()
            order.update(shipped=True, date_shipped=now)
            messages.success(request, "Shipping Status Updated.")
            return redirect('home')

        return render(request, "payment/not_shipped_dash.html", {'orders': orders})
    else:
        messages.success(request, "Access Denied.")
        return redirect('home')


def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True)
        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
            order = Order.objects.filter(id=num)
            order.update(shipped=False)
            messages.success(request, "Shipping Status Updated.")


        return render(request, "payment/shipped_dash.html", {'orders': orders})
    else:
        messages.success(request, "Access Denied.")
        return redirect('home')


def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        # Get the Order
        order = Order.objects.get(id=pk)
        items = OrderItem.objects.filter(order=pk)

        if request.POST:
            status = request.POST['shipping_status']
            # Check if true or false
            if status == 'true':
                order = Order.objects.filter(id=pk)
                now = datetime.datetime.now()
                order.update(shipped=True, date_shipped=now)
            else:
                order = Order.objects.filter(id=pk)
                order.update(shipped=False)
            messages.success(request, "Shipping Status Updated.")
            return redirect('home')

        return render(request, "payment/orders.html", {"order": order, "items": items})

    else:
        messages.success(request, "Access Denied.")
        return redirect('home')