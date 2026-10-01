# 4x4MAX — desarrollo local

La aplicación real está en esta carpeta (dentro de otra carpeta del mismo nombre). Es Django 5.2 y usa plantillas HTML, CSS y JavaScript. No requiere Node para ejecutarse.

## Abrir

Desde PowerShell en esta carpeta:

```powershell
.\start-local.ps1
```

Abre http://127.0.0.1:8000. Si la política de PowerShell bloquea el script, ejecuta directamente:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=ecom.settings.local --noreload
```

El servidor se detiene con Ctrl+C. Reinícialo después de modificar Python; recarga el navegador después de modificar HTML, CSS o JS.

## Preparar otra instalación

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
.\start-local.ps1
```

`start-local.ps1` copia `ecom/db.sqlite3` a `var/db.sqlite3` cuando no existe una base de trabajo. Los ajustes locales usan exclusivamente esa copia. El correo sale por consola; no hay credenciales de pago configuradas para este entorno. El checkout no está validado para operaciones de pago.

## Primera mejora implementada

Concepto comercial: repuestos y soluciones para un 4x4 más fuerte. Los textos generales no se vinculan a un proveedor; la marca se informa en las tarjetas y fichas según los datos del producto.

- Home centrada en vehículo, ocho familias comerciales en español y descubrimiento de familias existentes.
- Selector dependiente Marca → Modelo → Serie/chasis → Motor informado, con recuerdo de la selección en sesión y opción de limpieza.
- Botón «Limpiar filtros» junto al selector y en el catálogo. Reinicia la búsqueda y conserva los accesos rápidos.
- Hasta tres vehículos recientes en `localStorage`: se guardan al buscar una marca y modelo válidos, sin iniciar sesión. Un clic abre sus repuestos, incluyendo serie y motor elegidos. La cuarta selección sustituye la más antigua; × quita un acceso. Los accesos pertenecen al mismo navegador y dominio, no se sincronizan entre dispositivos ni del sitio local al publicado.
- Filtros de aplicación que exigen que marca, modelo y serie coincidan en la misma fila de compatibilidad.
- Catálogo con búsqueda por nombre, descripción, SKU y código de pieza; stock local/importación; orden por precio y paginación.
- Las ocho familias están visibles encima del catálogo, con cantidades dentro de los filtros actuales, selección resaltada y «Ver todos». Cambiar familia conserva vehículo y búsqueda y vuelve a la primera página. En móvil, los filtros adicionales se despliegan desde «Afinar búsqueda».
- Destacados variados por familia, con prioridad a kits y productos con imagen.
- Ficha con aplicaciones reales, estado de la selección, stock, carro y consulta de compatibilidad. Datos técnicos en cero ocultos.
- Diseño adaptable a escritorio y móvil; imágenes no disponibles tienen un marcador local.

## Datos y límites de esta copia

Al inicio del trabajo: 324 productos, 304 con stock local o internacional y 24 categorías con productos. Todos tienen el proveedor original `Terraintamers`. Es una instantánea local, no stock actualizado desde el servidor.

Las aplicaciones contienen marca, modelo y serie. No contienen año ni motor a nivel de aplicación. Sólo seis valores de motor distintos aparecen en los productos: por eso no se inventaron años ni correspondencias entre motor y chasis. Filtrar motor excluye productos que no lo informan; una aplicación registrada no reemplaza la revisión de versión y chasis.

Las ocho familias son una capa sobre las categorías existentes: no alteran los SKU, nombres técnicos, precios ni aplicaciones. Los nombres de productos siguen siendo los originales. Las imágenes de producto aún usan las URL del catálogo TT y requieren conexión. Las imágenes de portada ya venían en el proyecto.

La descarga utilizada para desarrollar el diseño no traía `.git`. Sus archivos originales se respaldaron en la máquina de trabajo; esos respaldos no se incluyen en esta rama. La rama integra las mejoras sobre el repositorio actual, sin publicar el sitio de producción.

## Archivos para continuar

- `store/catalog.py`: taxonomía y reglas de selección.
- `store/catalog_views.py`: vistas de home, catálogo, producto y opciones de vehículo.
- `store/templates/catalog_*.html`: nueva interfaz.
- `ecom/static/css/catalog.css` y `ecom/static/js/catalog.js`: estilos e interacciones.
- `ecom/settings/local.py`: entorno de desarrollo.

## Validar

```powershell
.\.venv\Scripts\python.exe manage.py check --settings=ecom.settings.local
.\.venv\Scripts\python.exe manage.py test store.test_catalog --settings=ecom.settings.local
```

Las pruebas usan una base temporal independiente. Cubren aplicaciones, motor, familias, sesión, búsqueda, orden por precio de oferta, ficha y agregado al carro.

## Identidad y tipografía

La interfaz utiliza Montserrat alojada localmente y el logo original de la carpeta compartida 4x4Max. La escala de tamaños, pesos y variantes está documentada en `IDENTIDAD-WEB.md`; las reglas viven en `ecom/static/css/typography.css`. El entorno local lee las plantillas en cada petición para que los cambios de HTML aparezcan al recargar.
