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
    tarif = 1.00 #1.19

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
            '--new-csv',
            type=str, 
            default=r'C:\Users\rodri\NewProject\custcat.csv',
            help='Ruta del archivo CSV nuevo (default: custcad.csv)'
        )

        parser.add_argument(
            '--skip-image-check',
            action='store_true',
            help='Omite la verificación de imágenes (más rápido)'
        )

    def handle(self, *args, **kwargs):
        # ============ INICIAR TIMER ============
        start_time = time.time()
        self.stdout.write(self.style.WARNING(f'⏱️  Iniciando actualización de productos...'))
        # =======================================

        new_csv_path = kwargs['new_csv']
        skip_image_check = kwargs.get('skip_image_check', False)

        # Obtener o crear el proveedor Terraintamer
        provider, _ = Provider.objects.get_or_create(
            id=1,
            defaults={'name': 'Terraintamer'}
        )

        # Cargar dataframe
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

        # Eliminar duplicados
        df_nuevos_unique = df_new.drop_duplicates(subset=['Numero de parte'], keep='first')

        # Cargar la base de datos actual para comparar
        products = Product.objects.filter(provider=provider)

        # Crear un diccionario para búsqueda O(1) en lugar de queries O(n)
        products_dict = {p.part_number: p for p in Product.objects.filter(provider=provider)}

        products_to_update = []
        n = 0
        for index, row in df_nuevos_unique.iterrows():
            part_number = row['Numero de parte']
            
            # Búsqueda en diccionario (instantánea, sin query)
            product = products_dict.get(part_number)
            
            if product:
                product.price = convertion(float(row["Minorista"]))
                product.stock = int(row["BR SOH"]) if pd.notna(row["BR SOH"]) else 0
                product.stock_international = int(row["MELSOH"]) if pd.notna(row["MELSOH"]) else 0
                
                products_to_update.append(product)

                if part_number == "90116-08325K":
                    self.stdout.write(f"Debug: Actualizando {part_number} - Precio: {product.price}, Stock Local: {row['BR SOH']}, Stock Internacional: {product.stock_international}")

                
            # Progress indicator cada 50 filas
            if n % 500 == 0:
                elapsed = time.time() - start_time
                self.stdout.write(f"⏱️  Procesando fila {n + 1}/{len(df_nuevos_unique)} - Tiempo transcurrido: {timedelta(seconds=int(elapsed))}")

            n += 1

        # Una sola query para actualizar todos
        # Actualizar todo de una vez
        if products_to_update:
            Product.objects.bulk_update(
                products_to_update, 
                ['price', 'stock', 'stock_international'],
                batch_size=500  # Procesa en lotes de 500
            )
            
        # ============ FINALIZAR ============
        end_time = time.time()
        total_time = end_time - start_time

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'✅ ACTUALIZACIÓN COMPLETADA\n'
            f'{"="*70}\n'
            f'⏱️  Tiempo total: {timedelta(seconds=int(total_time))} ({total_time:.2f} segundos)\n'
        ))