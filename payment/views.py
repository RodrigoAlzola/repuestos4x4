import logging
from django.shortcuts import render, redirect, get_object_or_404
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress
from django.contrib import messages
from django.utils import timezone
from payment.models import Order, OrderItem, Coupon, CouponUsage
from django.contrib.auth.models import User
from store.models import Product, Profile
from store.forms import GuestUserForm, UserInfoForm
from workshop.models import Workshop
import datetime
import uuid
from store.emails import send_order_confirmation_email_async, send_pending_order_email_async, send_provider_order_notification_async
from django.http import JsonResponse

from transbank.webpay.webpay_plus.transaction import Transaction
from django.conf import settings
import os

from django.urls import reverse

# Crear el logger
logger = logging.getLogger(__name__)

env = os.getenv('DJANGO_SETTINGS_MODULE', '')


def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    
    # ===== CUPONES =====
    coupon_code = request.session.get('coupon_code')
    coupon_discount = request.session.get('coupon_discount', 0)
    
    # Calcular totales
    cart_total = float(cart.cart_total())
    total_after_discount = cart_total - coupon_discount
    
    # Validar cupón si existe
    coupon = None
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            user = request.user if request.user.is_authenticated else None
            can_use, message = coupon.can_use(user=user, amount=cart_total)
            
            if not can_use:
                # Cupón ya no es válido, removerlo
                del request.session['coupon_code']
                del request.session['coupon_discount']
                messages.warning(request, f'El cupón ya no es válido: {message}')
                coupon = None
                coupon_discount = 0
                total_after_discount = cart_total
        except Coupon.DoesNotExist:
            del request.session['coupon_code']
            del request.session['coupon_discount']
            coupon = None
            coupon_discount = 0
            total_after_discount = cart_total

    personal_info = None
    guest_user_form = None

    # Workshop data
    workshop_id = request.POST.get('workshop_id') or request.GET.get('workshop_id')
    shipping_form = None
    is_workshop_shipping = False

    # Limpiar datos previos de sesión en GET
    if request.method == 'GET':
        request.session.pop('guest_info', None)

    # ====== USUARIOS AUTENTICADOS ======
    if request.user.is_authenticated:
        # Obtener datos personales desde Profile
        try:
            profile = Profile.objects.get(user=request.user)
            personal_info = {
                'full_name': profile.full_name,
                'phone': profile.phone,
                'email': profile.email,
            }
        except Profile.DoesNotExist:
            personal_info = {
                'full_name': '',
                'phone': '',
                'email': '',
            }

        # Obtener todas las direcciones del usuario
        shipping_addresses = ShippingAddress.objects.filter(user=request.user).order_by('-is_default', '-created_at')
        has_addresses = shipping_addresses.exists()
        can_add_more = shipping_addresses.count() < 10

        # ====== FLUJO CON TALLER ======
        if workshop_id:
            try:
                selected_workshop = Workshop.objects.get(id=workshop_id)
                is_workshop_shipping = True

                shipping_data = {
                    'shipping_full_name': selected_workshop.name,
                    'shipping_phone': '',
                    'shipping_email': '',
                    'shipping_id_number': selected_workshop.id_number,
                    'shipping_address1': selected_workshop.address1,
                    'shipping_address2': selected_workshop.address2,
                    'shipping_city': selected_workshop.city,
                    'shipping_state': selected_workshop.state,
                    'shipping_commune': selected_workshop.commune,
                    'shipping_zipcode': selected_workshop.zipcode,
                    'shipping_country': selected_workshop.country,
                }
                shipping_form = ShippingForm(initial=shipping_data)

                if request.method == 'POST':
                    shipping_info = shipping_data
                    billing_form = PaymentForm()

                    request.session['personal_info'] = personal_info
                    request.session['shipping_info'] = shipping_info
                    request.session['workshop_id'] = workshop_id
                    
                    return render(request, "payment/billing_info.html", {
                        "cart_products": cart_products,
                        "quantities": quantities,
                        "total": total_after_discount,  # CAMBIO: usar total con descuento
                        "total_original": cart_total,  # NUEVO: total original
                        "coupon_discount": coupon_discount,  # NUEVO
                        "coupon": coupon,  # NUEVO
                        "shipping_info": shipping_info,
                        "personal_info": personal_info,
                        "billing_form": billing_form
                    })

            except Workshop.DoesNotExist:
                shipping_form = ShippingForm()

        # ====== FLUJO SIN TALLER (DIRECCIONES PERSONALES) ======
        else:
            is_workshop_shipping = False

            if request.method == 'POST':
                action = request.POST.get('action')

                # ====== SELECCIONAR DIRECCIÓN EXISTENTE ======
                if action == 'select_address':
                    address_id = request.POST.get('address_id')
                    
                    try:
                        selected_address = ShippingAddress.objects.get(id=address_id, user=request.user)
                        
                        shipping_info = {
                            'shipping_full_name': selected_address.full_name,
                            'shipping_phone': selected_address.phone,
                            'shipping_email': selected_address.email,
                            'shipping_id_number': selected_address.id_number,
                            'shipping_address1': selected_address.address1,
                            'shipping_address2': selected_address.address2 or '',
                            'shipping_city': selected_address.city,
                            'shipping_state': selected_address.region or '',
                            'shipping_commune': selected_address.commune or '',
                            'shipping_zipcode': selected_address.zipcode or '',
                            'shipping_country': selected_address.country,
                        }

                        billing_form = PaymentForm()
                        request.session['personal_info'] = personal_info
                        request.session['shipping_info'] = shipping_info
                        
                        return render(request, "payment/billing_info.html", {
                            "cart_products": cart_products,
                            "quantities": quantities,
                            "total": total_after_discount,  # CAMBIO
                            "total_original": cart_total,  # NUEVO
                            "coupon_discount": coupon_discount,  # NUEVO
                            "coupon": coupon,  # NUEVO
                            "shipping_info": shipping_info,
                            "personal_info": personal_info,
                            "billing_form": billing_form
                        })
                    
                    except ShippingAddress.DoesNotExist:
                        messages.error(request, "❌ Dirección no encontrada.")
                        return redirect('checkout')

                # ====== AGREGAR NUEVA DIRECCIÓN ======
                elif action == 'add_new_address':
                    if not can_add_more:
                        messages.error(request, "❌ Has alcanzado el límite de 10 direcciones.")
                        return redirect('checkout')
                    
                    shipping_form = ShippingForm(request.POST)
                    
                    if shipping_form.is_valid():
                        new_address = shipping_form.save(commit=False)
                        new_address.user = request.user
                        
                        # Si es la primera dirección, hacerla default
                        if not has_addresses:
                            new_address.is_default = True
                        
                        new_address.save()
                        messages.success(request, "✅ Nueva dirección agregada y seleccionada.")
                        
                        # Usar la nueva dirección recién creada
                        shipping_info = {
                            'shipping_full_name': new_address.full_name,
                            'shipping_phone': new_address.phone,
                            'shipping_email': new_address.email,
                            'shipping_id_number': new_address.id_number,
                            'shipping_address1': new_address.address1,
                            'shipping_address2': new_address.address2 or '',
                            'shipping_city': new_address.city,
                            'shipping_state': new_address.region or '',
                            'shipping_commune': new_address.commune or '',
                            'shipping_zipcode': new_address.zipcode or '',
                            'shipping_country': new_address.country,
                        }

                        billing_form = PaymentForm()
                        request.session['personal_info'] = personal_info
                        request.session['shipping_info'] = shipping_info
                        
                        return render(request, "payment/billing_info.html", {
                            "cart_products": cart_products,
                            "quantities": quantities,
                            "total": total_after_discount,  # CAMBIO
                            "total_original": cart_total,  # NUEVO
                            "coupon_discount": coupon_discount,  # NUEVO
                            "coupon": coupon,  # NUEVO
                            "shipping_info": shipping_info,
                            "personal_info": personal_info,
                            "billing_form": billing_form
                        })
                    else:
                        # Mostrar errores del formulario
                        for field, errors in shipping_form.errors.items():
                            for error in errors:
                                messages.error(request, f"❌ {field}: {error}")

            # GET request - mostrar formulario vacío para nueva dirección
            shipping_form = ShippingForm()

    # ====== FLUJO PARA INVITADOS ======
    else:
        workshop_id = False
        is_workshop_shipping = False
        shipping_addresses = []
        has_addresses = False
        can_add_more = False
        
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
                'shipping_id_number': guest_data['id_number'],
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
                "total": total_after_discount,  # CAMBIO
                "total_original": cart_total,  # NUEVO
                "coupon_discount": coupon_discount,  # NUEVO
                "coupon": coupon,  # NUEVO
                "shipping_info": shipping_info,
                "personal_info": personal_info,
                "billing_form": billing_form
            })

    # Renderizar página de checkout
    return render(request, "payment/checkout.html", {
        "cart_products": cart_products,
        "quantities": quantities,
        "total": cart_total,  # Total original
        "total_after_discount": total_after_discount,  # NUEVO: Total con descuento
        "coupon": coupon,  # NUEVO
        "coupon_discount": coupon_discount,  # NUEVO
        "shipping_form": shipping_form,
        "personal_info": personal_info,
        "is_workshop_shipping": is_workshop_shipping,
        "guest_user_form": guest_user_form,
        "workshop_id": workshop_id,
        "shipping_addresses": shipping_addresses if request.user.is_authenticated else [],
        "has_addresses": has_addresses if request.user.is_authenticated else False,
        "can_add_more": can_add_more if request.user.is_authenticated else False,
    })



