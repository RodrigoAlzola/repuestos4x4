from django.core.management.base import BaseCommand
import pandas as pd
from store.models import Category, Product, Compatibility

class Command(BaseCommand):
    help = 'Carga productos y compatibilidades desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Ruta del archivo CSV')

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv_path']

        try:
            df = pd.read_csv(csv_path, encoding='latin-1')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al leer el CSV: {e}"))
            return

        creados = 0
        compatibles = 0

        for index, row in df.head(20).iterrows():
            # Limpieza de columnas
            name = row["Descripcion                                                 "].strip()
            part_number = row["Numero de parte     "].strip()
            price = float(row["Minorista   "])
            description = row["Descripcion                                                 "].strip()
            image = row["Foto                                                                            "].strip()
            stock = str(row["Cant "]).strip()
            stock = int(stock) if stock.isdigit() else 0
            tariff_code = str(row["Tarrif Code    "]).strip()
            weight = float(row["Peso (kg)      "])
            length = float(row["Largo (cm)     "])
            height = float(row["Alto (cm)      "])
            width = float(row["Ancho (cm)     "])
            volume = float(row["Volumen (m3)   "])
            motor = str(row["Motor     "]).strip()
            brand = str(row["Marca               "]).strip()
            model = str(row["Modelo                        "]).strip()
            serie = str(row["Serie     "]).strip()
            grupo = str(row["Grupo                         "]).strip()

            # Obtener o crear categoría
            category, _ = Category.objects.get_or_create(name=grupo)

            # Obtener o crear producto
            product, created = Product.objects.get_or_create(
                part_number=part_number,
                defaults={
                    'name': name,
                    'price': price,
                    'category': category,
                    'description': description,
                    'image': image,
                    'is_sale': False,
                    'sale_price': 0,
                    'stock': stock,
                    'tariff_code': tariff_code,
                    'weight_kg': weight,
                    'length_cm': length,
                    'height_cm': height,
                    'width_cm': width,
                    'volume_m3': volume,
                    'motor': motor,
                }
            )

            if created:
                creados += 1

            # Crear compatibilidad (aunque el producto ya exista)
            Compatibility.objects.create(
                product=product,
                brand=brand,
                model=model,
                serie=serie
            )
            compatibles += 1

        self.stdout.write(self.style.SUCCESS(f'Se cargaron {creados} productos y {compatibles} compatibilidades.'))
