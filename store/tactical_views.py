"""Página independiente: sin filtros de vehículo, ORM, carro ni importadores de productos."""
from urllib.parse import urlencode
import json
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET
from .tactical_parts import (load_references, normalize_search, CATEGORIES,
                             CANONICAL_URL, WHATSAPP_BASE)


@require_GET
def references(request):
    catalog = load_references()
    rows = catalog['references']
    search = request.GET.get('q', '').strip()[:160]
    tokens = normalize_search(search).split()
    searched = [row for row in rows if all(token in row['search_text'] for token in tokens)]
    category = request.GET.get('familia', '')
    if category not in CATEGORIES:
        category = ''
    filtered = [row for row in searched if not category or row['category'] == category]
    path = reverse('tactical_parts')

    def filter_url(selected=''):
        params = {key: value for key, value in [('q', search), ('familia', selected)] if value}
        return path + ('?' + urlencode(params) if params else '') + '#referencias'

    families = [{'slug': '', 'label': 'Todas', 'count': len(searched), 'url': filter_url()}]
    families.extend({'slug': key, 'label': label,
                     'count': sum(row['category'] == key for row in searched), 'url': filter_url(key)}
                    for key, label in CATEGORIES.items())
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', '@id': CANONICAL_URL, 'url': CANONICAL_URL,
         'name': 'Repuestos para vehículos tácticos | 4x4MAX',
         'description': 'Referencias de admisión, filtración y frenos para vehículos tácticos.',
         'inLanguage': 'es-CL'},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Inicio', 'item': 'https://4x4max.cl/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Repuestos para vehículos tácticos', 'item': CANONICAL_URL},
        ]},
    ]}
    # JSON seguro en un script: las descripciones del archivo no pueden cerrar la etiqueta.
    schema_json = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    general_quote = WHATSAPP_BASE + '?' + urlencode({'text': 'Hola, necesito repuestos para un vehículo táctico. Quisiera consultar referencias y disponibilidad.'})
    return render(request, 'tactical_parts.html', {
        'references': filtered, 'reference_count': len(rows), 'result_count': len(filtered),
        'search_query': search, 'selected_family': category, 'families': families,
        'stock_is_demo': catalog['stock_mode'] == 'demo', 'tactical_schema': schema_json,
        'demo_reference_count': sum(row['is_demo'] for row in rows),
        'general_quote_url': general_quote, 'clear_url': path + '#referencias',
    })