def billing_info(request):
    """
    Vista unificada que:
    1. GET: Muestra el formulario de billing
    2. POST: Procesa el pago y redirige a Transbank
    """
    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    cart_total = cart.cart_total()

    # ===== OBTENER CUPÓN Y CALCULAR TOTAL CON DESCUENTO =====
    coupon_code = request.session.get('coupon_code')
    coupon_discount = request.session.get('coupon_discount', 0)
    
    # Total final que se pagará
    total = float(cart_total) - coupon_discount
    
    # Validar cupón si existe
    coupon = None
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            user = request.user if request.user.is_authenticated else None
            can_use, message = coupon.can_use(user=user, amount=cart_total)
            
            if not can_use:
                # Cupón ya no es válido
                del request.session['coupon_code']
                del request.session['coupon_discount']
                messages.warning(request, f'El cupón ya no es válido: {message}')
                coupon = None
                coupon_discount = 0
                total = cart_total
        except Coupon.DoesNotExist:
            del request.session['coupon_code']
            del request.session['coupon_discount']
            coupon = None
            coupon_discount = 0
            total = cart_total

    # Validar que hay información de envío en sesión
    shipping_info = request.session.get('shipping_info')
    personal_info = request.session.get('personal_info')

    if not shipping_info:
        messages.error(request, "No se encontró información de envío. Por favor completa el checkout primero.")
        return redirect('checkout')

    if request.method == 'POST':
        # ===== VALIDAR TÉRMINOS Y CONDICIONES =====
        terms_accepted = request.POST.get('terms_accepted')
        
        if not terms_accepted or terms_accepted != 'true':
            messages.error(request, "Debes aceptar los Términos y Condiciones para continuar.")
            return render(request, "payment/billing_info.html", {
                "cart_products": cart_products,
                "quantities": quantities,
                "total": total,
                "total_original": cart_total,
                "coupon": coupon,
                "coupon_discount": coupon_discount,
                "shipping_info": shipping_info,
                "personal_info": personal_info,
            })


        # ===== OBTENER MÉTODO DE PAGO =====
        payment_method = request.POST.get('payment_method', 'transbank')
        
        # ===== FLUJO: TRANSBANK =====
        if payment_method == 'transbank':
        
            # Generar un buy_order único
            timestamp = datetime.datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4())[:8].upper()
            buy_order = f"{timestamp}-{unique_id}"
        
            try:
                env = os.getenv('DJANGO_SETTINGS_MODULE', '')
                
                # Desarrollo
                if 'dev' in env:
                    tx = Transaction.build_for_integration(
                        settings.TRANSBANK_COMMERCE_CODE,
                        settings.TRANSBANK_API_KEY
                    )
                # Producción
                elif 'prod' in env:
                    tx = Transaction.build_for_production(
                        settings.TRANSBANK_COMMERCE_CODE,
                        settings.TRANSBANK_API_KEY
                    )
            
                # CAMBIO: Usar el total con descuento
                response = tx.create(
                    buy_order=buy_order,
                    session_id=request.session.session_key,
                    amount=int(total),  # ← AQUÍ: Usar total con descuento
                    return_url=request.build_absolute_uri(reverse('evaluate_payment'))
                )

                # Guardar en sesión para crear la orden DESPUÉS del pago
                request.session['pending_buy_order'] = buy_order
                request.session['pending_payment'] = True

                # Redirigir a Transbank
                token = response['token']
                url = response['url']
                
                return redirect(f"{url}?token_ws={token}")

            except Exception as e:
                print(f"Error creando transacción Transbank: {e}")
                import traceback
                traceback.print_exc()
                
                messages.error(request, "Error al iniciar el pago con Transbank. Intenta nuevamente.")
                return render(request, "payment/billing_info.html", {
                    "cart_products": cart_products,
                    "quantities": quantities,
                    "total": total,
                    "total_original": cart_total,
                    "coupon": coupon,
                    "coupon_discount": coupon_discount,
                    "shipping_info": shipping_info,
                    "personal_info": personal_info,
                })
        
        # ===== FLUJO: TRANSFERENCIA BANCARIA =====
        elif payment_method == 'bank_transfer':
            # Crear la orden directamente con estado pending
            try:
                # Preparar dirección de envío
                if shipping_info.get('shipping_to_workshop') == 'True':
                    workshop_id = shipping_info.get('shipping_workshop')
                    workshop = Workshop.objects.get(id=workshop_id) if workshop_id else None
                    shipping_address = f"Taller: {workshop.name if workshop else 'No especificado'}"
                else:
                    workshop = None
                    shipping_address = f"{shipping_info['shipping_address1']}\n"
                    if shipping_info.get('shipping_address2'):
                        shipping_address += f"{shipping_info['shipping_address2']}\n"
                    shipping_address += f"{shipping_info['shipping_commune']}, {shipping_info['shipping_city']}\n"
                    if shipping_info.get('shipping_state'):
                        shipping_address += f"{shipping_info['shipping_state']}\n"
                    if shipping_info.get('shipping_zipcode'):
                        shipping_address += f"CP: {shipping_info['shipping_zipcode']}\n"
                    shipping_address += f"{shipping_info['shipping_country']}"

                # Crear la orden
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    full_name=personal_info['full_name'],
                    email=personal_info['email'],
                    phone=personal_info['phone'],
                    id_number=shipping_info['shipping_id_number'],
                    shipping_address=shipping_address,
                    workshop=workshop,
                    amount_pay=total,
                    payment_method='bank_transfer',
                    order_status='pending',  # Estado pendiente
                    # Cupón
                    coupon=coupon,
                    coupon_discount=coupon_discount,
                    amount_before_discount=cart_total if coupon else total,
                )

                # Crear los items de la orden
                has_international = False
                for product in cart_products:
                    quantity = quantities.get(str(product.id), 0)
                    
                    # Determinar precio
                    if product.is_sale:
                        price = product.sale_price
                    else:
                        price = product.price
                    
                    # Verificar si es internacional
                    is_international = getattr(product, 'is_international', False)
                    if is_international:
                        has_international = True
                    
                    # Crear OrderItem
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        user=request.user if request.user.is_authenticated else None,
                        quantity=quantity,
                        price=price,
                        is_international=is_international,
                    )

                # Actualizar flag de items internacionales
                if has_international:
                    order.has_international_items = True
                    order.save()

                # Marcar cupón como usado
                if coupon:
                    coupon.use_coupon(user=request.user if request.user.is_authenticated else None)

                # Limpiar carrito y sesión
                clear_cart_and_session(request)

                # Limpiar también información de cupón
                for key in ['coupon_code', 'coupon_discount']:
                    if key in request.session:
                        del request.session[key]

                # Después de crear la orden y antes del redirect
                send_pending_order_email_async(order)

                # Redirigir a página de confirmación
                return redirect('order_pending', order_id=order.id)

            except Exception as e:
                print(f"Error creando orden con transferencia bancaria: {e}")
                import traceback
                traceback.print_exc()
                
                messages.error(request, "Error al crear el pedido. Por favor intenta nuevamente.")
                return render(request, "payment/billing_info.html", {
                    "cart_products": cart_products,
                    "quantities": quantities,
                    "total": total,
                    "total_original": cart_total,
                    "coupon": coupon,
                    "coupon_discount": coupon_discount,
                    "shipping_info": shipping_info,
                    "personal_info": personal_info,
                })
        
        else:
            messages.error(request, "Método de pago no válido.")
            return redirect('billing_info')

    else:
        # ===== GET REQUEST - MOSTRAR FORMULARIO =====
        return render(request, "payment/billing_info.html", {
            "cart_products": cart_products,
            "quantities": quantities,
            "total": total,
            "total_original": cart_total,
            "coupon": coupon,
            "coupon_discount": coupon_discount,
            "shipping_info": shipping_info,
            "personal_info": personal_info,
        })


