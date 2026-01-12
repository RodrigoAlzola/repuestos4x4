from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Profile, Compatibility
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django.contrib.auth import get_user_model
from django import forms 
from django.db.models import Q, Count
import json
from cart.cart import Cart
from django.views.decorators.cache import never_cache
from store.emails import send_registration_email_async
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


# Create your views here.
def home(request):
    # products = Product.objects.all()
    batteries = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0), category__name__iexact='BATTERIES').order_by('?')[:4]
    rear_axle = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0), category__name__iexact='REAR AXLE').order_by('?')[:4]
    engine = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0), category__name__iexact='ENGINE').order_by('?')[:4]

    # Obtener todas las categorías
    categories = Category.objects.annotate(product_count=Count('product')).filter(product_count__gt=0).order_by('name')

    # Ruta relativa dentro de MEDIA
    header_image = 'media/marketing/IMG-home.png'  

    return render(request, 'home.html', {
        'batteries': batteries,
        'rear_axle': rear_axle,
        'engine': engine,
        'categories': categories,
        'header_image': header_image,
    })


def about(request):
    return render(request, 'about.html', {})


def login_user(request):
    if request.method == 'POST':
        username_or_email = request.POST['username']
        password = request.POST['password']
        
        # Intentar autenticar con username primero
        user = authenticate(request, username=username_or_email, password=password)
        
        # Si falla, intentar con email
        if user is None:
            User = get_user_model()
            try:
                # Buscar usuario por email
                user_obj = User.objects.get(email=username_or_email)
                # Autenticar con el username encontrado
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            login(request, user)
            
            # Recuperar carrito guardado
            try:
                profile = Profile.objects.get(user=user)
                saved_cart = profile.old_cart
                
                if saved_cart:
                    # Intentar convertir el JSON
                    try:
                        converted_cart = json.loads(saved_cart)
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        print(f"Error decodificando carrito: {e}")
                        print(f"Carrito corrupto: {saved_cart}")
                        converted_cart = {}
                        # Limpiar el carrito corrupto
                        profile.old_cart = ''
                        profile.save()
                    
                    # Restaurar carrito en sesión
                    cart = Cart(request)
                    for key, value in converted_cart.items():
                        cart.db_add(product=key, quantity=value)
                else:
                    converted_cart = {}
                    
            except Profile.DoesNotExist:
                # Si no existe profile, crear uno
                Profile.objects.create(user=user)
            
            messages.success(request, "Has iniciado sesión correctamente")
            return redirect('home')
        else:
            messages.error(request, "Error al iniciar sesión. Verifica tus credenciales.")
            return redirect('login')
    else:
        return render(request, 'login.html', {})


def logout_user(request):
    logout(request)
    messages.success(request, ('You have been logged out...'))
    return redirect('home')


def register_user(request):
    form = SignUpForm()
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Verificar si el email ya existe
            if User.objects.filter(email=email).exists() or Profile.objects.filter(email=email).exists():
                messages.error(request, 'Este correo electrónico ya está registrado. Por favor usa otro.')
                return redirect('register')
            
            # Guardar el usuario
            user = form.save()
            
            # Crear o actualizar el Profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.full_name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}"
            profile.phone = form.cleaned_data['phone']
            profile.email = email
            profile.save()
            
            # Enviar email de bienvenida en background (NO BLOQUEA)
            send_registration_email_async(email, profile.full_name)
            
            messages.success(request, 'Cuenta creada exitosamente! Por favor completa tu información de envío.')
            
            # Log in user
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            
            return redirect('update_info')
        else:
            messages.error(request, 'Hubo un error en el registro. Por favor verifica los datos.')
            return redirect('register')
    else:
        return render(request, 'register.html', {'form': form})
    

def update_user(request):
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        user_form = UpdateUserForm(request.POST or None, instance=current_user)

        if user_form.is_valid():
            user_form.save()

            login(request, current_user)
            messages.success(request, "User has been Updated.")
            return redirect('home')
        return render(request, 'update_user.html', {'user_form': user_form})
    else:
        messages.success(request, "You must been Logged in to access the Update page.")
        return redirect('home')


