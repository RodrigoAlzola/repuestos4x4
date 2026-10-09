# Búsqueda de repuestos por código, sistema y tipo

El catálogo permite buscar una referencia desde la portada y afinar por familia, sistema y tipo de pieza, con etiquetas en español. Los filtros, el orden por precio, la vista lista/tarjetas y el tamaño de página (24/48) comparten el mismo formulario GET; no alteran el inventario ni el carro. Sin JavaScript se pueden aplicar con «Buscar».

Una coincidencia exacta en SKU o número de parte ignora el vehículo y los filtros anteriores para no ocultar la referencia, e incluye fichas sin stock con su estado real. Las opciones de piezas se desactivan mientras hay una referencia exacta; quitar su búsqueda vuelve a habilitarlas. La ficha conserva el vehículo para consultar compatibilidad, sin atribuir una aplicación inexistente.

La búsqueda admite palabras en cualquier orden y sin tildes, sinónimos español/inglés (retén/seal/oil seal, bomba de agua/water pump, etc.) y separadores habituales en referencias. El orden por precio usa el precio de oferta cuando corresponde y un desempate estable por ID.

`store/catalog_search.py` define las etiquetas y reglas. Los kits se clasifican primero; los retenes y juntas se separan cuando la descripción permite identificarlos. Los subgrupos mixtos sin descripción suficiente conservan «Juntas y retenes sin desglosar»; las piezas desconocidas aparecen como «Otros componentes», sin excluirlas del catálogo. Los nombres técnicos, códigos, imágenes y aplicaciones originales se conservan. No hay migraciones ni dependencias nuevas.

`update_products` sincroniza Grupo y Subgrupo también para referencias existentes cuando esas columnas llegan en el CSV; una cabecera ausente conserva el dato anterior. No se ejecuta una importación por publicar este cambio. El cálculo de precios y las reglas de stock del importador siguen siendo los existentes.

## Validación

- 38 pruebas Django de catálogo, búsqueda, clasificación, importación de metadatos, precios de oferta, filtros, aplicaciones, carro y página táctica.
- 3 pruebas JavaScript de vehículos recientes.
- Revisión de escritorio/móvil y controles automáticos de la interfaz.
- Prueba de volumen en una SQLite aislada con 16.200 productos sintéticos; no se publica ni se utiliza como inventario real. Los tiempos de ese equipo no garantizan tiempos en el servidor.

## Despliegue

Publicar el cambio completo, compilar estáticos mediante el proceso habitual y comprobar portada, catálogo, ficha, carro y página táctica. Conservar todos los ajustes, datos y credenciales del entorno. Para volver atrás, revertir el commit completo y desplegar de nuevo: no hay una migración que revertir.