def evaluate_payment(request):
    if request.GET:
        # Verificar si es una cancelación/anulación
        tbk_token = request.GET.get('TBK_TOKEN')
        tbk_orden_compra = request.GET.get('TBK_ORDEN_COMPRA')
        tbk_id_sesion = request.GET.get('TBK_ID_SESION')
        
        if tbk_token or tbk_orden_compra or tbk_id_sesion:
            # Usuario canceló - NO hay orden creada aún, solo limpiar sesión
            request.session.pop('pending_buy_order', None)
            request.session.pop('pending_payment', None)
            
            # NO LIMPIAR EL CARRITO - mantener los productos
            messages.warning(request, "Cancelaste el pago. Tus productos siguen en el carrito.")
            return render(request, 'payment/payment_failed.html', {
                'reason': 'cancelled',
                'message': 'Cancelaste el pago en Transbank. Tus productos siguen en el carrito y puedes intentar nuevamente.',
                'show_cart_button': True
            })
        
        # Flujo normal - pago exitoso o rechazado
        token = request.GET.get('token_ws')
        
        if not token:
            messages.error(request, "No se recibió el token de Transbank.")
            return redirect('cart_summary')

        try:
            env = os.getenv('DJANGO_SETTINGS_MODULE', '')
            
            # Desarrollo
            if 'dev' in env:
                tx = Transaction.build_for_integration(
                    settings.TRANSBANK_COMMERCE_CODE,
                    settings.TRANSBANK_API_KEY
                )
            # Producción
            elif 'prod' in env:
                tx = Transaction.build_for_production(
                    settings.TRANSBANK_COMMERCE_CODE,
                    settings.TRANSBANK_API_KEY
                )

            response = tx.commit(token)

            if response['status'] == 'AUTHORIZED':
                # ✅ PAGO EXITOSO - AHORA SÍ CREAR LA ORDEN
                
                # Verificar que tenemos el buy_order pendiente
                pending_buy_order = request.session.get('pending_buy_order')
                if not pending_buy_order:
                    raise ValueError("No se encontró información de la orden pendiente")
                
                # CREAR LA ORDEN AHORA
                order = create_order_from_session(request)
                order.buy_order = pending_buy_order
                order.session_id = request.session.session_key
                order.payment_method='transbank',
                order.order_status='paid',
                order.paid = True
                order.payment_status = 'APPROVED'
                order.save()
                
                # Actualizar orden con datos de Transbank
                update_order_with_transaction(order, response)
                
                order_items = order.orderitem_set.all()
                
                # Limpiar sesión y carrito
                request.session.pop('pending_buy_order', None)
                request.session.pop('pending_payment', None)
                clear_cart_and_session(request)
                
                # Enviar email de confirmación
                try:
                    send_order_confirmation_email_async(order)
                except Exception as e:
                    print(f"Error enviando email de confirmación: {e}")

                # Enviar email a proveedores
                try:
                    send_provider_order_notification_async(order)
                except Exception as e:
                    print(f"Error enviando emails a proveedores: {e}")
                
                # Preparar datos para el template
                transaction_data = {
                    'order_number': order.id,
                    'buy_order': response.get('buy_order'),
                    'commerce_code': settings.TRANSBANK_COMMERCE_CODE,
                    'amount': response.get('amount'),
                    'authorization_code': response.get('authorization_code'),
                    'transaction_date': response.get('transaction_date'),
                    'payment_type': order.get_payment_type_display(),
                    'payment_type_code': response.get('payment_type_code'),
                    'installments': response.get('installments_number', 0),
                    'card_number': response.get('card_detail', {}).get('card_number', 'N/A'),
                    'status': response.get('status'),
                }
                
                return render(request, "payment/payment_success.html", {
                    'order': order,
                    'order_items': order_items,
                    'transaction': transaction_data,
                })
            else:
                # ❌ PAGO RECHAZADO - No hay orden creada, solo limpiar sesión
                request.session.pop('pending_buy_order', None)
                request.session.pop('pending_payment', None)
                
                # NO LIMPIAR EL CARRITO - mantener los productos
                messages.error(request, "Tu pago fue rechazado. Tus productos siguen en el carrito.")
                return render(request, 'payment/payment_failed.html', {
                    'reason': 'rejected',
                    'message': 'Tu pago fue rechazado por el banco. Por favor verifica tus datos e intenta nuevamente. Tus productos siguen en el carrito.',
                    'status': response.get('status'),
                    'show_cart_button': True
                })
                
        except Exception as e:
            print(f"Error en evaluate_payment: {e}")
            import traceback
            traceback.print_exc()
            
            # Limpiar sesión pendiente (no hay orden que eliminar)
            request.session.pop('pending_buy_order', None)
            request.session.pop('pending_payment', None)
            
            # NO LIMPIAR EL CARRITO - mantener los productos
            return render(request, 'payment/payment_failed.html', {
                'reason': 'error',
                'message': 'Ocurrió un error técnico al procesar tu pago. Tus productos siguen en el carrito. Por favor intenta nuevamente o contacta con soporte.',
                'show_cart_button': True
            })
    
    messages.error(request, "Acceso inválido.")
    return redirect('cart_summary')


