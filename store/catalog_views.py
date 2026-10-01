from urllib.parse import urlencode
import json
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET
from .models import Product
from .catalog import (available_products, filter_vehicle, vehicle_from_request,
                      vehicle_options, family_counts, family_query, curated, discovery_cards)

def context_for(request):
    vehicle = vehicle_from_request(request)
    products = filter_vehicle(available_products(), vehicle)
    # Sólo recordar una búsqueda explícita y válida, nunca una selección heredada
    # de sesión: así quitar un acceso no lo recrea al recargar la portada.
    remember_vehicle = (request.path == reverse('all_products')
                        and bool(request.GET.get('brand') and request.GET.get('model'))
                        and request.GET.get('clear_vehicle') != '1'
                        and bool(vehicle.get('model')) and products.exists())
    return products, {'vehicle': vehicle, 'options': vehicle_options(vehicle),
                      'garage_config': {'vehicle': vehicle if remember_vehicle else {}, 'remember': remember_vehicle},
                      'vehicle_label': ' · '.join(vehicle.get(k, '') for k in ('brand', 'model', 'serie', 'motor') if vehicle.get(k)),
                      'vehicle_query': urlencode({k: v for k, v in vehicle.items() if v})}

@require_GET
def home(request):
    products, context = context_for(request)
    featured = []
    for family in ('suspension', 'frenos', 'transmision', 'tren-motriz'):
        item = curated(products.filter(family_query(family))).first()
        if item:
            featured.append(item)
    if len(featured) < 4:
        featured.extend(curated(products.exclude(pk__in=[item.pk for item in featured]))[:4 - len(featured)])
    context.update(families=family_counts(products), featured=featured,
                   discoveries=discovery_cards(products), catalog_count=available_products().count(),
                   vehicle_count=products.count())
    return render(request, 'catalog_home.html', context)

@require_GET
def listing(request):
    products, context = context_for(request)
    family = request.GET.get('family', '')
    search = request.GET.get('search', '').strip()
    stock = request.GET.get('stock_type', '')
    sort = request.GET.get('sort', '')
    # Conservar enlaces antiguos a categorías y subcategorías.
    for field in ('category', 'subcategory'):
        if request.GET.get(field):
            products = products.filter(**{('category__name' if field == 'category' else field): request.GET[field]})
    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search) | Q(sku__icontains=search) | Q(part_number__icontains=search))
    if stock == 'nacional':
        products = products.filter(stock__gt=0)
    elif stock == 'internacional':
        products = products.filter(stock__lte=0, stock_international__gt=0)
    # Conteos dentro de la búsqueda actual, antes de restringir a una familia.
    families = family_counts(products)
    family_params = request.GET.copy()
    for key in ('page', 'family', 'clear_vehicle'):
        family_params.pop(key, None)
    for key in ('brand', 'model', 'serie', 'motor'):
        family_params[key] = context['vehicle'].get(key, '')
    catalog_url = reverse('all_products')
    context['all_families_url'] = f'{catalog_url}?{family_params.urlencode()}#catalog-families'
    for item in families:
        family_params['family'] = item['slug']
        item['url'] = f'{catalog_url}?{family_params.urlencode()}#catalog-families'
    context.update(families=families, family_total=sum(item['count'] for item in families))
    if family:
        products = products.filter(family_query(family))
    products = curated(products)
    if sort in ('price', '-price'):
        from django.db.models import Case, When, F
        products = products.annotate(effective_price=Case(When(is_sale=True, then=F('sale_price')), default=F('price'))).order_by(('-' if sort.startswith('-') else '') + 'effective_price', 'pk')
    page = Paginator(products, 12).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    params.pop('clear_vehicle', None)
    context.update(page_obj=page, search_query=search, selected_family=family,
                   selected_stock_type=stock, selected_sort=sort, pagination_query=params.urlencode(),
                   selected_category=request.GET.get('category', ''), selected_subcategory=request.GET.get('subcategory', ''))
    return render(request, 'catalog_list.html', context)

@require_GET
def options(request):
    vehicle = {k: request.GET.get(k, '') for k in ('brand', 'model', 'serie')}
    return JsonResponse(vehicle_options(vehicle))

@require_GET
def product(request, pk):
    item = get_object_or_404(Product.objects.select_related('category', 'provider').prefetch_related('compatibilities'), pk=pk)
    products, context = context_for(request)
    applications = list(item.compatibilities.all().order_by('brand', 'model', 'serie'))
    has_vehicle = bool(context['vehicle'].get('model'))
    schema = {'@context': 'https://schema.org', '@type': 'Product', 'name': item.name,
              'description': item.description or item.name, 'sku': item.part_number or item.sku,
              'offers': {'@type': 'Offer', 'priceCurrency': 'CLP',
                         'price': str(item.sale_price if item.is_sale else item.price),
                         'url': f'https://4x4max.cl/product/{item.pk}',
                         'availability': 'https://schema.org/InStock' if item.stock > 0 or item.stock_international > 0 else 'https://schema.org/OutOfStock'}}
    if item.image and 'DEFAULTPARTIMG' not in item.image:
        schema['image'] = item.image
    context['product_schema'] = json.dumps(schema).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    context.update(product=item, applications=applications,
                   compatible=filter_vehicle(Product.objects.filter(pk=pk), context['vehicle']).exists() if has_vehicle else None,
                   related=curated(products.filter(category=item.category).exclude(pk=pk))[:4],
                   quantity_range=range(1, min(max(item.stock, item.stock_international if item.stock <= 0 else 0), 10) + 1))
    return render(request, 'catalog_product.html', context)