def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user
        
        if request.method == 'POST':
            form = ChangePasswordForm(current_user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your Password has been Updated.")
                login(request, current_user)
                return redirect('login')
            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)
                return redirect('update_password')
        else:
            form = ChangePasswordForm(current_user)
            return render(request, "update_password.html", {'form': form})
        
    else:
        messages.success(request, "You must been Logged in to access that page.")
        return redirect('home')

@login_required
def update_info(request):
    # Obtener o crear Profile
    current_user, created = Profile.objects.get_or_create(user=request.user)
    
    # Obtener todas las direcciones del usuario
    shipping_addresses = ShippingAddress.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    # Verificar si tiene direcciones
    has_addresses = shipping_addresses.exists()
    
    # Límite de direcciones
    MAX_ADDRESSES = 10
    can_add_more = shipping_addresses.count() < MAX_ADDRESSES
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'shipping_new':
            # Agregar nueva dirección de envío
            if not can_add_more:
                messages.error(request, f"❌ Has alcanzado el límite de {MAX_ADDRESSES} direcciones.")
                return redirect('update_info')
            
            shipping_form = ShippingForm(request.POST)
            if shipping_form.is_valid():
                new_address = shipping_form.save(commit=False)
                new_address.user = request.user
                
                # Si es la primera dirección, hacerla default
                if not has_addresses:
                    new_address.is_default = True
                
                new_address.save()
                messages.success(request, "✅ Nueva dirección agregada correctamente.")
                return redirect('update_info')
            else:
                # DEBUG: Mostrar errores específicos
                error_messages = []
                for field, errors in shipping_form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                
                error_text = " | ".join(error_messages)
                messages.error(request, f"❌ Errores: {error_text}")
                
                # También imprimir en consola para debugging
                print("ERRORES DEL FORMULARIO:")
                print(shipping_form.errors)
                print("DATOS POST:")
                print(request.POST)
        
        elif form_type == 'shipping_edit':
            # Editar dirección existente
            address_id = request.POST.get('address_id')
            shipping_address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
            
            shipping_form = ShippingForm(request.POST, instance=shipping_address)
            if shipping_form.is_valid():
                shipping_form.save()
                messages.success(request, "✅ Dirección actualizada correctamente.")
                return redirect('update_info')
            else:
                messages.error(request, "❌ Error al actualizar la dirección.")
    
    # GET request
    # Formulario para nueva dirección
    # Solo pre-llenar si es la PRIMERA dirección
    if not has_addresses:
        # Primera dirección: pre-llenar con datos del usuario
        shipping_form_new = ShippingForm(initial={
            'full_name': current_user.full_name or request.user.get_full_name(),
            'email': current_user.email or request.user.email,
            'phone': current_user.phone,
        })
    else:
        # Direcciones adicionales: formulario vacío
        shipping_form_new = ShippingForm()
    
    return render(request, 'update_info.html', {
        'profile': current_user,  # Para mostrar info estática
        'shipping_form_new': shipping_form_new,
        'shipping_addresses': shipping_addresses,
        'has_addresses': has_addresses,
        'can_add_more': can_add_more,
        'max_addresses': MAX_ADDRESSES,
        'addresses_count': shipping_addresses.count(),
    })


@login_required
def delete_shipping_address(request, address_id):
    """Eliminar dirección de envío (excepto la default)"""
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    
    # No permitir eliminar la dirección default
    if address.is_default:
        messages.error(request, "❌ No puedes eliminar tu dirección principal. Marca otra como principal primero.")
        return redirect('update_info')
    
    address.delete()
    messages.success(request, "✅ Dirección eliminada correctamente.")
    return redirect('update_info')