def update_order_with_transaction(order, transaction_response):
    """Actualiza la orden con los datos de la transacción de Transbank"""
    
    # Procesar fecha de transacción
    transaction_date_str = transaction_response.get('transaction_date')
    if transaction_date_str:
        try:
            transaction_date = datetime.datetime.strptime(transaction_date_str[:19], '%Y-%m-%dT%H:%M:%S')
            order.transaction_date = timezone.make_aware(transaction_date)
        except:
            order.transaction_date = timezone.now()
    
    order.authorization_code = transaction_response.get('authorization_code')
    order.payment_type_code = transaction_response.get('payment_type_code')
    order.installments_number = transaction_response.get('installments_number', 0)
    
    # Obtener últimos 4 dígitos de la tarjeta
    card_detail = transaction_response.get('card_detail', {})
    order.card_number = card_detail.get('card_number', 'N/A')
    
    order.commerce_code = transaction_response.get('commerce_code') or settings.TRANSBANK_COMMERCE_CODE
    order.accounting_date = transaction_response.get('accounting_date')
    order.transaction_status = transaction_response.get('status')
    
    order.save()


def clear_cart_and_session(request):
    """
    Limpia el carrito y la sesión después de un pago exitoso
    """
    # Limpiar sesión
    request.session.pop('session_key', None)
    request.session.pop('shipping_info', None)
    request.session.pop('personal_info', None)
    request.session.pop('guest_info', None)
    request.session.pop('workshop_id', None)
    request.session.pop('buy_order', None)
    request.session.pop('order_id', None)

    # Limpiar carrito del usuario autenticado
    if request.user.is_authenticated:
        current_user = Profile.objects.filter(user__id=request.user.id)
        current_user.update(old_cart="")

    # Limpiar session_key del carrito
    for key in list(request.session.keys()):
        if key == 'session_key':
            del request.session[key]


