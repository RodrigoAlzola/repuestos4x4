"""
Carga o actualiza UN producto individual, copiando su imagen a los archivos
estaticos del proyecto (persistentes en Railway) y guardando la URL absoluta
en el campo Product.image (URLField).

Ejemplo:
    python manage.py load_single_product ^
        --sku "TT-1234" ^
        --name "Amortiguador delantero" ^
        --price 89990 ^
        --category "Suspension" ^
        --image "C:\\Users\\rodri\\Downloads\\foto.png" ^
        --stock 5
"""

import shutil
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from store.models import Category, Product, Provider

# Dominio canonico del sitio (ecom/middleware.py redirige el resto hacia aca).
DEFAULT_BASE_URL = 'https://4x4max.cl'

# Subcarpeta dentro de /static donde viven las fotos cargadas a mano.
STATIC_SUBDIR = 'products'

# Lado mayor maximo antes de redimensionar con --optimize.
MAX_SIDE = 1200

# Calidad JPEG al convertir fotos sin transparencia real.
JPEG_QUALITY = 85


class Command(BaseCommand):
    help = 'Carga o actualiza un producto individual con su imagen local (PNG/JPG).'

    def add_arguments(self, parser):
        # --- Identificacion ---
        parser.add_argument('--sku', type=str, default=None, help='SKU unico del producto')
        parser.add_argument('--part-number', type=str, default=None, help='Numero de parte')
        parser.add_argument('--name', type=str, default=None, help='Nombre del producto')

        # --- Imagen ---
        parser.add_argument(
            '--image',
            type=str,
            default=None,
            help='Ruta local al archivo de imagen (se copia a /static/products/)',
        )
        parser.add_argument(
            '--image-url',
            type=str,
            default=None,
            help='URL ya publicada, si la imagen esta hosteada en otra parte',
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default=DEFAULT_BASE_URL,
            help=f'Dominio para armar la URL absoluta (default: {DEFAULT_BASE_URL})',
        )
        parser.add_argument(
            '--optimize',
            action='store_true',
            help=(
                f'Redimensiona el lado mayor a {MAX_SIDE}px, comprime y convierte a JPEG '
                'si la imagen no usa transparencia real'
            ),
        )

        # --- Datos comerciales ---
        parser.add_argument('--price', type=str, default=None, help='Precio de venta')
        parser.add_argument('--category', type=str, default=None, help='Nombre de la categoria')
        parser.add_argument('--subcategory', type=str, default=None)
        parser.add_argument('--description', type=str, default=None)
        parser.add_argument('--motor', type=str, default=None)
        parser.add_argument('--provider', type=str, default=None, help='Nombre del proveedor existente')
        parser.add_argument('--stock', type=int, default=None)
        parser.add_argument('--tariff-code', type=str, default=None)

        # --- Logistica ---
        parser.add_argument('--weight-kg', type=str, default=None)
        parser.add_argument('--length-cm', type=str, default=None)
        parser.add_argument('--height-cm', type=str, default=None)
        parser.add_argument('--width-cm', type=str, default=None)

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra lo que haria sin tocar la base de datos ni copiar archivos',
        )

    # ------------------------------------------------------------------ #

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        lookup = self._build_lookup(options)
        image_url = self._resolve_image(options, lookup, dry_run)
        fields = self._build_fields(options, image_url, dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No se escribio nada en la base de datos.'))
            self.stdout.write(f'  Buscaria por: {lookup}')
            for key, value in fields.items():
                self.stdout.write(f'  {key}: {value}')
            return

        product, created = Product.objects.update_or_create(**lookup, defaults=fields)

        verbo = 'creado' if created else 'actualizado'
        estilo = self.style.SUCCESS if created else self.style.WARNING
        self.stdout.write(estilo(f'\nProducto {verbo} (id={product.pk}): {product}'))
        self.stdout.write(f'  Imagen: {product.image or "(sin imagen)"}')

        if options['image']:
            self._print_deploy_reminder()

    # ------------------------------------------------------------------ #

    def _build_lookup(self, options):
        """Define la clave de busqueda: sku > part_number > name."""
        if options['sku']:
            return {'sku': options['sku'].strip()}
        if options['part_number']:
            return {'part_number': options['part_number'].strip()}
        if options['name']:
            return {'name': options['name'].strip()}
        raise CommandError('Debes indicar al menos --sku, --part-number o --name para identificar el producto.')

    def _resolve_image(self, options, lookup, dry_run):
        """Devuelve la URL absoluta de la imagen, copiandola a /static/ si hace falta."""
        if options['image'] and options['image_url']:
            raise CommandError('Usa --image (archivo local) o --image-url (ya publicada), no ambos.')

        if options['image_url']:
            return options['image_url'].strip()

        if not options['image']:
            return None

        origen = Path(options['image']).expanduser()
        if not origen.is_file():
            raise CommandError(f'No existe el archivo de imagen: {origen}')

        destino_dir = Path(settings.STATICFILES_DIRS[0]) / STATIC_SUBDIR
        nombre = self._static_filename(options, lookup, origen, options['optimize'])
        destino = destino_dir / nombre

        if not dry_run:
            destino_dir.mkdir(parents=True, exist_ok=True)
            if options['optimize']:
                self._copy_optimized(origen, destino)
            else:
                shutil.copy2(origen, destino)
            peso_kb = destino.stat().st_size / 1024
            self.stdout.write(self.style.SUCCESS(f'Imagen copiada a {destino} ({peso_kb:.0f} KB)'))
            if peso_kb > 500:
                self.stdout.write(self.style.WARNING('  Pesa mas de 500 KB: considera volver a correr con --optimize.'))
        else:
            self.stdout.write(f'[DRY RUN] Copiaria {origen} -> {destino}')

        base = options['base_url'].rstrip('/')
        return f'{base}{settings.STATIC_URL if settings.STATIC_URL.startswith("/") else "/" + settings.STATIC_URL}{STATIC_SUBDIR}/{nombre}'

    def _static_filename(self, options, lookup, origen, optimize):
        """Nombre de archivo estable y seguro para URL, derivado del sku/nombre."""
        semilla = options['sku'] or options['part_number'] or options['name'] or list(lookup.values())[0]
        return f'{slugify(semilla)}{self._target_suffix(origen, optimize)}'

    def _target_suffix(self, origen, optimize):
        """Con --optimize, una foto sin transparencia real termina como JPEG."""
        if not optimize:
            return origen.suffix.lower()

        from PIL import Image

        with Image.open(origen) as img:
            return '.png' if self._has_transparency(img) else '.jpg'

    @staticmethod
    def _has_transparency(img):
        if img.mode in ('RGBA', 'LA'):
            return img.getchannel('A').getextrema()[0] < 255
        return 'transparency' in img.info

    def _copy_optimized(self, origen, destino):
        from PIL import Image

        with Image.open(origen) as img:
            img.load()

            lado_mayor = max(img.size)
            redimensionada = lado_mayor > MAX_SIDE
            if redimensionada:
                escala = MAX_SIDE / lado_mayor
                img = img.resize((round(img.width * escala), round(img.height * escala)), Image.LANCZOS)

            if destino.suffix == '.jpg':
                img = self._flatten(img)
                img.save(destino, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
            else:
                img.save(destino, optimize=True)

        # Re-comprimir un archivo que ya venia optimizado puede agrandarlo:
        # en ese caso conviene el original tal cual.
        if not redimensionada and self._same_format(origen, destino) and destino.stat().st_size >= origen.stat().st_size:
            shutil.copy2(origen, destino)
            self.stdout.write('  El original ya estaba mejor comprimido: se copio sin recomprimir.')

    @staticmethod
    def _same_format(origen, destino):
        """True si el original se puede usar tal cual bajo el nombre de destino."""
        jpeg = {'.jpg', '.jpeg'}
        if destino.suffix == '.jpg':
            return origen.suffix.lower() in jpeg
        return origen.suffix.lower() == destino.suffix

    @staticmethod
    def _flatten(img):
        """Aplana sobre blanco: JPEG no soporta canal alfa."""
        from PIL import Image

        if img.mode == 'RGB':
            return img
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGBA')
            fondo = Image.new('RGB', img.size, (255, 255, 255))
            fondo.paste(img, mask=img.getchannel('A'))
            return fondo
        return img.convert('RGB')

    def _build_fields(self, options, image_url, dry_run=False):
        """Arma el dict de campos a escribir, omitiendo los que no se pasaron."""
        fields = {}

        directos = {
            'name': 'name',
            'part_number': 'part_number',
            'subcategory': 'subcategory',
            'description': 'description',
            'motor': 'motor',
            'tariff_code': 'tariff_code',
        }
        for opcion, campo in directos.items():
            if options[opcion] is not None:
                fields[campo] = options[opcion].strip()

        decimales = ['price', 'weight_kg', 'length_cm', 'height_cm', 'width_cm']
        for campo in decimales:
            if options[campo] is not None:
                fields[campo] = self._to_decimal(campo, options[campo])

        if options['stock'] is not None:
            fields['stock'] = options['stock']

        if image_url is not None:
            fields['image'] = image_url

        if options['category']:
            nombre_categoria = options['category'].strip()
            if dry_run:
                categoria = Category.objects.filter(name=nombre_categoria).first()
                if categoria is None:
                    self.stdout.write(self.style.WARNING(f'[DRY RUN] Crearia la categoria: {nombre_categoria}'))
            else:
                categoria, creada = Category.objects.get_or_create(name=nombre_categoria)
                if creada:
                    self.stdout.write(self.style.WARNING(f'Categoria creada: {categoria.name}'))
            fields['category'] = categoria or nombre_categoria

        if options['provider']:
            proveedor = Provider.objects.filter(name__iexact=options['provider'].strip()).first()
            if proveedor is None:
                raise CommandError(f'No existe el proveedor "{options["provider"]}". Crealo primero en el admin.')
            fields['provider'] = proveedor

        if 'name' not in fields and not Product.objects.filter(**self._build_lookup(options)).exists():
            raise CommandError('Para crear un producto nuevo debes pasar --name.')

        return fields

    def _to_decimal(self, campo, valor):
        try:
            return Decimal(str(valor).replace(',', '.'))
        except InvalidOperation:
            raise CommandError(f'Valor invalido para --{campo.replace("_", "-")}: {valor}')

    def _print_deploy_reminder(self):
        self.stdout.write(self.style.MIGRATE_HEADING('\nFalta publicar la imagen:'))
        self.stdout.write(f'  git add ecom/static/{STATIC_SUBDIR}/')
        self.stdout.write('  git commit -m "Agrega imagen de producto"')
        self.stdout.write('  git push')
        self.stdout.write('\nHasta que Railway termine el deploy, la URL devolvera 404.')
