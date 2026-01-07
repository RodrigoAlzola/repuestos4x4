from django.core.management.base import BaseCommand
import pandas as pd
from store.models import Category, Product, Compatibility, Provider
import math
import requests
import time
from datetime import timedelta


def convertion(value):
    tarif = 1.23
    return math.ceil(value*tarif/100)*100

def verify_image_url(url, default_url="https://parts.terraintamer.com/images/DEFAULTPARTIMG.JPG"):
    """Verifica si la URL de la imagen es válida, si no retorna la por defecto"""
    if not url or url.strip() == "":
        return default_url
    
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 404:
            return default_url
        elif response.status_code == 200:
            return url
        else:
            return default_url
    except requests.exceptions.RequestException:
        return default_url

class Command(BaseCommand):
    help = 'Carga productos y compatibilidades desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_path',
            type=str, 
            default=r'C:\Users\rodri\NewProject\custcat.csv', 
            help='Ruta del archivo CSV')
        parser.add_argument(
            '--skip-image-check',
            action='store_true',
            help='Omite la verificación de imágenes (más rápido)'
        )

    def handle(self, *args, **kwargs):
        # ============ INICIAR TIMER ============
        start_time = time.time()
        self.stdout.write(self.style.WARNING(f'⏱️  Iniciando carga de productos...'))
        # =======================================

        # Obtener o crear el proveedor Terraintamers
        provider, created = Provider.objects.get_or_create(
            id=1,
            defaults={
                'name': 'Terraintamer',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Provider "{provider.name}" creado'))

        csv_path = kwargs['csv_path']
        skip_image_check = kwargs.get('skip_image_check', False)

        try:
            df = pd.read_csv(csv_path, encoding='latin-1')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al leer el CSV: {e}"))
            return
        
        # 1. Strip a los nombres de columnas
        df.columns = df.columns.str.strip()

        # 2. Strip a los valores de las celdas (solo columnas string)
        string_columns = df.select_dtypes(include=['object']).columns
        df[string_columns] = df[string_columns].apply(lambda col: col.str.strip())

        # 3. Reemplazar imágenes vacías
        default_image = "https://parts.terraintamer.com/images/DEFAULTPARTIMG.JPG"
        df['Foto'] = df['Foto'].replace("", default_image)

        # 4. FILTRAR productos sin stock
        # Convertir a numérico y llenar NaN con 0
        df['BR SOH'] = pd.to_numeric(df['BR SOH'], errors='coerce').fillna(0)
        df['MELSOH'] = pd.to_numeric(df['MELSOH'], errors='coerce').fillna(0)
        
        # Filtrar: mantener solo productos con stock local O internacional > 0
        df = df[(df['BR SOH'] > 0) | (df['MELSOH'] > 0)]
        
        # ============ NUEVO: FILTRAR PRODUCTOS EXISTENTES ============
        self.stdout.write(self.style.WARNING(f'🔍 Verificando productos existentes en la base de datos...'))
        
        # Obtener todos los part_numbers existentes en la BD
        productos = Product.objects.filter(provider=provider)
        print('Todos los productos', len(productos))

        existing_part_numbers = set(
            Product.objects.filter(provider=provider)
            .values_list('part_number', flat=True)
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'📊 Productos existentes en BD: {len(existing_part_numbers)}'
        ))
        
        # Filtrar productos que ya existen (solo crear nuevos)
        df = df[~df['Numero de parte'].astype(str).isin(existing_part_numbers)]
        productos_a_procesar = len(df)
        
        self.stdout.write(self.style.SUCCESS(
            f'✨ Filas nuevas a procesar: {productos_a_procesar}'
        ))

        creados = 0
        compatibles = 0
        compatibles_duplicados = 0
        imagenes_invalidas = 0
        
        # Cache para imágenes ya verificadas (optimización)
        verified_images = {}
        
        total_rows = len(df)

        new_products_preview = "0000"
        for index, row in df.iterrows():
            try:
                # Progress indicator cada 50 filas
                if index % 50 == 0:
                    elapsed = time.time() - start_time
                    self.stdout.write(f"⏱️  Procesando fila {index + 1}/{total_rows} - Tiempo transcurrido: {timedelta(seconds=int(elapsed))}")

                # Limpieza de columnas
                sku = str(row["Numero de parte"])
                brand = str(row["Marca"])
                model = str(row["Modelo"])
                serie = str(row["Serie"])

                if sku != new_products_preview:
                    new_products_preview = sku

                    name = row["Descripcion"]
                    part_number = row["Numero de parte"]
                    price = convertion(float(row["Minorista"]))
                    description = row["Descripcion"]
                    stock = int(row["BR SOH"]) if pd.notna(row["BR SOH"]) else 0
                    stock_international = int(row["MELSOH"]) if pd.notna(row["MELSOH"]) else 0
                    subcategory = row['Subgrupo'] if pd.notna(row['Subgrupo']) else ''
                    tariff_code = str(row["Tarrif Code"]) if pd.notna(row["Tarrif Code"]) else ""
                    weight = float(row["Peso (kg)"]) if pd.notna(row["Peso (kg)"]) else 0
                    length = float(row["Largo (cm)"]) if pd.notna(row["Largo (cm)"]) else 0
                    height = float(row["Alto (cm)"]) if pd.notna(row["Alto (cm)"]) else 0
                    width = float(row["Ancho (cm)"]) if pd.notna(row["Ancho (cm)"]) else 0
                    volume = float(row["Volumen (m3)"]) if pd.notna(row["Volumen (m3)"]) else 0
                    motor = str(row["Motor"]) if pd.notna(row["Motor"]) else ""
                    grupo = str(row["Grupo"])
                    image = row["Foto"]

                    # Verificar imagen usando caché (solo verifica URLs no vistas antes)
                    if not skip_image_check:
                        if image not in verified_images:
                            original_image = image
                            image = verify_image_url(image, default_image)
                            verified_images[original_image] = image
                            
                            if image == default_image and original_image != default_image:
                                imagenes_invalidas += 1
                        else:
                            image = verified_images[image]

                    # Obtener o crear categoría
                    category, _ = Category.objects.get_or_create(name=grupo)

                    # Crear nuevo producto
                    product = Product.objects.create(
                            part_number=part_number,
                            sku=sku,
                            name=name,
                            price=price,
                            category=category,
                            subcategory=subcategory,
                            description=description,
                            image=image,
                            is_sale=False,
                            sale_price=0,
                            stock=stock,
                            stock_international=stock_international,
                            tariff_code=tariff_code,
                            weight_kg=weight,
                            length_cm=length,
                            height_cm=height,
                            width_cm=width,
                            volume_m3=volume,
                            motor=motor,
                            provider=provider,
                        )
                    creados += 1

                # Crear compatibilidad SOLO si no existe
                compatibility, comp_created = Compatibility.objects.get_or_create(
                    product=product,
                    brand=brand,
                    model=model,
                    serie=serie
                )
                
                if comp_created:
                    compatibles += 1
                else:
                    compatibles_duplicados += 1
                    
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error al procesar la fila {index}: {e}"))
                continue

        # ============ FINALIZAR TIMER ============
        end_time = time.time()
        total_time = end_time - start_time
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n'
            f'✅ PROCESO COMPLETADO\n'
            f'{"="*60}\n'
            f'⏱️  Tiempo total: {timedelta(seconds=int(total_time))} ({total_time:.2f} segundos)\n'
            f'✨ Productos nuevos creados: {creados}\n'
            f'🔗 Compatibilidades nuevas: {compatibles}\n'
        ))