def create_order_from_session(request, transaction_response=None):

    cart = Cart(request)
    cart_products = cart.get_products()
    quantities = cart.get_quants()
    international_status = cart.get_international_status()
    cart_total = cart.cart_total()

    # ===== OBTENER CUPÓN DE LA SESIÓN =====
    coupon_code = request.session.get('coupon_code')
    coupon_discount = request.session.get('coupon_discount', 0)
    coupon = None
    
    # Calcular el total final con descuento
    amount_pay = float(cart_total) - coupon_discount

    # Obtener información de envío
    shipping = request.session.get('shipping_info')
    
    if not shipping:
        raise ValueError("No se encontró la información de envío en la sesión.")

    full_name = shipping.get('shipping_full_name', '')
    email = shipping.get('shipping_email', '')
    phone = shipping.get('shipping_phone', '')
    id_number = shipping.get('shipping_id_number', '')
    shipping_address = "\n".join(filter(None, [
        shipping.get('shipping_address1', ''),
        shipping.get('shipping_address2', ''),
        shipping.get('shipping_commune', ''),
        shipping.get('shipping_city', ''),
        shipping.get('shipping_state', ''),
        shipping.get('shipping_zipcode', ''),
        shipping.get('shipping_country', '')
    ]))
    
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

    # ===== VALIDAR Y OBTENER CUPÓN =====
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            # Verificar que el cupón sigue siendo válido
            can_use, message = coupon.can_use(user=user, amount=cart_total)
            if not can_use:
                # Si el cupón ya no es válido, no aplicar descuento
                coupon = None
                coupon_discount = 0
                amount_pay = cart_total
        except Coupon.DoesNotExist:
            coupon = None
            coupon_discount = 0
            amount_pay = cart_total

    # Crear la orden (buy_order se genera automáticamente)
    order = Order(
        user=user,
        full_name=full_name,
        email=email,
        phone=phone,
        id_number=id_number,
        shipping_address=shipping_address,
        amount_before_discount=cart_total,  # NUEVO: Total antes de descuento
        coupon=coupon,  # NUEVO: Cupón aplicado
        coupon_discount=coupon_discount,  # NUEVO: Monto del descuento
        amount_pay=amount_pay,  # Total final con descuento
        workshop=workshop,
        has_international_items=has_international
    )
    
    # Guardar - esto generará automáticamente el buy_order
    order.save()

    # ===== REGISTRAR USO DEL CUPÓN =====
    if coupon:
        try:
            # Crear registro de uso
            CouponUsage.objects.create(
                coupon=coupon,
                user=user,
                order=order
            )
            
            # Incrementar contador de usos
            coupon.times_used += 1
            coupon.save()
            
            # Limpiar cupón de la sesión
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
            if 'coupon_discount' in request.session:
                del request.session['coupon_discount']
                
        except Exception as e:
            # Log del error pero no fallar la orden
            print(f"Error al registrar uso del cupón: {e}")

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
                is_international=is_international
            )
    
    return order


