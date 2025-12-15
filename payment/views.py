from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress
from django.contrib import messages
from payment.models import Order, OrderItem
from django.contrib.auth.models import User
from store.models import Product, Profile
from store.forms import GuestUserForm, UserInfoForm
from workshop.models import Workshop
import datetime
import uuid
from store.emails import send_order_confirmation_email_async

from transbank.webpay.webpay_plus.transaction import Transaction
from django.conf import settings
import os

TRANSBANK_COMMERCE_CODE = os.environ.get('TRANSBANK_COMMERCE_CODE')
TRANSBANK_API_KEY = os.environ.get('TRANSBANK_API_KEY')


def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    total = cart.cart_total()

    personal_info = None
    guest_user_form = None

    # Workshop data
    workshop_id = workshop_id = request.POST.get('workshop_id') or request.GET.get('workshop_id')
    shipping_form = None
    is_workshop_shipping = False

    # Limpiar datos previos de sesión
    if request.method == 'GET':
       request.session.pop('guest_info', None)
      # request.session.pop('personal_shipping_info', None)
      # request.session.pop('workshop_shipping_info', None)

    # Obtener datos personales desde Profile
    if request.user.is_authenticated:
        try:
            profile = Profile.objects.get(user=request.user)
            personal_info = {
                'full_name': profile.full_name,
                'phone': profile.phone,
                'email': profile.email,
            }
            #print("DEBUG - Personal Info:", personal_info)
            #print("DEBUG - Profile phone:", profile.phone) 
        except Profile.DoesNotExist:
            #print("Profile NO encontrado para usuario:", request.user)
            personal_info = {
                'full_name': '',
                'phone': '',
                'email': '',
            }

        if workshop_id:
            try:
                selected_workshop = Workshop.objects.get(id=workshop_id)
                is_workshop_shipping = True

                shipping_data = {
                    'shipping_full_name': selected_workshop.name,
                    'shipping_phone': '',
                    'shipping_email': '',
                    'shipping_address1': selected_workshop.address1,
                    'shipping_address2': selected_workshop.address2,
                    'shipping_city': selected_workshop.city,
                    'shipping_state': selected_workshop.state,
                    'shipping_commune': selected_workshop.commune,
                    'shipping_zipcode': selected_workshop.zipcode,
                    'shipping_country': selected_workshop.country,
                }
                shipping_form = ShippingForm(initial=shipping_data)
               # request.session['workshop_shipping_info'] = shipping_data

                if request.method == 'POST':
                        print("POST recibido con taller")

                        shipping_info = shipping_data
                        billing_form = PaymentForm()

                        request.session['personal_info'] = personal_info
                        request.session['shipping_info'] = shipping_info
                        request.session['workshop_id'] = workshop_id
                        return render(request, "payment/billing_info.html", {
                            "cart_products": cart_products,
                            "quantities": quantities,
                            "total": total,
                            "shipping_info": shipping_info,
                            "personal_info": personal_info,
                            "billing_form": billing_form
                            }) 

            except Workshop.DoesNotExist:
                print("No se encontró el taller o no se envió POST")
                shipping_form = ShippingForm()


        # Si no hay taller, usar dirección personal
        else:
            is_workshop_shipping = False

            try:
                shipping_user = ShippingAddress.objects.get(user=request.user)
                shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
            except ShippingAddress.DoesNotExist:
                shipping_form = ShippingForm(request.POST or None)

            if request.method == 'POST' and shipping_form.is_valid():
                shipping_info = shipping_form.cleaned_data
                billing_form = PaymentForm()

                request.session['personal_info'] = personal_info
                request.session['shipping_info'] = shipping_info
                return render(request, "payment/billing_info.html", {
                    "cart_products": cart_products,
                    "quantities": quantities,
                    "total": total,
                    "shipping_info": shipping_info,
                    "personal_info": personal_info,
                    "billing_form": billing_form
            })       
        
    # Flujo para invitados
    else:
        workshop_id = False  # invitados no pueden seleccionar taller
        is_workshop_shipping = False
        guest_data = request.session.get('guest_info')
        guest_user_form = GuestUserForm(request.POST or None, initial=guest_data)
        if request.method == 'POST' and guest_user_form.is_valid():
            guest_data = guest_user_form.cleaned_data
            request.session['guest_info'] = guest_data
            request.session['shipping_info'] = guest_data

            personal_info = {
                'full_name': guest_data['full_name'],
                'phone': guest_data['phone'],
                'email': guest_data['email'],
            }

            shipping_info = {
                'shipping_full_name': guest_data['full_name'],
                'shipping_phone': guest_data['phone'], 
                'shipping_email': guest_data['email'],
                'shipping_address1': guest_data['address1'],
                'shipping_address2': guest_data['address2'],
                'shipping_city': guest_data['city'],
                'shipping_state': guest_data['state'],
                'shipping_commune': guest_data['commune'],
                'shipping_zipcode': guest_data['zipcode'],
                'shipping_country': guest_data['country'],
            }

            billing_form = PaymentForm()

            request.session['personal_info'] = personal_info
            request.session['shipping_info'] = shipping_info
            return render(request, "payment/billing_info.html", {
                "cart_products": cart_products,
                "quantities": quantities,
                "total": total,
                "shipping_info": shipping_info,
                "personal_info": personal_info,
                "billing_form": billing_form
            })        

    
    return render(request, "payment/checkout.html", {
        "cart_products": cart_products,
        "quantities": quantities,
        "total": total,
        "shipping_form": shipping_form,
        "personal_info": personal_info,
        "is_workshop_shipping": is_workshop_shipping,
        "guest_user_form": guest_user_form,
        "workshop_id": workshop_id,
    })



