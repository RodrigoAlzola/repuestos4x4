"""Búsqueda y clasificación comercial; conserva los datos técnicos del proveedor."""
import re
import unicodedata
from functools import reduce
from operator import or_
from django.db.models import Q, F, Value, Case, When, CharField, IntegerField, Count
from django.db.models.functions import Concat, Coalesce, Lower, Replace

SYSTEM_LABELS = {
    'SUSPENSION FRONT': 'Suspensión delantera', 'SUSPENSION REAR': 'Suspensión trasera',
    'BRAKE': 'Frenos', 'BRAKE GR SPORT & ROGUE': 'Frenos GR Sport y Rogue',
    'ENGINE': 'Motor', 'COOLING': 'Refrigeración', 'FUEL': 'Combustible',
    'EXHAUST': 'Escape', 'SNORKEL': 'Snorkel', 'CLUTCH': 'Embrague',
    'GEARBOX': 'Caja de cambios', 'TRANSFER CASE': 'Caja de transferencia',
    'TRANSMISSION': 'Transmisión', 'DIFF FRONT': 'Diferencial delantero',
    'DIFF REAR': 'Diferencial trasero', 'DRIVELINE': 'Cardán y transmisión',
    'FRONT AXLE': 'Eje delantero', 'REAR AXLE': 'Eje trasero', 'WHEEL': 'Ruedas',
    'STEERING': 'Dirección', 'FILTERS': 'Filtros', 'LUBRICATION': 'Lubricación',
    'AIR CONDITIONING': 'Aire acondicionado', 'BATTERIES': 'Baterías',
    'BODY PARTS': 'Carrocería', 'ELECTRICAL': 'Electricidad', 'ACCESSORIES': 'Accesorios',
    'INTAKE MANIFOLD': 'Admisión', 'RECOVERY': 'Recuperación y rescate',
    'SUSPENSION KITS': 'Kits de suspensión', 'TRANSMISSION AUTOMATIC': 'Transmisión automática',
}

