import time
from datetime import timedelta

from django.core.management.base import BaseCommand

from store.models import Product
from store.utils import verify_image_url, DEFAULT_PRODUCT_IMAGE


class Command(BaseCommand):
    help = 'Revisa el link de imagen (Foto) de todos los productos y reemplaza los rotos por la imagen default'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo reporta los links rotos, no modifica la base de datos'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        start_time = time.time()

        products = list(
            Product.objects.exclude(image=DEFAULT_PRODUCT_IMAGE)
            .exclude(image__isnull=True)
            .exclude(image='')
        )
        total = len(products)
        self.stdout.write(f'🔍 Productos con imagen propia a revisar: {total}')

        verified = {}
        broken = []
        products_to_update = []

        for i, product in enumerate(products, start=1):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                self.stdout.write(f'⏱️  Revisando {i}/{total} - Tiempo transcurrido: {timedelta(seconds=int(elapsed))}')

            url = product.image
            if url not in verified:
                verified[url] = verify_image_url(url)
            result = verified[url]

            if result != url:
                broken.append((product.part_number, url))
                if not dry_run:
                    product.image = result
                    products_to_update.append(product)

        if products_to_update:
            Product.objects.bulk_update(products_to_update, ['image'], batch_size=500)

        elapsed = time.time() - start_time
        self.stdout.write(self.style.WARNING(f'\n🔗 Links únicos revisados: {len(verified)}'))
        self.stdout.write(self.style.WARNING(f'❌ Links rotos encontrados: {len(broken)}'))

        for part_number, url in broken:
            self.stdout.write(f'   - {part_number}: {url}')

        if dry_run:
            self.stdout.write(self.style.WARNING('🧪 Dry-run: no se modificó la base de datos'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Productos actualizados con imagen default: {len(products_to_update)}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n'
            f'✅ REVISIÓN COMPLETADA\n'
            f'{"="*60}\n'
            f'⏱️  Tiempo total: {timedelta(seconds=int(elapsed))}\n'
            f' - Productos revisados: {total}\n'
            f' - Links rotos: {len(broken)}\n'
        ))
