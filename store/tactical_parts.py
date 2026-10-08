"""Referencias especiales de archivo. No consulta ni modifica el inventario Product."""
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata
from urllib.parse import urlencode


DATA_FILE = Path(__file__).parent / 'data' / 'tactical_parts.json'
CATEGORIES = {'admision': 'Admisión y filtración', 'frenos': 'Frenos'}
AVAILABILITY = {'limited': 'Stock limitado', 'on_request': 'A pedido'}
CANONICAL_URL = 'https://4x4max.cl/repuestos-vehiculos-tacticos/'
WHATSAPP_BASE = 'https://wa.me/56941815955'


class ReferenceDataError(ValueError):
    pass


def normalize_search(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(c))


def price_label(value, currency):
    if currency == 'CLP':
        return '$ ' + format(value, ',.0f').replace(',', '.') + ' CLP'
    amount = format(value, ',.2f').replace(',', '_').replace('.', ',').replace('_', '.')
    return currency + ' ' + amount


def load_references(path=None):
    """Lee valores fijos; los stocks de demostración no se regeneran al visitar."""
    source = Path(path) if path is not None else DATA_FILE
    try:
        config = json.loads(source.read_text(encoding='utf-8-sig'), parse_float=Decimal)
    except (OSError, ValueError) as exc:
        raise ReferenceDataError(f'No se pudo leer {source.name}: {exc}') from exc
    if not isinstance(config, dict) or not isinstance(config.get('references'), list):
        raise ReferenceDataError('Se requiere un objeto con una lista references.')
    currency = config.get('currency', 'CLP')
    mode = config.get('stock_mode', 'demo')
    vat = config.get('prices_include_vat')
    if currency not in ('CLP', 'USD', 'EUR'):
        raise ReferenceDataError('currency debe ser CLP, USD o EUR.')
    if mode not in ('demo', 'manual'):
        raise ReferenceDataError('stock_mode debe ser demo o manual.')
    if vat is not None and type(vat) is not bool:
        raise ReferenceDataError('prices_include_vat debe ser true, false o null.')
    records, refs, sku_records = [], set(), {}
    for raw in config['references']:
        if not isinstance(raw, dict):
            raise ReferenceDataError('Cada referencia debe ser un objeto.')
        row = dict(raw)
        for key in ('ref', 'name', 'sku', 'description', 'category'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ReferenceDataError(f'Falta {key} en una referencia.')
            row[key] = row[key].strip()
        ref = row['ref']
        if not re.fullmatch(r'[A-Z][A-Z0-9-]{1,31}', ref) or ref in refs:
            raise ReferenceDataError(f'Referencia inválida o repetida: {ref}.')
        refs.add(ref)
        if row['category'] not in CATEGORIES:
            raise ReferenceDataError(f'{ref}: categoría no reconocida.')
        availability = row.get('availability', 'on_request')
        if availability not in AVAILABILITY:
            raise ReferenceDataError(f'{ref}: disponibilidad no reconocida.')
        stock = row.get('stock')
        if stock is not None and (type(stock) is not int or stock < 0):
            raise ReferenceDataError(f'{ref}: stock debe ser entero no negativo o null.')
        if availability == 'limited' and (stock is None or stock < 1):
            raise ReferenceDataError(f'{ref}: Stock limitado requiere una cantidad positiva.')
        if mode == 'demo' and stock is not None and not 1 <= stock <= 5:
            raise ReferenceDataError(f'{ref}: en demostración, stock debe estar entre 1 y 5.')
        sku_pending = row.get('sku_pending', False)
        if type(sku_pending) is not bool:
            raise ReferenceDataError(f'{ref}: sku_pending debe ser true o false.')
        is_demo = row.get('is_demo', False)
        if type(is_demo) is not bool:
            raise ReferenceDataError(f'{ref}: is_demo debe ser true o false.')
        image = row.get('image', '')
        if not isinstance(image, str) or (image and (
            not image.startswith('images/tactical/') or '..' in PurePosixPath(image).parts
            or '\\' in image or '?' in image or '#' in image
            or PurePosixPath(image).suffix.lower() not in ('.webp', '.png', '.jpg', '.jpeg')
        )):
            raise ReferenceDataError(f'{ref}: imagen debe ser una ruta local dentro de images/tactical/.')
        for key in ('application', 'notes'):
            if not isinstance(row.get(key, ''), str):
                raise ReferenceDataError(f'{ref}: {key} debe ser texto.')
            row[key] = row.get(key, '').strip()
        raw_price = row.get('price')
        price = None
        if raw_price is not None:
            # No interpretar separadores de miles como decimales: 100.000 no es un precio válido.
            if type(raw_price) is bool or not re.fullmatch(r'\d+(?:\.\d{1,2})?', str(raw_price)):
                raise ReferenceDataError(f'{ref}: precio numérico sin separadores de miles o null.')
            try:
                price = Decimal(str(raw_price))
            except InvalidOperation as exc:
                raise ReferenceDataError(f'{ref}: precio inválido.') from exc
            if currency == 'CLP' and price != price.to_integral_value():
                raise ReferenceDataError(f'{ref}: precios CLP en pesos enteros.')
        row.update(
            price=price, price_display=price_label(price, currency) if price is not None else 'Consultar precio',
            vat_label='IVA incluido' if vat is True else 'Más IVA' if vat is False else 'IVA por confirmar',
            availability=availability, availability_label=AVAILABILITY[availability],
            category_label=CATEGORIES[row['category']], sku_pending=sku_pending, is_demo=is_demo,
            image=image, image_static=image or 'images/part-placeholder.svg',
            stock=stock, stock_is_demo=mode == 'demo',
        )
        sku_note = 'Número de parte por confirmar.' if sku_pending else f"SKU {row['sku']}."
        message = f"Hola, quiero cotizar {row['name']}. {sku_note}"
        if is_demo:
            message = (f"Hola, estoy revisando un producto de prueba: {row['name']}. "
                       f"Código interno de prueba {row['sku']}. Confirmar existencia y aplicación.")
        if row['application']:
            message += f" Aplicación: {row['application']}."
        row['quote_url'] = WHATSAPP_BASE + '?' + urlencode({'text': message})
        row['search_text'] = normalize_search(' '.join(
            row[k] for k in ('sku', 'name', 'description', 'application', 'category_label')
        ))
        records.append(row)
        sku_records.setdefault(row['sku'].casefold(), []).append(row)
    for group in sku_records.values():
        if len(group) > 1 and sum(not row['sku_pending'] for row in group) > 1:
            raise ReferenceDataError(f"Código repetido sin marcar por validar: {group[0]['sku']}.")
    return {'references': records, 'stock_mode': mode, 'currency': currency, 'prices_include_vat': vat}
