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

# Create your views here.
def home(request):
    products = Product.objects.all()
    return render(request, 'home.html', {'products': products})

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

def register_user(request):
    form = SignUpForm()
    if request.method ==  'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            # log in user
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, ('Username Created - Please fill your information.'))
            return redirect('update_info')
        else:
            messages.success(request, ('Whooops. There was an error, try again.'))
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
        current_user = Profile.objects.get(user__id=request.user.id)
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)

        form = UserInfoForm(request.POST or None, instance=current_user)
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)

        if form.is_valid() or shipping_form.is_valid():
            form.save()
            shipping_form.save()
            messages.success(request, "Your Info has been Updated.")
            return redirect('home')
        return render(request, 'update_info.html', {'form': form, 'shipping_form': shipping_form})
    else:
        messages.success(request, "You must been Logged in to access the Update page.")
        return redirect('home')
    

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

    return render(request, 'product.html', {
        'product': product,
        'compat_data': compat_data,
        'quantity_range': range(1, product.stock + 1),
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


def all_products(request):
    # Filtros desde GET
    selected_category = request.GET.get('category')
    selected_brand = request.GET.get('brand')
    selected_model = request.GET.get('model')
    selected_serie = request.GET.get('serie')
    search_query = request.GET.get('search', '')

    products = Product.objects.all()

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
    paginator = Paginator(products, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Datos para filtros
    categories = Category.objects.all()
    compat_data = {}
    for comp in Compatibility.objects.all():
        brand = comp.brand.strip()
        model = comp.model.strip()
        serie = comp.serie.strip()
        compat_data.setdefault(brand, {}).setdefault(model, []).append(serie)

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