@login_required
def set_default_address(request, address_id):
    """Marcar una dirección como predeterminada"""
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    
    # Desmarcar todas las demás
    ShippingAddress.objects.filter(user=request.user).update(is_default=False)
    
    # Marcar esta como default
    address.is_default = True
    address.save()
    
    messages.success(request, "✅ Dirección principal actualizada.")
    return redirect('update_info')


@login_required
def edit_shipping_address(request, address_id):
    """Editar dirección de envío"""
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    
    if request.method == 'POST':
        form = ShippingForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Dirección actualizada correctamente.")
            return redirect('update_info')
    else:
        form = ShippingForm(instance=address)
    
    return render(request, 'edit_shipping_address.html', {
        'form': form,
        'address': address
    })
    

def product(request, pk):
    product = Product.objects.get(id=pk)

    # Agrupar compatibilidades
    compat_data = {}
    for comp in product.compatibilities.all():
        brand = comp.brand.strip()
        model = comp.model.strip()
        serie = comp.serie.strip()
        compat_data.setdefault(brand, {}).setdefault(model, []).append(serie)

    # Capturar filtros seleccionados desde GET
    selected_brand = request.GET.get('brand', '')
    selected_model = request.GET.get('model', '')
    selected_serie = request.GET.get('serie', '')

    # Determinar rango de cantidad según tipo de stock
    quantity_range = None
    quantity_range_international = None
    
    if product.stock > 0:
        quantity_range = range(1, min(product.stock + 1, 11))  # Máximo 10 o el stock disponible
    elif product.stock_international > 0:
        quantity_range_international = range(1, min(product.stock_international + 1, 11))

    return render(request, 'product.html', {
        'product': product,
        'compat_data': compat_data,
        'quantity_range': quantity_range,
        'quantity_range_international': quantity_range_international,
        'selected_brand': selected_brand,
        'selected_model': selected_model,
        'selected_serie': selected_serie,
    })


def category(request, foo):
    foo = foo.replace('-', ' ')

    try:
        category = Category.objects.get(name=foo)
        products = Product.objects.filter(category=category)
        return render(request, 'category.html', {'products': products, 'category': category})

    except:
        messages.success(request, ("That  Category doesn't exist."))
        return redirect('home')