def billing_info(request):
    if request.method == 'POST':
        # Validar términos y condiciones
        terms_accepted = request.POST.get('terms_accepted')
        
        if not terms_accepted or terms_accepted != 'true':
            messages.error(request, "Debes aceptar los Términos y Condiciones para continuar.")
            return redirect('billing_info')
        
        cart = Cart(request)
        cart_products = cart.get_products()
        quantities = cart.get_quants()
        total = cart.cart_total()

        # CAMBIADO: Ahora solo busca 'shipping_info'
        shipping_info = request.session.get('shipping_info')
        personal_info = request.session.get('personal_info')

        billing_form = PaymentForm()

        return render(request, "payment/billing_info.html", {
            "cart_products": cart_products,
            "quantities": quantities,
            "total": total,
            "shipping_info": shipping_info,
            "personal_info": personal_info,
            "billing_form": billing_form
        })

    else:
        messages.error(request, "Acceso denegado.")
        return redirect('home')


def process_payment(request):
    if request.method == 'POST':
        # Obtener método de pago de la sesión
        payment_method = request.session.get('payment_method', 'webpay')
        
        if payment_method == 'webpay':
            cart = Cart(request)
            total = int(cart.cart_total())

            buy_order = str(uuid.uuid4()).replace('-', '')[:26]
            session_id = str(uuid.uuid4())
            return_url = request.build_absolute_uri('/payment/evaluate_payment')

            tx = Transaction.build_for_integration(
                settings.TRANSBANK_COMMERCE_CODE, 
                settings.TRANSBANK_API_KEY
            )

            response = tx.create(buy_order, session_id, total, return_url)

            token = response['token']
            url = response['url']

            # print(response, token, url)

            return redirect(f"{url}?token_ws={token}")
        
        elif payment_method == 'transferencia':
            # Lógica futura para transferencia bancaria
            messages.info(request, "Transferencia bancaria próximamente disponible")
            return redirect('billing_info')
        
        else:
            messages.error(request, "Método de pago no válido")
            return redirect('billing_info')
    else:
        messages.error(request, "Error processing payment.")
        return redirect('payment_failed')


def evaluate_payment(request):
    if request.GET:
        # Verificar si es una cancelación/anulación
        tbk_token = request.GET.get('TBK_TOKEN')
        tbk_orden_compra = request.GET.get('TBK_ORDEN_COMPRA')
        tbk_id_sesion = request.GET.get('TBK_ID_SESION')
        
        # Si vienen estos parámetros, el usuario canceló
        if tbk_token or tbk_orden_compra or tbk_id_sesion:
            messages.error(request, "La transacción fue cancelada o anulada.")
            return render(request, 'payment/payment_failed.html', {
                'reason': 'cancelled',
                'message': 'Cancelaste el pago en Transbank. Puedes intentar nuevamente cuando quieras.'
            })
        
        # Flujo normal - pago exitoso o rechazado
        token = request.GET.get('token_ws')
        
        if not token:
            messages.error(request, "No se recibió el token de Transbank.")
            return redirect('cart_summary')

        try:
            tx = Transaction.build_for_integration(
                settings.TRANSBANK_COMMERCE_CODE, 
                settings.TRANSBANK_API_KEY
            )
            response = tx.commit(token)

            if response['status'] == 'AUTHORIZED':
                # Pago exitoso
                order = create_order_from_session(request)
                order_items = order.orderitem_set.all()
                
                # Enviar email de confirmación
                try:
                    send_order_confirmation_email_async(order)
                except Exception as e:
                    print(f"Error enviando email de confirmación: {e}")
                
                return render(request, "payment/payment_success.html", {
                    'order': order,
                    'order_items': order_items,
                })
            else:
                # Pago rechazado
                messages.error(request, f"El pago fue rechazado. Estado: {response.get('status')}")
                return render(request, 'payment/payment_failed.html', {
                    'reason': 'rejected',
                    'message': 'Tu pago fue rechazado. Por favor verifica tus datos e intenta nuevamente.',
                    'status': response.get('status')
                })
                
        except Exception as e:
            print(f"Error en evaluate_payment: {e}")
            messages.error(request, "Ocurrió un error al procesar el pago.")
            return render(request, 'payment/payment_failed.html', {
                'reason': 'error',
                'message': 'Ocurrió un error técnico. Por favor intenta nuevamente o contacta con soporte.'
            })
    
    # Si no viene por GET, redirigir
    messages.error(request, "Acceso inválido.")
    return redirect('cart_summary')


