from django.core.management.base import BaseCommand
import pandas as pd
from store.models import Category, Product, Compatibility, Provider
import math
import requests
import time
from datetime import timedelta
from django.db.models import F


def convertion(value):
    """Convierte precio aplicando tarifa del 19% y redondea"""
    tarif = 1.23
    return math.ceil(value * tarif / 100) * 100


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
        old_csv_path = kwargs['old_csv']
        skip_image_check = kwargs.get('skip_image_check', False)

        # Obtener o crear el proveedor Terraintamer
        provider, _ = Provider.objects.get_or_create(
            id=1,
            defaults={'name': 'Terraintamer'}
        )

        # ============ CARGAR ARCHIVOS CSV ============
        try:
            df_new = pd.read_csv(new_csv_path, encoding='latin-1')
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error al leer los archivos CSV: {e}"))
            return

        # Limpiar columnas
        df_new.columns = df_new.columns.str.strip()

        # Limpiar valores string
        for df in [df_new, df_old]:
            string_columns = df.select_dtypes(include=['object']).columns
            df[string_columns] = df[string_columns].apply(lambda col: col.str.strip())

        # Imagen por defecto
        default_image = "https://parts.terraintamer.com/images/DEFAULTPARTIMG.JPG"
        df_new['Foto'] = df_new['Foto'].replace("", default_image)
        df_old['Foto'] = df_old['Foto'].replace("", default_image)

        # Convertir columnas numéricas
        for df in [df_new, df_old]:
            df['BR SOH'] = pd.to_numeric(df['BR SOH'], errors='coerce').fillna(0)
            df['MELSOH'] = pd.to_numeric(df['MELSOH'], errors='coerce').fillna(0)
            df['Minorista'] = pd.to_numeric(df['Minorista'], errors='coerce').fillna(0)

        # ============ PASO 1: DETECTAR NUEVOS PRODUCTOS ============
        self.stdout.write(self.style.WARNING('\n🔍 PASO 1: Detectando nuevos productos...'))

        old_part_numbers = set(df_old['Numero de parte'].astype(str))
        new_part_numbers = set(df_new['Numero de parte'].astype(str))

        nuevos_productos_set = new_part_numbers - old_part_numbers

        self.stdout.write(self.style.SUCCESS(
            f'✨ Productos nuevos detectados en CSV: {len(nuevos_productos_set)}'
        ))

        # Filtrar solo productos nuevos
        df_nuevos = df_new[df_new['Numero de parte'].astype(str).isin(nuevos_productos_set)]

        # Filtrar productos sin stock (solo revisar la primera fila de cada part_number)
        df_nuevos_unique = df_nuevos.drop_duplicates(subset=['Numero de parte'], keep='first')
        df_nuevos_unique = df_nuevos_unique[(df_nuevos_unique['BR SOH'] > 0) | (df_nuevos_unique['MELSOH'] > 0)]

        productos_nuevos_creados = 0
        compatibilidades_nuevas = 0
        compatibilidades_duplicadas = 0

        # Cache para imágenes verificadas
        verified_images = {}

        # ============ CREAR NUEVOS PRODUCTOS ============
        if len(df_nuevos) > 0:
            self.stdout.write(self.style.WARNING(
                f'📦 Procesando {len(df_nuevos)} filas ({len(df_nuevos_unique)} productos únicos)...'
            ))
            
            # Diccionario para rastrear productos ya procesados en ESTE comando
            productos_procesados_en_comando = {}
            
            for index, row in df_nuevos.iterrows():
                try:
                    part_number = str(row["Numero de parte"])
                    
                    # ============ VERIFICAR SI EL PRODUCTO YA EXISTE ============
                    # Opción 1: Ya se creó en esta ejecución del comando
                    if part_number in productos_procesados_en_comando:
                        product = productos_procesados_en_comando[part_number]
                        
                    # Opción 2: Ya existe en la base de datos
                    elif Product.objects.filter(part_number=part_number, provider=provider).exists():
                        product = Product.objects.get(part_number=part_number, provider=provider)
                        productos_procesados_en_comando[part_number] = product
                        
                    # Opción 3: Es un producto nuevo, hay que crearlo
                    else:
                        if productos_nuevos_creados % 50 == 0 and productos_nuevos_creados > 0:
                            elapsed = time.time() - start_time
                            self.stdout.write(
                                f"⏱️  Creados {productos_nuevos_creados} productos - "
                                f"Tiempo: {timedelta(seconds=int(elapsed))}"
                            )

                        # Extraer datos
                        sku = str(row["Numero de parte"])
                        name = row["Descripcion"]
                        price = convertion(float(row["Minorista"]))
                        description = row["Descripcion"]
                        stock = int(row["BR SOH"])
                        stock_international = int(row["MELSOH"])
                        tariff_code = str(row["Tarrif Code"]) if pd.notna(row["Tarrif Code"]) else ""
                        weight = float(row["Peso (kg)"]) if pd.notna(row["Peso (kg)"]) else 0
                        length = float(row["Largo (cm)"]) if pd.notna(row["Largo (cm)"]) else 0
                        height = float(row["Alto (cm)"]) if pd.notna(row["Alto (cm)"]) else 0
                        width = float(row["Ancho (cm)"]) if pd.notna(row["Ancho (cm)"]) else 0
                        volume = float(row["Volumen (m3)"]) if pd.notna(row["Volumen (m3)"]) else 0
                        motor = str(row["Motor"]) if pd.notna(row["Motor"]) else ""
                        grupo = str(row["Grupo"])
                        image = row["Foto"]

                        # Verificar imagen
                        if not skip_image_check:
                            if image not in verified_images:
                                verified_images[image] = verify_image_url(image, default_image)
                            image = verified_images[image]

                        # Obtener o crear categoría
                        category, _ = Category.objects.get_or_create(name=grupo)

                        # Crear producto
                        product = Product.objects.create(
                            part_number=part_number,
                            sku=sku,
                            name=name,
                            price=price,
                            category=category,
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
                        productos_nuevos_creados += 1
                        productos_procesados_en_comando[part_number] = product

                    # ============ CREAR COMPATIBILIDAD (SIEMPRE) ============
                    brand = str(row["Marca"])
                    model = str(row["Modelo"])
                    serie = str(row["Serie"])
                    
                    # Crear compatibilidad SOLO si no existe
                    compatibility, comp_created = Compatibility.objects.get_or_create(
                        product=product,
                        brand=brand,
                        model=model,
                        serie=serie
                    )
                    
                    if comp_created:
                        compatibilidades_nuevas += 1
                    else:
                        compatibilidades_duplicadas += 1

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Error procesando fila {index} ({part_number}): {e}"))
                    import traceback
                    traceback.print_exc()
                    continue

            self.stdout.write(self.style.SUCCESS(
                f'✅ Productos nuevos creados: {productos_nuevos_creados}\n'
                f'✅ Compatibilidades nuevas: {compatibilidades_nuevas}\n'
                f'♻️  Compatibilidades duplicadas: {compatibilidades_duplicadas}'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('✅ No hay productos nuevos para crear'))

        # ============ PASO 2: COMPARAR CSV Y DETECTAR CAMBIOS EN PRECIO/STOCK ============
        self.stdout.write(self.style.WARNING('\n🔄 PASO 2: Comparando CSVs para detectar cambios en precio y stock...'))
        
        # Merge de dataframes por 'Numero de parte'
        df_old_indexed = df_old.set_index('Numero de parte')
        df_new_indexed = df_new.set_index('Numero de parte')
        
        # Solo productos que existen en ambos archivos (excluir nuevos)
        common_parts = old_part_numbers.intersection(new_part_numbers)
        
        self.stdout.write(f'📊 Productos comunes a comparar: {len(common_parts)}')
        
        # Listas para actualización bulk
        productos_a_actualizar_precio = []
        productos_a_actualizar_stock = []
        productos_a_actualizar_stock_int = []
        
        cambios_precio = 0
        cambios_stock = 0
        cambios_stock_int = 0
        
        for part_num in common_parts:
            try:
                old_row = df_old_indexed.loc[part_num]
                new_row = df_new_indexed.loc[part_num]
                
                # Comparar Minorista (precio)
                old_price = float(old_row['Minorista'])
                new_price = float(new_row['Minorista'])
                
                if old_price != new_price:
                    productos_a_actualizar_precio.append({
                        'part_number': str(part_num),
                        'new_price': convertion(new_price)
                    })
                    cambios_precio += 1
                
                # Comparar BR SOH (stock local)
                old_stock = int(old_row['BR SOH'])
                new_stock = int(new_row['BR SOH'])
                
                if old_stock != new_stock:
                    productos_a_actualizar_stock.append({
                        'part_number': str(part_num),
                        'new_stock': new_stock
                    })
                    cambios_stock += 1
                
                # Comparar MELSOH (stock internacional)
                old_stock_int = int(old_row['MELSOH'])
                new_stock_int = int(new_row['MELSOH'])
                
                if old_stock_int != new_stock_int:
                    productos_a_actualizar_stock_int.append({
                        'part_number': str(part_num),
                        'new_stock_int': new_stock_int
                    })
                    cambios_stock_int += 1
                    
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Error comparando producto {part_num}: {e}"))
                continue
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Cambios detectados:\n'
            f'   • Precios: {cambios_precio}\n'
            f'   • Stock local: {cambios_stock}\n'
            f'   • Stock internacional: {cambios_stock_int}'
        ))
        
        # ============ ACTUALIZAR EN BULK ============
        self.stdout.write(self.style.WARNING('💾 Aplicando actualizaciones en la base de datos...'))
        
        productos_actualizados = 0
        
        # Actualizar precios
        for item in productos_a_actualizar_precio:
            try:
                Product.objects.filter(
                    part_number=item['part_number'],
                    provider=provider
                ).update(price=item['new_price'])
                productos_actualizados += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Error actualizando precio de {item['part_number']}: {e}"))
        
        # Actualizar stock local
        for item in productos_a_actualizar_stock:
            try:
                Product.objects.filter(
                    part_number=item['part_number'],
                    provider=provider
                ).update(stock=item['new_stock'])
                productos_actualizados += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Error actualizando stock de {item['part_number']}: {e}"))
        
        # Actualizar stock internacional
        for item in productos_a_actualizar_stock_int:
            try:
                Product.objects.filter(
                    part_number=item['part_number'],
                    provider=provider
                ).update(stock_international=item['new_stock_int'])
                productos_actualizados += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Error actualizando stock internacional de {item['part_number']}: {e}"))

        # ============ PASO 3: COMPARAR Y ACTUALIZAR IMÁGENES ============
        if not skip_image_check:
            self.stdout.write(self.style.WARNING('\n🖼️  PASO 3: Comparando CSVs para detectar cambios en imágenes...'))
            
            productos_con_imagen_cambiada = []
            
            for part_num in common_parts:
                try:
                    old_row = df_old_indexed.loc[part_num]
                    new_row = df_new_indexed.loc[part_num]
                    
                    old_image = str(old_row['Foto']) if pd.notna(old_row['Foto']) else default_image
                    new_image = str(new_row['Foto']) if pd.notna(new_row['Foto']) else default_image
                    
                    # Si la imagen cambió en el CSV
                    if old_image != new_image:
                        productos_con_imagen_cambiada.append({
                            'part_number': str(part_num),
                            'new_image': new_image
                        })
                        
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Error comparando imagen de {part_num}: {e}"))
                    continue
            
            self.stdout.write(self.style.SUCCESS(
                f'✅ Imágenes cambiadas detectadas: {len(productos_con_imagen_cambiada)}'
            ))
            
            imagenes_actualizadas = 0
            imagenes_verificadas = 0
            imagenes_invalidas = 0
            
            if not skip_image_check and len(productos_con_imagen_cambiada) > 0:
                self.stdout.write(self.style.WARNING(
                    f'🔍 Verificando {len(productos_con_imagen_cambiada)} imágenes nuevas...'
                ))
                
                for item in productos_con_imagen_cambiada:
                    try:
                        new_image = item['new_image']
                        
                        # Verificar imagen (usar caché)
                        if new_image not in verified_images:
                            verified_images[new_image] = verify_image_url(new_image, default_image)
                            imagenes_verificadas += 1
                        
                        valid_image = verified_images[new_image]
                        
                        # Solo actualizar si la imagen es válida (no es la default)
                        if valid_image != default_image:
                            Product.objects.filter(
                                part_number=item['part_number'],
                                provider=provider
                            ).update(image=valid_image)
                            imagenes_actualizadas += 1
                        else:
                            imagenes_invalidas += 1
                            self.stdout.write(self.style.WARNING(
                                f'⚠️  Imagen inválida (404) para {item["part_number"]}, se mantiene la anterior'
                            ))
                        
                        # Progress cada 20 imágenes
                        if imagenes_verificadas % 20 == 0:
                            self.stdout.write(f'   Verificadas: {imagenes_verificadas}/{len(productos_con_imagen_cambiada)}')
                            
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"❌ Error actualizando imagen de {item['part_number']}: {e}"))
                        continue
        
        elif skip_image_check:
            self.stdout.write(self.style.WARNING('⏭️  Verificación de imágenes omitida (--skip-image-check)'))
        
        # ============ FINALIZAR ============
        end_time = time.time()
        total_time = end_time - start_time

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'✅ ACTUALIZACIÓN COMPLETADA\n'
            f'{"="*70}\n'
            f'⏱️  Tiempo total: {timedelta(seconds=int(total_time))} ({total_time:.2f} segundos)\n'
            f'\n📦 NUEVOS PRODUCTOS:\n'
            f'   • Detectados: {len(nuevos_productos_set)}\n'
            f'   • Creados: {productos_nuevos_creados}\n'
            f'   • Compatibilidades nuevas: {compatibilidades_nuevas}\n'
            f'\n🔄 CAMBIOS DETECTADOS (CSV vs CSV):\n'
            f'   • Precios modificados: {cambios_precio}\n'
            f'   • Stock local modificado: {cambios_stock}\n'
            f'   • Stock internacional modificado: {cambios_stock_int}\n'
            f'   • Total de actualizaciones aplicadas: {productos_actualizados}\n'
            f'\n🖼️  IMÁGENES:\n'
            f'   • Imágenes cambiadas en CSV: {len(productos_con_imagen_cambiada)}\n'
            f'   • Imágenes verificadas: {imagenes_verificadas}\n'
            f'   • Imágenes actualizadas en BD: {imagenes_actualizadas}\n'
            f'   • Imágenes inválidas (404): {imagenes_invalidas}\n'
            f'   • URLs únicas en caché: {len(verified_images)}\n'
            f'\n⚡ Velocidad: {len(df_new)/total_time if total_time > 0 else 0:.2f} productos/segundo\n'
            f'{"="*70}'
        ))