def confirmed_orders_dash(request):
    """Dashboard para órdenes confirmadas (pagadas) pero no enviadas"""
    if request.user.is_authenticated and request.user.is_superuser:
        # Filtrar órdenes pagadas pero no enviadas
        orders = Order.objects.filter(
            order_status='paid',
            shipped=False
        ).order_by('-date_order')
        
        if request.POST:
            action = request.POST.get('action')
            order_id = request.POST.get('order_id')
            
            try:
                order = Order.objects.get(id=order_id)
                
                if action == 'mark_shipped':
                    # Marcar como enviada
                    now = datetime.datetime.now()
                    order.shipped = True
                    order.date_shipped = now
                    order.save()
                    
                    messages.success(request, f"✅ Orden #{order.buy_order} marcada como enviada.")
                    return redirect('confirmed_orders_dash')
                    
            except Order.DoesNotExist:
                messages.error(request, "❌ La orden no existe.")
                return redirect('confirmed_orders_dash')
            except Exception as e:
                logger.error(f"[CONFIRMED DASH] Error procesando orden: {e}")
                messages.error(request, f"❌ Error procesando la orden: {str(e)}")
                return redirect('confirmed_orders_dash')

        return render(request, "payment/confirmed_orders_dash.html", {'orders': orders})
    else:
        messages.error(request, "⛔ Acceso Denegado.")
        return redirect('home')