@never_cache
def all_products(request):
    # Filtros desde GET
    selected_category = request.GET.get('category')
    selected_subcategory = request.GET.get('subcategory')
    selected_brand = request.GET.get('brand')
    selected_model = request.GET.get('model')
    selected_serie = request.GET.get('serie')
    selected_stock_type = request.GET.get('stock_type')
    search_query = request.GET.get('search', '')

    # Base de productos con stock
    products = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0))

    # Aplicar búsqueda
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query)
        )

    # NUEVO: Filtro de tipo de stock
    if selected_stock_type == 'nacional':
        products = products.filter(stock__gt=0)
    elif selected_stock_type == 'internacional':
        products = products.filter(stock_international__gt=0, stock=0)

    # Aplicar filtros
    if selected_category:
        products = products.filter(category__name=selected_category)

    if selected_subcategory:
        products = products.filter(subcategory=selected_subcategory)

    if selected_brand:
        products = products.filter(compatibilities__brand=selected_brand)

    if selected_model:
        products = products.filter(compatibilities__model=selected_model)

    if selected_serie:
        products = products.filter(compatibilities__serie=selected_serie)

    products = products.distinct().order_by('name')

    # Paginación
    paginator = Paginator(products, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ===== FILTROS DINÁMICOS BIDIRECCIONALES =====
    
    # 1. CATEGORÍAS DINÁMICAS (filtradas por compatibilidad)
    if selected_brand or selected_model or selected_serie:
        # Obtener productos que coinciden con la compatibilidad seleccionada
        filtered_products = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0))
        
        if selected_brand:
            filtered_products = filtered_products.filter(compatibilities__brand=selected_brand)
        if selected_model:
            filtered_products = filtered_products.filter(compatibilities__model=selected_model)
        if selected_serie:
            filtered_products = filtered_products.filter(compatibilities__serie=selected_serie)
        
        # Obtener solo las categorías de esos productos
        category_ids = filtered_products.values_list('category_id', flat=True).distinct()
        categories = Category.objects.filter(id__in=category_ids).order_by('name')
    else:
        categories = Category.objects.exclude(name__in=['BRAKE GR SPORT & ROGUE', 'WHEEL']).order_by('name')

    # 2. SUBCATEGORÍAS DINÁMICAS
    subcategories_query = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0))
    
    if selected_category:
        subcategories_query = subcategories_query.filter(category__name=selected_category)
    
    if selected_brand:
        subcategories_query = subcategories_query.filter(compatibilities__brand=selected_brand)
    if selected_model:
        subcategories_query = subcategories_query.filter(compatibilities__model=selected_model)
    if selected_serie:
        subcategories_query = subcategories_query.filter(compatibilities__serie=selected_serie)
    
    subcategories = (
        subcategories_query
        .exclude(subcategory__isnull=True)
        .exclude(subcategory='')
        .values_list('subcategory', flat=True)
        .distinct()
        .order_by('subcategory')
    )

    # 3. COMPATIBILIDADES DINÁMICAS (filtradas por categoría)
    if selected_category or selected_subcategory:
        # Obtener productos que coinciden con la categoría seleccionada
        filtered_products = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0))
        
        if selected_category:
            filtered_products = filtered_products.filter(category__name=selected_category)
        if selected_subcategory:
            filtered_products = filtered_products.filter(subcategory=selected_subcategory)
        
        # Obtener solo las compatibilidades de esos productos
        compat_ids = filtered_products.values_list('compatibilities__id', flat=True).distinct()
        unique_compatibilities = (
            Compatibility.objects
            .filter(id__in=compat_ids)
            .values('brand', 'model', 'serie')
            .distinct()
            .order_by('brand', 'model', 'serie')
        )
    else:
        unique_compatibilities = (
            Compatibility.objects
            .values('brand', 'model', 'serie')
            .distinct()
            .order_by('brand', 'model', 'serie')
        )

    # Construir compat_data
    compat_data = {}
    for comp in unique_compatibilities:
        brand = comp['brand'].strip()
        model = comp['model'].strip()
        serie = comp['serie'].strip()
        
        if brand not in compat_data:
            compat_data[brand] = {}
        
        if model not in compat_data[brand]:
            compat_data[brand][model] = []
        
        if serie not in compat_data[brand][model]:
            compat_data[brand][model].append(serie)

    return render(request, 'all_products.html', {
        'page_obj': page_obj,
        'categories': categories,
        'subcategories': subcategories,
        'compat_data': compat_data,
        'selected_category': selected_category,
        'selected_subcategory': selected_subcategory,
        'selected_brand': selected_brand,
        'selected_model': selected_model,
        'selected_serie': selected_serie,
        'selected_stock_type': selected_stock_type,
        'search_query': search_query,
    })


