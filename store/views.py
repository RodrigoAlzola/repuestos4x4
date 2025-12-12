from django.shortcuts import render, redirect
from .models import Product, Category, Profile, Compatibility
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django import forms 
from django.db.models import Q
import json
from cart.cart import Cart
from django.views.decorators.cache import never_cache
from store.emails import send_registration_email

# Create your views here.
def home(request):
    # products = Product.objects.all()
    batteries = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0), category__name__iexact='BATTERIES').order_by('?')[:4]
    rear_axle = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0), category__name__iexact='REAR AXLE').order_by('?')[:4]
    engine = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0), category__name__iexact='ENGINE').order_by('?')[:4]

    header_image = 'media/marketing/IMG-20250815-WA0022.jpg'  # ruta relativa dentro de MEDIA
    return render(request, 'home.html', {
        'batteries': batteries,
        'rear_axle': rear_axle,
        'engine': engine,
        'header_image': header_image,
    })

def about(request):
    return render(request, 'about.html', {})

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Get the save cart
            current_user = Profile.objects.get(user__id=request.user.id)
            saved_cart = current_user.old_cart
            if saved_cart:
                converted_cart = json.loads(saved_cart)
                cart = Cart(request)

                for key, value in converted_cart.items():
                    cart.db_add(product=key, quantity=value)


            messages.success(request, ('You have been logged in!'))
            return redirect('home')
        else:
            messages.success(request, ('There was an error, please try again.'))
            return redirect('login')
    else:
        return render(request, 'login.html', {})

def logout_user(request):
    logout(request)
    messages.success(request, ('You have been logged out...'))
    return redirect('home')

from store.emails import send_registration_email  # Ajusta según tu estructura de apps

def register_user(request):
    form = SignUpForm()
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Verificar si el email ya existe en User o Profile
            if User.objects.filter(email=email).exists() or Profile.objects.filter(email=email).exists():
                messages.error(request, 'Este correo electrónico ya está registrado. Por favor usa otro.')
                return redirect('register')
            
            # Guardar el usuario
            user = form.save()
            
            # Crear o actualizar el Profile con los datos del formulario
            profile, created = Profile.objects.get_or_create(user=user)
            profile.full_name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}"
            profile.phone = form.cleaned_data['phone']
            profile.email = email
            profile.save()
            
            # Enviar email de bienvenida
            try:
                send_registration_email(email, profile.full_name)
                messages.success(request, '¡Cuenta creada exitosamente! Hemos enviado un correo de confirmación.')
            except Exception as e:
                print(f"Error enviando email de bienvenida: {e}")
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
    
def update_info(request):
    if request.user.is_authenticated:
        # Obtener o crear Profile y ShippingAddress
        current_user, created = Profile.objects.get_or_create(user=request.user)
        shipping_user, created = ShippingAddress.objects.get_or_create(user=request.user)

        if request.method == 'POST':
            form_type = request.POST.get('form_type')
            
            # Determinar qué formulario se envió
            if form_type == 'personal':
                # Solo procesar UserInfoForm
                form = UserInfoForm(request.POST, instance=current_user)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Tu información personal ha sido actualizada correctamente.")
                    return redirect('update_info')
                else:
                    messages.error(request, "Hubo un error en la información personal. Por favor verifica los datos.")
                    shipping_form = ShippingForm(instance=shipping_user)
                    
            elif form_type == 'shipping':
                # Solo procesar ShippingForm
                shipping_form = ShippingForm(request.POST, instance=shipping_user)
                if shipping_form.is_valid():
                    shipping_form.save()
                    messages.success(request, "Tu dirección de envío ha sido actualizada correctamente.")
                    return redirect('update_info')
                else:
                    messages.error(request, "Hubo un error en la dirección de envío. Por favor verifica los datos.")
                    form = UserInfoForm(instance=current_user)
            else:
                # Si no se especifica form_type, inicializar ambos
                form = UserInfoForm(instance=current_user)
                shipping_form = ShippingForm(instance=shipping_user)
        else:
            # GET request - mostrar formularios con datos actuales
            form = UserInfoForm(instance=current_user)
            shipping_form = ShippingForm(instance=shipping_user)
        
        return render(request, 'update_info.html', {
            'form': form, 
            'shipping_form': shipping_form
        })
    else:
        messages.error(request, "Debes iniciar sesión para acceder a esta página.")
        return redirect('login')
    

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
    selected_brand = request.GET.get('brand')
    selected_model = request.GET.get('model')
    selected_serie = request.GET.get('serie')
    search_query = request.GET.get('search', '')

    products = Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0))

    # Aplicar búsqueda
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Aplicar filtros
    if selected_category:
        products = products.filter(category__name=selected_category)

    if selected_brand:
        products = products.filter(compatibilities__brand=selected_brand)

    if selected_model:
        products = products.filter(compatibilities__model=selected_model)

    if selected_serie:
        products = products.filter(compatibilities__serie=selected_serie)

    products = products.distinct()

    # Paginación
    paginator = Paginator(products, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Datos para filtros (únicos y ordenados) - VERSIÓN OPTIMIZADA
    categories = Category.objects.all().order_by('name')
    
    # Construir compat_data con valores únicos y ordenados (más eficiente)
    compat_data = {}
    
    # Obtener combinaciones únicas de marca-modelo-serie ordenadas
    unique_compatibilities = (
        Compatibility.objects
        .values('brand', 'model', 'serie')
        .distinct()
        .order_by('brand', 'model', 'serie')
    )

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
        'compat_data': compat_data,
        'selected_category': selected_category,
        'selected_brand': selected_brand,
        'selected_model': selected_model,
        'selected_serie': selected_serie,
        'search_query': search_query,
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