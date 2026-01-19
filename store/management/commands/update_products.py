from django.core.management.base import BaseCommand
import pandas as pd
from store.models import Category, Product, Compatibility, Provider
import math
import requests
import time
from datetime import timedelta
from django.db.models import F


def convertion(value):
    """
    Convierte precio aplicando tarifa del 0% y redondea a .0 o .5
    """
    tarif = 1.19 #1.19

    # Aplicar tarifa y dividir por 1000 para generar decimales
    precio_base = value * tarif / 1000
    
    # Redondear a .0 o .5
    precio_redondeado = math.floor(precio_base * 2) / 2
    
    # Multiplicar de vuelta por 1000
    return precio_redondeado * 1000


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
    help = 'Actualiza productos comparando archivo nuevo vs antiguo'

    def add_arguments(self, parser):
        parser.add_argument(
        'csv_path',
        nargs='?',  # Opcional
        type=str,
        default=r'C:\Users\rodri\NewProject\custcat.csv',
        help='Ruta del archivo CSV (default: custcat.csv)'
        )

        parser.add_argument(
            '--skip-image-check',
            action='store_true',
            help='Omite la verificación de imágenes (más rápido)'
        )

    def handle(self, *args, **kwargs):
        # ============ INICIAR TIMER ============ #
        start_time = time.time()

        new_csv_path = kwargs['csv_path']
        skip_image_check = kwargs.get('skip_image_check', False)

        # Obtener o crear el proveedor Terraintamer
        provider, _ = Provider.objects.get_or_create(
            id=1,
            defaults={'name': 'Terraintamer'}
        )

        # ============ Procesar Dataframe ============ #
        df_new = pd.read_csv(new_csv_path, encoding='latin-1')
            
        # Limpiar columnas
        df_new.columns = df_new.columns.str.strip()

        # Convertir columnas numéricas
        df_new['BR SOH'] = pd.to_numeric(df_new['BR SOH'], errors='coerce').fillna(0)   
        df_new['MELSOH'] = pd.to_numeric(df_new['MELSOH'], errors='coerce').fillna(0)
        df_new['Minorista'] = pd.to_numeric(df_new['Minorista'], errors='coerce').fillna(0)

        # Limpiar espacios en columnas de texto
        string_columns = df_new.select_dtypes(include=['object']).columns
        df_new[string_columns] = df_new[string_columns].apply(lambda col: col.str.strip())

        # Imagen por defecto
        default_image = "https://parts.terraintamer.com/images/DEFAULTPARTIMG.JPG"
        df_new['Foto'] = df_new['Foto'].replace("", default_image)

        # Filtrar productos sin stock
        df_new = df_new[(df_new['BR SOH'] > 0) | (df_new['MELSOH'] > 0)]

        # Obtener la Base de Datos: crear un diccionario para búsqueda O(1) en lugar de queries O(n)
        products_dict = {p.part_number: p for p in Product.objects.filter(provider=provider)}

        # Filtrar productos que no existen (solo actualizar existentes)
        df_nuevos_unique = df_new[df_new['Numero de parte'].astype(str).isin(products_dict.keys())]
        # Eliminar duplicados
        df_nuevos_unique = df_new.drop_duplicates(subset=['Numero de parte'], keep='first')

        # Filtrar productos que ya existen (solo crear nuevos)
        df_new_products = df_new[~df_new['Numero de parte'].astype(str).isin(products_dict.keys())]


        # ============ Actualizar ============ #
        self.stdout.write(self.style.WARNING(f'⏱️  Iniciando actualización de productos...'))

        products_not_found = []
        products_to_update = []
        for index, row in df_nuevos_unique.iterrows():
            part_number = row['Numero de parte']
            
            # Búsqueda en diccionario (instantánea, sin query)
            product = products_dict.get(part_number)
            
            if product:
                product.price = convertion(float(row["Minorista"]))
                product.stock = int(row["BR SOH"]) if pd.notna(row["BR SOH"]) else 0
                product.stock_international = int(row["MELSOH"]) if pd.notna(row["MELSOH"]) else 0

                # Por esta vez actualizar subcatory y recomended_auantities
                # product.subcategory = row['Subgrupo'] if pd.notna(row['Subgrupo']) else ''
                # product.recommended_quantities = row['Cant'] if pd.notna(row['Cant']) else ''
                
                products_to_update.append(product)

            else:
                products_not_found.append(part_number)

        # Una sola query para actualizar todos
        # Actualizar todo de una vez
        if products_to_update:
            Product.objects.bulk_update(
                products_to_update, 
                ['price', 'stock', 'stock_international'],
                batch_size=500  # Procesa en lotes de 500
            )
        elapsed = time.time() - start_time
        self.stdout.write(self.style.WARNING(f'⏱️  Productos Actualizados - Tiempo transcurrido: {timedelta(seconds=int(elapsed))}'))


        # ============ Cargar nuevos productos ============ #
        self.stdout.write(self.style.WARNING(f'⏱️  Iniciando carga de nuevos productos: '))
        creados = 0
        verified_images = {}
        total_rows = len(df_new_products)
        new_products_preview = "0000"
        n = 0

        # Listas para bulk_create
        products_to_create = []
        compatibilities_to_create = []
        categories_to_create = {}
        product_map = {}  # Mapeo de SKU a producto para compatibilidades

        for index, row in df_new_products.iterrows():
            n = n + 1
            sku = str(row["Numero de parte"])
            try:
                # Progress indicator cada 50 filas
                if n % 50 == 0:
                    elapsed = time.time() - start_time
                    self.stdout.write(f"⏱️  Procesando fila {n}/{total_rows} - Tiempo transcurrido: {timedelta(seconds=int(elapsed))}")

                # Limpieza de columnas
                sku = str(row["Numero de parte"])
                brand = str(row["Marca"])
                model = str(row["Modelo"])
                serie = str(row["Serie"])

                # Primera vez que ve el producto
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
                    recommended_quantities = row['Cant'] if pd.notna(row['Cant']) else ''
                    image = row["Foto"]

                    # Verificar imagen usando caché
                    if not skip_image_check:
                        if image not in verified_images:
                            original_image = image
                            image = verify_image_url(image, default_image)
                            verified_images[original_image] = image
                        else:
                            image = verified_images[image]

                    # Guardar categoría para crear después
                    if grupo not in categories_to_create:
                        categories_to_create[grupo] = grupo

                    # Crear objeto producto (sin guardar aún)
                    product = Product(
                        part_number=part_number,
                        sku=sku,
                        name=name,
                        price=price,
                        category=None,  # Se asignará después
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
                        recommended_quantities=recommended_quantities
                    )
                    products_to_create.append(product)
                    product_map[sku] = {'product': product, 'grupo': grupo, 'compatibilities': []}
                    creados += 1

                # Guardar datos de compatibilidad para crear después
                product_map[sku]['compatibilities'].append({
                    'brand': brand,
                    'model': model,
                    'serie': serie
                })
                    
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error al procesar el producto {sku}: {e}"))
                continue

        # Bulk Create de Categorías 
        self.stdout.write(self.style.SUCCESS(f'📦 Creando categorías en bulk...'))
        existing_categories = {cat.name: cat for cat in Category.objects.filter(name__in=categories_to_create.keys())}
        new_categories = []
        for cat_name in categories_to_create.keys():
            if cat_name not in existing_categories:
                new_categories.append(Category(name=cat_name))

        if new_categories:
            Category.objects.bulk_create(new_categories, ignore_conflicts=True)
            # Actualizar el diccionario con las nuevas categorías
            all_categories = {cat.name: cat for cat in Category.objects.filter(name__in=categories_to_create.keys())}
        else:
            all_categories = existing_categories

        # Asignar categorías a productos
        for product in products_to_create:
            category_name = product_map[product.sku]['grupo']
            product.category = all_categories[category_name]

        # Bulk Create de Productos 
        self.stdout.write(self.style.SUCCESS(f'📦 Creando {len(products_to_create)} productos en bulk...'))
        if products_to_create:
            Product.objects.bulk_create(products_to_create, batch_size=500)
            self.stdout.write(self.style.SUCCESS(f'✅ {len(products_to_create)} productos creados'))

        # Bulk Create de Compatibilidades
        self.stdout.write(self.style.SUCCESS(f'📦 Preparando compatibilidades...'))
        # Obtener los productos recién creados con sus IDs
        created_products = Product.objects.filter(sku__in=product_map.keys())
        sku_to_product_db = {p.sku: p for p in created_products}

        # Obtener compatibilidades existentes para evitar duplicados
        existing_compatibilities = set(
            Compatibility.objects.filter(
                product__in=created_products
            ).values_list('product_id', 'brand', 'model', 'serie')
        )

        for sku, data in product_map.items():
            product_db = sku_to_product_db.get(sku)
            if product_db:
                for comp_data in data['compatibilities']:
                    # Verificar si ya existe
                    comp_tuple = (product_db.id, comp_data['brand'], comp_data['model'], comp_data['serie'])
                    if comp_tuple not in existing_compatibilities:
                        compatibilities_to_create.append(
                            Compatibility(
                                product=product_db,
                                brand=comp_data['brand'],
                                model=comp_data['model'],
                                serie=comp_data['serie']
                            )
                        )

        if compatibilities_to_create:
            self.stdout.write(self.style.SUCCESS(f'📦 Creando {len(compatibilities_to_create)} compatibilidades en bulk...'))
            Compatibility.objects.bulk_create(compatibilities_to_create, batch_size=1000, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f'✅ {len(compatibilities_to_create)} compatibilidades creadas'))

        self.stdout.write(self.style.SUCCESS(f'✅ Proceso completado: {creados} productos nuevos cargados'))


        # ============ FINALIZAR ============ #
        end_time = time.time()
        total_time = end_time - start_time

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'✅ ACTUALIZACIÓN COMPLETADA\n'
            f'{"="*70}\n'
            f'⏱️  Tiempo total: {timedelta(seconds=int(total_time))} ({total_time:.2f} segundos)\n'
            f'{"="*70}\n'
            f' - Productos no encontrado: {len(products_not_found)}\n'
            f' - Productos nuevos creados: {creados}\n'
        ))