def shipped_orders_dash(request):
    """Dashboard para órdenes que ya fueron enviadas"""
    if request.user.is_authenticated and request.user.is_superuser:
        # Filtrar órdenes enviadas
        orders = Order.objects.filter(shipped=True).order_by('-date_shipped')
        
        if request.POST:
            action = request.POST.get('action')
            order_id = request.POST.get('order_id')
            
            try:
                order = Order.objects.get(id=order_id)
                
                if action == 'mark_unshipped':
                    # Marcar como no enviada
                    order.shipped = False
                    order.date_shipped = None
                    order.save()
                    
                    messages.success(request, f"✅ Orden #{order.buy_order} marcada como no enviada.")
                    return redirect('shipped_orders_dash')
                    
            except Order.DoesNotExist:
                messages.error(request, "❌ La orden no existe.")
                return redirect('shipped_orders_dash')
            except Exception as e:
                logger.error(f"[SHIPPED DASH] Error procesando orden: {e}")
                messages.error(request, f"❌ Error procesando la orden: {str(e)}")
                return redirect('shipped_orders_dash')

        return render(request, "payment/shipped_orders_dash.html", {'orders': orders})
    else:
        messages.error(request, "⛔ Acceso Denegado.")
        return redirect('home')
    
    
def pending_orders_dash(request):
    """Dashboard para órdenes pendientes de pago (transferencia bancaria)"""
    if request.user.is_authenticated and request.user.is_superuser:
        # Filtrar órdenes con pago pendiente
        orders = Order.objects.filter(
            payment_method='bank_transfer',
            order_status='pending'
        ).order_by('-date_order')
        
        if request.POST:
            action = request.POST.get('action')
            order_id = request.POST.get('order_id')
            
            try:
                order = Order.objects.get(id=order_id)
                
                if action == 'confirm_payment':
                    # Cambiar estado a pagado
                    order.order_status = 'paid'
                    order.save()
                    
                    # Enviar email de confirmación al cliente
                    try:
                        send_order_confirmation_email_async(order)
                        logger.info(f"[PENDING DASH] Email de confirmación enviado al cliente para orden #{order.id}")
                    except Exception as e:
                        logger.error(f"[PENDING DASH] Error enviando email al cliente: {e}")
                    
                    # Enviar emails a proveedores
                    try:
                        send_provider_order_notification_async(order)
                        logger.info(f"[PENDING DASH] Emails a proveedores iniciados para orden #{order.id}")
                    except Exception as e:
                        logger.error(f"[PENDING DASH] Error enviando emails a proveedores: {e}")
                    
                    messages.success(request, f"✅ Orden #{order.buy_order} confirmada. Emails enviados al cliente y proveedores.")
                    return redirect('pending_orders_dash')
                
                elif action == 'cancel_order':
                    # Cancelar orden
                    order.order_status = 'cancelled'
                    order.save()
                    
                    messages.warning(request, f"❌ Orden #{order.buy_order} cancelada.")
                    return redirect('pending_orders_dash')
                
            except Order.DoesNotExist:
                messages.error(request, "❌ La orden no existe.")
                return redirect('pending_orders_dash')
            except Exception as e:
                logger.error(f"[PENDING DASH] Error procesando orden: {e}")
                messages.error(request, f"❌ Error procesando la orden: {str(e)}")
                return redirect('pending_orders_dash')

        return render(request, "payment/pending_orders_dash.html", {'orders': orders})
    else:
        messages.error(request, "⛔ Acceso Denegado.")
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
                return redirect('shipped_orders_dash')  # ✅ Redirige a enviadas
            else:
                order_obj = Order.objects.filter(id=pk)
                order_obj.update(shipped=False)
                messages.success(request, "Orden marcada como no enviada.")
                return redirect('confirmed_orders_dash')  # ✅ Redirige a pendientes

        return render(request, "payment/orders.html", {"order": order, "items": items})

    else:
        messages.success(request, "Access Denied.")
        return redirect('home')
    