@never_cache
def get_dynamic_filters(request):
    """Vista AJAX para obtener filtros dinámicos sin recargar productos"""
    selected_category = request.GET.get('category')
    selected_subcategory = request.GET.get('subcategory')
    selected_brand = request.GET.get('brand')
    selected_model = request.GET.get('model')
    selected_serie = request.GET.get('serie')
    selected_stock_type = request.GET.get('stock_type')  # Ya lo tienes

    # Base de productos con stock
    base_products = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0))

    # APLICAR FILTRO DE STOCK PRIMERO
    if selected_stock_type == 'nacional':
        base_products = base_products.filter(stock__gt=0)
    elif selected_stock_type == 'internacional':
        base_products = base_products.filter(stock_international__gt=0, stock=0)

    # 1. CATEGORÍAS DINÁMICAS (filtradas por compatibilidad Y stock)
    if selected_brand or selected_model or selected_serie:
        filtered_products = base_products  # Usa base_products que ya tiene filtro de stock
        
        if selected_brand:
            filtered_products = filtered_products.filter(compatibilities__brand=selected_brand)
        if selected_model:
            filtered_products = filtered_products.filter(compatibilities__model=selected_model)
        if selected_serie:
            filtered_products = filtered_products.filter(compatibilities__serie=selected_serie)
        
        category_ids = filtered_products.values_list('category_id', flat=True).distinct()
        categories = list(Category.objects.filter(id__in=category_ids).values('id', 'name').order_by('name'))
    else:
        # Categorías basadas en stock
        category_ids = base_products.values_list('category_id', flat=True).distinct()
        categories = list(Category.objects.filter(id__in=category_ids).exclude(name__in=['BRAKE GR SPORT & ROGUE', 'WHEEL']).values('id', 'name').order_by('name'))

    # 2. SUBCATEGORÍAS DINÁMICAS (con filtro de stock)
    subcategories_query = base_products  # Usa base_products
    
    if selected_category:
        subcategories_query = subcategories_query.filter(category__name=selected_category)
    
    if selected_brand:
        subcategories_query = subcategories_query.filter(compatibilities__brand=selected_brand)
    if selected_model:
        subcategories_query = subcategories_query.filter(compatibilities__model=selected_model)
    if selected_serie:
        subcategories_query = subcategories_query.filter(compatibilities__serie=selected_serie)
    
    subcategories = list(
        subcategories_query
        .exclude(subcategory__isnull=True)
        .exclude(subcategory='')
        .values_list('subcategory', flat=True)
        .distinct()
        .order_by('subcategory')
    )

    # 3. COMPATIBILIDADES DINÁMICAS (filtradas por categoría Y stock)
    if selected_category or selected_subcategory:
        filtered_products = base_products  # Usa base_products
        
        if selected_category:
            filtered_products = filtered_products.filter(category__name=selected_category)
        if selected_subcategory:
            filtered_products = filtered_products.filter(subcategory=selected_subcategory)
        
        compat_ids = filtered_products.values_list('compatibilities__id', flat=True).distinct()
        unique_compatibilities = (
            Compatibility.objects
            .filter(id__in=compat_ids)
            .values('brand', 'model', 'serie')
            .distinct()
            .order_by('brand', 'model', 'serie')
        )
    else:
        # Compatibilidades basadas en stock
        compat_ids = base_products.values_list('compatibilities__id', flat=True).distinct()
        unique_compatibilities = (
            Compatibility.objects
            .filter(id__in=compat_ids)
            .values('brand', 'model', 'serie')
            .distinct()
            .order_by('brand', 'model', 'serie')
        )

    # Construir compat_data
    compat_data = {}
    for comp in unique_compatibilities:
        brand = comp['brand'].strip()
        model = comp['model'].strip()
        serie = comp['serie'].strip()
        
        if brand not in compat_data:
            compat_data[brand] = {}
        
        if model not in compat_data[brand]:
            compat_data[brand][model] = []
        
        if serie not in compat_data[brand][model]:
            compat_data[brand][model].append(serie)

    return JsonResponse({
        'categories': categories,
        'subcategories': subcategories,
        'compat_data': compat_data,
    })


def category_summary(request):
    categories = Category.objects.all()
    return render(request, 'category_summary.html', {"categories": categories})


def search(request):
    # If they fill a form
    if request.method == 'POST':
        searched = request.POST['searched']

        # Query DB
        searched = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched) | Q(category__name__icontains=searched))

        if not searched:
            messages.success(request, "No match found for search.")
            return render(request, 'search.html', {})

        else:
            return render(request, 'search.html', {"searched": searched})
    else:
        return render(request, 'search.html', {})
    


# debug_views.py
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import socket
import os

