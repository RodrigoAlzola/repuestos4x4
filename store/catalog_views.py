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
from .catalog_search import (searchable, apply_search, reference_key, ordered,
                             facet_options, system_label, PIECE_LABELS)

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
    search = request.GET.get('search', '').strip()[:160]
    stock = request.GET.get('stock_type', '')
    sort = request.GET.get('sort', '')
    system = request.GET.get('system', request.GET.get('category', ''))
    piece_type = request.GET.get('piece_type', '')
    subcategory = request.GET.get('subcategory', '')
    scope = 'all' if request.GET.get('scope') == 'all' or not context['vehicle'].get('brand') else 'vehicle'
    per_page = int(request.GET.get('per_page', '24')) if request.GET.get('per_page', '24') in ('24', '48') else 24
    view = 'grid' if request.GET.get('view') == 'grid' else 'list'
    products = searchable(available_products() if scope == 'all' else products)
    exact = False
    if search:
        # Una referencia exacta no queda oculta por stock o un vehículo heredado.
        key = reference_key(search)
        references = searchable(Product.objects.exclude(name='').select_related('category', 'provider'))
        references = references.filter(Q(sku_key=key) | Q(part_key=key)) if key else references.none()
        if references.exists():
            products, exact, scope = references, True, 'all'
            family = system = piece_type = stock = subcategory = ''
        else:
            products = apply_search(products, search)
    if subcategory:
        products = products.filter(subcategory=subcategory)
    if stock == 'nacional':
        products = products.filter(stock__gt=0)
    elif stock == 'internacional':
        products = products.filter(stock__lte=0, stock_international__gt=0)
    # Los conteos permiten cambiar familia sin conservar un sistema incompatible.
    families = family_counts(products)
    family_params = request.GET.copy()
    for key in ('page', 'family', 'system', 'category', 'subcategory', 'piece_type', 'clear_vehicle'):
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
    systems = facet_options(products, 'category__name', system_label)
    if system:
        products = products.filter(category__name=system)
    types = facet_options(products, 'piece_type', lambda key: PIECE_LABELS[key])
    if piece_type:
        products = products.filter(piece_type=piece_type)
    products = ordered(products, search, sort)
    page = Paginator(products, per_page).get_page(request.GET.get('page'))
    for item in page:
        item.catalog_type_label = PIECE_LABELS[item.piece_type]
        item.catalog_system_label = system_label(item.category.name) if item.category else ''
    params = request.GET.copy()
    for key in ('page', 'clear_vehicle', 'category', 'family', 'system', 'piece_type', 'subcategory', 'stock_type'):
        params.pop(key, None)
    for key, value in [('family', family), ('system', system), ('piece_type', piece_type), ('subcategory', subcategory), ('stock_type', stock), ('scope', scope)]:
        if value:
            params[key] = value
    for key in ('brand', 'model', 'serie', 'motor'):
        params[key] = context['vehicle'].get(key, '')
    chips = []
    labels = {'family': next((f['name'] for f in families if f['slug'] == family), family),
              'system': system_label(system) if system else '', 'piece_type': PIECE_LABELS.get(piece_type, piece_type),
              'subcategory': subcategory, 'search': search,
              'stock_type': {'nacional': 'Disponible en Chile', 'internacional': 'Por importación'}.get(stock, '')}
    for key, label in labels.items():
        if not label:
            continue
        removed = params.copy()
        removed.pop(key, None)
        if key == 'family':
            for lower in ('system', 'piece_type', 'subcategory'):
                removed.pop(lower, None)
        if key == 'system':
            removed.pop('piece_type', None)
            removed.pop('subcategory', None)
        chips.append({'label': label, 'url': f'{catalog_url}?{removed.urlencode()}#catalog-results'})
    reset = params.copy()
    for key in labels:
        reset.pop(key, None)
    context.update(page_obj=page, search_query=search, selected_family=family,
                   selected_stock_type=stock, selected_sort=sort, pagination_query=params.urlencode(),
                   selected_category=system, selected_subcategory=subcategory,
                   system_options=systems, type_options=types, selected_piece_type=piece_type,
                   search_scope=scope, exact_reference=exact, per_page=str(per_page), selected_view=view,
                   filter_chips=chips, reset_search_url=f'{catalog_url}?{reset.urlencode()}#catalog-results')
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