# Primero los kits: una descripción que enumera retenes no convierte el kit
# completo en un retén individual. Los grupos ambiguos no se desdoblan a ciegas.
PIECE_RULES = [
    ('kits', 'Kits de reparación y conjuntos', ('kit', 'kits', 'overhaul kit', 'juego', 'conjunto'), ()),
    ('separadores', 'Separadores', (), ()),
    ('retenes', 'Retenes', ('oil seal', 'oilseal', 'seal', 'seals', 'reten', 'retenes', 'sello de aceite'), ('OIL SEAL', 'OIL SEALS', 'SEALS')),
    ('juntas', 'Juntas y empaquetaduras', ('gasket', 'gaskets', 'junta', 'juntas', 'empaquetadura'), ('GASKETS',)),
    ('radiadores', 'Radiadores', ('radiator', 'radiador', 'radiadores'), ('RADIATOR',)),
    ('bombas-agua', 'Bombas de agua', ('water pump', 'waterpump', 'bomba de agua'), ('WATER PUMP',)),
    ('rodamientos', 'Rodamientos', ('bearing', 'bearings', 'rodamiento', 'rodamientos'), ('WHEEL BEARINGS',)),
    ('amortiguadores', 'Amortiguadores', ('shock absorber', 'amortiguador', 'amortiguadores'), ('SHOCK ABSORBER',)),
    ('pastillas', 'Pastillas de freno', ('brake pad', 'brake pads', 'pastilla', 'pastillas'), ('PADS',)),
    ('discos', 'Discos de freno', ('brake disc', 'brake rotor', 'disco de freno'), ('DISCS', 'ROTORS')),
    ('correas', 'Correas', ('belt', 'belts', 'correa', 'correas'), ('BELTS',)),
    ('mangueras', 'Mangueras', ('hose', 'hoses', 'manguera', 'mangueras'), ('HOSES', 'AIR CLEANER HOSE')),
    ('termostatos', 'Termostatos', ('thermostat', 'termostato'), ('THERMOSTAT',)),
    ('ventiladores', 'Ventiladores', ('fan blade', 'ventilador'), ('FAN BLADE',)),
    ('intercoolers', 'Intercoolers', ('intercooler',), ('INTERCOOLER',)),
    ('inyectores', 'Inyectores', ('injector', 'inyector', 'inyectores'), ('INJECTOR', 'INJECTOR SET')),
    ('alternadores', 'Alternadores', ('alternator', 'alternador'), ('ALTERNATOR',)),
    ('filtros', 'Filtros', ('filter', 'filtro', 'filtros'), ('FUEL FILTER', 'OIL FILTER', 'AIR FILTER')),
    ('bujes', 'Bujes', ('bush', 'bushes', 'buje', 'bujes'), ('BUSHES & CIRCLIPS',)),
    ('resortes', 'Resortes y ballestas', ('spring', 'resorte', 'ballesta'), ('SPRING',)),
    ('rotulas', 'Rótulas', ('ball joint', 'rotula'), ('BALL JOINT',)),
    ('bloqueos', 'Bloqueos de diferencial', ('e locker', 'elocker', 'bloqueo'), ('E LOCKER', 'E LOCKER DANA DIFF')),
    ('cubos', 'Cubos de rueda libre', ('free wheeling hub', 'free wheel hub', 'avm'), ('FREE WHEELING HUB',)),
    ('semiejes', 'Semiejes', ('axle shaft', 'semieje'), ('AXLE SHAFT',)),
    ('cardanes', 'Cardanes', ('tailshaft', 'propeller shaft', 'cardan'), ('TAILSHAFT',)),
    ('soportes', 'Soportes', ('engine mount', 'soporte de motor'), ('ENGINE MOUNTS',)),
    ('cilindros', 'Cilindros maestros', ('master cylinder', 'cilindro maestro'), ('MASTER CYLINDER',)),
    ('bandejas', 'Bandejas y brazos de suspensión', ('control arm',), ('CONTROL ARM',)),
    ('protecciones', 'Protecciones inferiores', ('bash plate',), ('BASH PLATE',)),
    ('distribucion', 'Componentes de distribución', (), ('TIMING COMPONENTS',)),
    ('electricidad', 'Interruptores, relés y cableado', (), ('SWITCHES & RELAYS', 'WIRING', 'WIRE LEAD INJECTOR')),
    ('fijaciones', 'Pernos, tuercas y fijaciones', (), ('STUDS, NUTS & WASHERS', 'CENTRE BOLT')),
    ('juntas-retenes', 'Juntas y retenes sin desglosar', (), ('GASKETS & SEALS',)),
    ('otros', 'Otros componentes', (), ()),
]
PIECE_LABELS = {key: label for key, label, _, _ in PIECE_RULES}
SYNONYMS = [
    ('bomba de agua', 'bombas de agua', 'water pump', 'water pumps', 'waterpump'),
    ('oil seal', 'oil seals', 'oilseal', 'seal', 'seals', 'reten', 'retenes', 'sello de aceite'),
    ('gasket', 'gaskets', 'junta', 'juntas', 'empaquetadura', 'empaquetaduras'),
    ('bearing', 'bearings', 'rodamiento', 'rodamientos'),
    ('radiator', 'radiador', 'radiadores'), ('differential', 'diff', 'diferencial', 'diferenciales'),
    ('front', 'delantero', 'delantera', 'frontal'), ('rear', 'trasero', 'trasera'),
    ('cooling', 'refrigeracion'), ('shock absorber', 'amortiguador', 'amortiguadores'),
    ('brake', 'freno', 'frenos'), ('filter', 'filtro', 'filtros'), ('kit', 'kits', 'juego'),
]