def create_order_from_session(request):
    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    international_status = cart.get_international_status()
    total = cart.cart_total()

    # Obtener información de envío
    shipping = request.session.get('shipping_info')
    
    if not shipping:
        raise ValueError("No se encontró la información de envío en la sesión.")

    full_name = shipping.get('shipping_full_name', '')
    email = shipping.get('shipping_email', '')
    phone = shipping.get('shipping_phone', '')
    
    shipping_address = "\n".join(filter(None, [
        shipping.get('shipping_address1', ''),
        shipping.get('shipping_address2', ''),
        shipping.get('shipping_commune', ''),
        shipping.get('shipping_city', ''),
        shipping.get('shipping_state', ''),
        shipping.get('shipping_zipcode', ''),
        shipping.get('shipping_country', '')
    ]))
    
    amount_pay = total
    user = request.user if request.user.is_authenticated else None
    
    # Obtener workshop si existe
    workshop_id = request.session.get('workshop_id')
    workshop = None
    if workshop_id:
        try:
            workshop = Workshop.objects.get(id=workshop_id)
        except Workshop.DoesNotExist:
            pass

    # Verificar si hay productos internacionales
    has_international = any(international_status.values())

    # Crear la orden
    order = Order(
        user=user,
        full_name=full_name,
        email=email,
        phone=phone,
        shipping_address=shipping_address,
        amount_pay=amount_pay,
        workshop=workshop,
        has_international_items=has_international  # NUEVO
    )
    order.save()

    # Crear los ítems de la orden
    for product in cart_products:
        price = product.sale_price if product.is_sale else product.price
        quantity = quantities.get(str(product.id), 0)
        is_international = international_status.get(str(product.id), False)
        
        if quantity > 0:
            OrderItem.objects.create(
                order=order,
                product=product,
                user=user,
                quantity=quantity,
                price=price,
                is_international=is_international  # NUEVO
            )

    # Limpiar sesión y carrito
    request.session.pop('session_key', None)
    request.session.pop('shipping_info', None)
    request.session.pop('personal_info', None)
    request.session.pop('guest_info', None)
    request.session.pop('workshop_id', None)

    if user:
        current_user = Profile.objects.filter(user__id=request.user.id)
        current_user.update(old_cart="")

    for key in list(request.session.keys()):
        if key == 'session_key':
            del request.session[key]

    return order


# Deberia eliminarse esta función si se usa create_order_from_session
def process_order(request):
    if request.POST:
        # Get the cart
        cart = Cart(request)
        cart_products = cart.get_products()
        quantities = cart.get_quants()
        total = cart.cart_total()

        # Get the billing info from the last page
        # payment_form = PaymentForm(request.POST or None)

        # get shipping session data
        my_shipping = request.session.get('shipping_info')

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
                order_obj = Order.objects.filter(id=pk)
                now = datetime.datetime.now()
                order_obj.update(shipped=True, date_shipped=now)
                messages.success(request, "Orden marcada como enviada.")
                return redirect('shipped_dash')  # ✅ Redirige a enviadas
            else:
                order_obj = Order.objects.filter(id=pk)
                order_obj.update(shipped=False)
                messages.success(request, "Orden marcada como no enviada.")
                return redirect('not_shipped_dash')  # ✅ Redirige a pendientes

        return render(request, "payment/orders.html", {"order": order, "items": items})

    else:
        messages.success(request, "Access Denied.")
        return redirect('home')
    

def payment_success(request):
    return render(request, "payment/payment_success.html", {})

def payment_failed(request):
    return render(request, "payment/payment_failed.html", {})