def payment_success(request):
    return render(request, "payment/payment_success.html", {})


def payment_failed(request):
    return render(request, "payment/payment_failed.html", {})


def validate_coupon(request):
    """Vista AJAX para validar cupones"""
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        
        if not code:
            return JsonResponse({'valid': False, 'message': 'Ingresa un código de cupón'})
        
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return JsonResponse({'valid': False, 'message': 'Cupón inválido'})
        
        # Obtener monto del carrito
        from cart.cart import Cart
        cart = Cart(request)
        cart_total = float(cart.cart_total())
        
        # Verificar si puede usar el cupón
        user = request.user if request.user.is_authenticated else None
        can_use, message = coupon.can_use(user=user, amount=cart_total)
        
        if not can_use:
            return JsonResponse({'valid': False, 'message': message})
        
        # Calcular descuento
        discount_amount = float(coupon.calculate_discount(cart_total))
        new_total = cart_total - discount_amount
        
        # Guardar en sesión
        request.session['coupon_code'] = code
        request.session['coupon_discount'] = float(discount_amount)
        
        return JsonResponse({
            'valid': True,
            'message': f'¡Cupón aplicado! Descuento: ${discount_amount:,.0f}',
            'discount_amount': float(discount_amount),
            'new_total': float(new_total),
            'original_total': cart_total
        })
    
    return JsonResponse({'valid': False, 'message': 'Método no permitido'})


def remove_coupon(request):
    """Remover cupón de la sesión"""
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
    if 'coupon_discount' in request.session:
        del request.session['coupon_discount']
    
    return JsonResponse({'success': True, 'message': 'Cupón removido'})


def order_pending(request, order_id):
    """
    Vista para mostrar un pedido pendiente (transferencia bancaria)
    """
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    
    return render(request, 'payment/order_pending.html', context)