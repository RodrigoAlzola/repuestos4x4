"""Capa comercial sobre las categorías originales, sin modificar el inventario."""
from django.db.models import Q, Case, When, Value, IntegerField
from .models import Product, Compatibility

FAMILIES = [
    {'slug': 'suspension', 'name': 'Suspensión', 'icon': '↟', 'description': 'Amortiguadores, ballestas y componentes para tu suspensión.', 'categories': ['SUSPENSION FRONT', 'SUSPENSION REAR']},
    {'slug': 'frenos', 'name': 'Frenos', 'icon': '◉', 'description': 'Discos, pastillas y componentes del sistema de frenado.', 'categories': ['BRAKE', 'BRAKE GR SPORT & ROGUE']},
    {'slug': 'motor', 'name': 'Motor y refrigeración', 'icon': '⚙', 'description': 'Refrigeración, combustible y componentes de motor.', 'categories': ['ENGINE', 'COOLING', 'FUEL', 'EXHAUST', 'SNORKEL']},
    {'slug': 'transmision', 'name': 'Transmisión y embrague', 'icon': '⇄', 'description': 'Embragues, cajas de cambio y cajas de transferencia.', 'categories': ['CLUTCH', 'GEARBOX', 'TRANSFER CASE', 'TRANSMISSION']},
    {'slug': 'tren-motriz', 'name': 'Ejes y diferenciales', 'icon': '⊕', 'description': 'Rodamientos, retenes, juntas y kits de diferencial.', 'categories': ['DIFF FRONT', 'DIFF REAR', 'DRIVELINE', 'FRONT AXLE', 'REAR AXLE', 'WHEEL']},
    {'slug': 'direccion', 'name': 'Dirección', 'icon': '↗', 'description': 'Componentes para reparar el sistema de dirección.', 'categories': ['STEERING']},
    {'slug': 'mantenimiento', 'name': 'Filtración y mantenimiento', 'icon': '≋', 'description': 'Filtros y kits para el servicio de tu vehículo.', 'categories': ['FILTERS', 'LUBRICATION']},
    {'slug': 'otros', 'name': 'Otros repuestos', 'icon': '+', 'description': 'Electricidad, baterías y otros componentes del catálogo.', 'categories': []},
]

def family_query(slug):
    family = next((f for f in FAMILIES if f['slug'] == slug), None)
    if family is None:
        return Q(pk__in=[])
    if slug == 'otros':
        return ~Q(category__name__in=[c for f in FAMILIES for c in f['categories']])
    return Q(category__name__in=family['categories'])

def available_products():
    return Product.objects.filter(Q(stock__gt=0) | Q(stock_international__gt=0)).exclude(name='').select_related('category', 'provider')

def filter_vehicle(products, vehicle):
    # Un solo filter garantiza que marca, modelo y serie pertenecen a la misma aplicación.
    conditions = {f'compatibilities__{k}': vehicle[k] for k in ('brand', 'model', 'serie') if vehicle.get(k)}
    if conditions:
        products = products.filter(**conditions)
    if vehicle.get('motor'):
        products = products.filter(motor=vehicle['motor'])
    return products.distinct()

def vehicle_from_request(request):
    keys = ('brand', 'model', 'serie', 'motor')
    if request.GET.get('clear_vehicle') == '1':
        request.session.pop('catalog_vehicle', None)
        return {}
    if any(k in request.GET for k in keys):
        vehicle = {k: request.GET.get(k, '').strip() for k in keys}
        if not vehicle['brand']:
            vehicle = {}
        elif not vehicle['model']:
            vehicle.update(serie='', motor='')
        elif not vehicle['serie']:
            vehicle['motor'] = ''
        # Sólo recordar aplicaciones existentes; la consulta inválida sigue devolviendo cero.
        if vehicle and filter_vehicle(Product.objects.all(), vehicle).exists():
            request.session['catalog_vehicle'] = vehicle
        else:
            request.session.pop('catalog_vehicle', None)
        return vehicle
    return request.session.get('catalog_vehicle', {})

def vehicle_options(vehicle):
    compat = Compatibility.objects.filter(product__in=available_products())
    def values(query, field):
        return list(query.exclude(**{field: ''}).values_list(field, flat=True).distinct().order_by(field))
    brands = values(compat, 'brand')
    models = values(compat.filter(brand=vehicle.get('brand')), 'model') if vehicle.get('brand') else []
    series = values(compat.filter(brand=vehicle.get('brand'), model=vehicle.get('model')), 'serie') if vehicle.get('model') else []
    motors = values(filter_vehicle(available_products(), {k: v for k, v in vehicle.items() if k != 'motor'}), 'motor') if vehicle.get('serie') else []
    return {'brand': brands, 'model': models, 'serie': series, 'motor': motors}

def family_counts(products):
    return [dict(f, count=products.filter(family_query(f['slug'])).count()) for f in FAMILIES]

def curated(products):
    return products.annotate(
        image_priority=Case(When(Q(image__isnull=True) | Q(image='') | Q(image__icontains='DEFAULTPARTIMG'), then=Value(1)), default=Value(0), output_field=IntegerField()),
        kit_priority=Case(When(Q(name__icontains='kit') | Q(name__icontains='heavy duty') | Q(name__icontains='reforzad'), then=Value(0)), default=Value(1), output_field=IntegerField()),
    ).order_by('image_priority', 'kit_priority', 'name', 'pk')

def discovery_cards(products):
    cards = []
    for slug, title, text, family in [
        ('diferenciales', 'Más que piezas sueltas.', 'Explora kits y componentes para reparar tus ejes y diferenciales.', 'tren-motriz'),
        ('refrigeracion', 'El motor también necesita respaldo.', 'Descubre los componentes de refrigeración disponibles en el catálogo.', 'motor'),
        ('servicio', 'Prepara tu próximo mantenimiento.', 'Encuentra filtros para el servicio de tu 4x4.', 'mantenimiento'),
    ]:
        selection = products.filter(family_query(family))
        if slug == 'refrigeracion':
            selection = selection.filter(category__name='COOLING')
        product = curated(selection).first()
        if product:
            cards.append({'title': title, 'text': text, 'family': family, 'product': product})
    return cards