@csrf_exempt
def test_smtp_debug(request):
    """Endpoint temporal para debug SMTP"""
    
    # Seguridad básica
    secret = request.GET.get('key')
    if secret != 'debug2025':  # Cambia esto por algo más seguro
        return HttpResponse('Forbidden', status=403)
    
    lines = []
    lines.append("=" * 60)
    lines.append("RAILWAY SMTP DEBUG REPORT")
    lines.append("=" * 60)
    
    # Configuración
    lines.append("\n📧 EMAIL SETTINGS:")
    lines.append(f"  Backend: {settings.EMAIL_BACKEND}")
    lines.append(f"  Host: {settings.EMAIL_HOST}")
    lines.append(f"  Port: {settings.EMAIL_PORT}")
    lines.append(f"  Use TLS: {getattr(settings, 'EMAIL_USE_TLS', False)}")
    lines.append(f"  Use SSL: {getattr(settings, 'EMAIL_USE_SSL', False)}")
    lines.append(f"  User: {settings.EMAIL_HOST_USER}")
    lines.append(f"  Password: {'SET ✓' if settings.EMAIL_HOST_PASSWORD else 'NOT SET ✗'}")
    lines.append(f"  Timeout: {getattr(settings, 'EMAIL_TIMEOUT', 'default')}")
    lines.append(f"  From: {settings.DEFAULT_FROM_EMAIL}")
    
    # Environment
    lines.append("\n🌍 ENVIRONMENT:")
    lines.append(f"  Railway: {os.getenv('RAILWAY_ENVIRONMENT', 'NOT DETECTED')}")
    lines.append(f"  Settings: {os.getenv('DJANGO_SETTINGS_MODULE', 'NOT SET')}")
    
    # Test puertos
    lines.append("\n🔌 PORT CONNECTIVITY:")
    host = settings.EMAIL_HOST
    
    for port in [587, 465]:
        lines.append(f"\n  Port {port}:")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            result = sock.connect_ex((host, port))
            
            if result == 0:
                lines.append(f"    ✅ OPEN - Connection successful")
                sock.close()
                
                # Test handshake
                try:
                    import smtplib
                    if port == 465:
                        lines.append(f"    Testing SSL...")
                        s = smtplib.SMTP_SSL(host, port, timeout=15)
                        s.quit()
                        lines.append(f"    ✅ SSL handshake OK")
                    else:
                        lines.append(f"    Testing STARTTLS...")
                        s = smtplib.SMTP(host, port, timeout=15)
                        s.starttls()
                        s.quit()
                        lines.append(f"    ✅ STARTTLS OK")
                except Exception as e:
                    lines.append(f"    ⚠️  Handshake error: {str(e)[:100]}")
            else:
                lines.append(f"    ❌ BLOCKED (error code: {result})")
        except socket.timeout:
            lines.append(f"    ❌ TIMEOUT after 15 seconds")
        except Exception as e:
            lines.append(f"    ❌ Error: {str(e)[:100]}")
    
    # Test autenticación
    lines.append("\n🔐 AUTHENTICATION TEST:")
    try:
        import smtplib
        port = settings.EMAIL_PORT
        use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
        use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
        
        lines.append(f"  Attempting with port {port}, SSL={use_ssl}, TLS={use_tls}")
        
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            if use_tls:
                server.starttls()
        
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        lines.append("  ✅ LOGIN SUCCESSFUL")
        server.quit()
        
    except socket.timeout:
        lines.append("  ❌ LOGIN TIMEOUT")
    except Exception as e:
        lines.append(f"  ❌ LOGIN FAILED: {str(e)[:200]}")
    
    # Test de envío
    if request.GET.get('send') == 'yes':
        lines.append("\n📨 EMAIL SEND TEST:")
        try:
            from django.core.mail import send_mail
            send_mail(
                'Test Railway',
                'Test email body',
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            lines.append("  ✅ EMAIL SENT")
        except Exception as e:
            lines.append(f"  ❌ SEND FAILED: {str(e)[:200]}")
    
    lines.append("\n" + "=" * 60)
    lines.append("Add &send=yes to URL to test actual email sending")
    lines.append("=" * 60)
    
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")