def normalize(value):
    text = ''.join(c for c in unicodedata.normalize('NFKD', value or '') if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', text.lower()).strip()

def reference_key(value):
    return re.sub(r'[^a-z0-9]', '', normalize(value))

def normalized_sql(expression):
    # Lower de SQLite sólo cubre ASCII; ambos casos se reemplazan explícitamente.
    for source, target in zip('áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN'):
        expression = Replace(expression, Value(source), Value(target))
    return Lower(expression)

def code_sql(field):
    expression = Lower(Coalesce(F(field), Value('')))
    for char in (' ', '-', '.', '_', '/', '\\'):
        expression = Replace(expression, Value(char), Value(''))
    return expression

def word_query(field, terms):
    variants = []
    accented = {'reten': ('retén', 'retÉn'), 'retenes': ('reténes', 'retÉnes'),
                'rotula': ('rótula', 'rÓtula'), 'cardan': ('cardán', 'cardÁn')}
    for term in terms:
        variants.extend((normalize(term), *accented.get(normalize(term), ())))
    if not variants:
        return Q(pk__in=[])
    pattern = r'(^|[^a-z0-9])(' + '|'.join(re.escape(term) for term in variants) + r')([^a-z0-9]|$)'
    return Q(**{field + '__regex': pattern})

def searchable(products):
    products = products.alias(
        catalog_text=normalized_sql(Concat(Value(' '), 'name', Value(' '), Coalesce('description', Value('')), Value(' '), Coalesce('subcategory', Value('')), Value(' '), Coalesce('category__name', Value('')), Value(' '), output_field=CharField())),
        piece_text=Lower(Concat(Value(' '), 'name', Value(' '), Coalesce('description', Value('')), Value(' '), output_field=CharField())),
        sku_key=code_sql('sku'), part_key=code_sql('part_number'),
    )
    conditions = []
    for key, _, terms, subgroups in PIECE_RULES[:-1]:
        condition = word_query('piece_text', terms) | Q(subcategory__in=subgroups)
        if key == 'kits':
            condition |= Q(category__name='SUSPENSION KITS')
        if key == 'separadores':
            # «SPACER ... SUITS PINION SEAL» describe un separador, no un retén.
            condition = Q(name__iregex=r'^\s*(spacer|collapsible spacer|separador|separadores)([^a-z0-9]|$)')
        conditions.append(When(condition, then=Value(key)))
    return products.annotate(piece_type=Case(*conditions, default=Value('otros'), output_field=CharField()))

def search_units(query):
    text = normalize(query)
    words = text.split()
    aliases = {phrase: group for group in SYNONYMS for phrase in group}
    units = []
    while words:
        for length in range(min(4, len(words)), 0, -1):
            phrase = ' '.join(words[:length])
            if phrase in aliases:
                units.append(aliases[phrase]); del words[:length]; break
        else:
            units.append((words.pop(0),))
    return units

def apply_search(products, query):
    key = reference_key(query)
    condition = Q()
    for unit in search_units(query):
        condition &= word_query('catalog_text', unit) if len(unit) > 1 else Q(catalog_text__contains=unit[0])
    return products.filter(condition | Q(sku_key__contains=key) | Q(part_key__contains=key)) if key else products.none()

def ordered(products, query, sort):
    products = products.annotate(effective_price=Case(When(is_sale=True, then=F('sale_price')), default=F('price')))
    if sort in ('price', '-price'):
        return products.order_by(sort.replace('price', 'effective_price'), 'pk')
    if query:
        key = reference_key(query)
        products = products.annotate(search_rank=Case(
            When(Q(sku_key=key) | Q(part_key=key), then=Value(0)),
            When(Q(sku_key__startswith=key) | Q(part_key__startswith=key), then=Value(1)),
            default=Value(2), output_field=IntegerField()))
        return products.order_by('search_rank', 'name', 'pk')
    return products.order_by('name', 'pk')

def system_label(value):
    return SYSTEM_LABELS.get(value, 'Otros sistemas · ' + value.title())

def facet_options(products, field, label):
    rows = products.order_by().values(field).annotate(count=Count('pk', distinct=True))
    return sorted([{'value': row[field], 'label': label(row[field]), 'count': row['count']} for row in rows if row[field]], key=lambda row: normalize(row['label']))
