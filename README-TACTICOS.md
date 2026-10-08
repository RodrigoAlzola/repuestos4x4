# Repuestos para vehículos tácticos

Página independiente: `/repuestos-vehiculos-tacticos/`. Reúne 28 referencias, imágenes referenciales, búsqueda por código/nombre/aplicación, filtros de admisión/frenos y consulta por WhatsApp.

Lee exclusivamente `store/data/tactical_parts.json`. No consulta ni modifica Product, inventario, compatibilidades, pedidos, pagos o importaciones del catálogo. No requiere migraciones ni nuevas dependencias. Los precios se consultan y no se publican cantidades de stock simuladas. Las 13 propuestas de prueba mantienen sus códigos internos y aplicación por confirmar; las pastillas cerámicas tienen el número de parte pendiente.

El CSS se carga únicamente en esta página. Se heredan cabecera y pie actuales sin editar su plantilla, la portada ni el menú. Los archivos de fotos se sirven como estáticos del proyecto. Todas las fotos llevan la indicación de imagen referencial y no certifican diseño, material, medidas ni compatibilidad.

Para mantener los datos: editar el JSON, conservando ref como identificador interno (no se muestra). Las fotos están en ecom/static/images/tactical/. Las fuentes figuran en store/data/tactical_image_sources.csv. Ejecutar el flujo de despliegue habitual de Railway; se conserva la configuración efectiva de producción.

Verificación: `python manage.py test store.test_tactical_parts --settings=ecom.settings.local`. Las pruebas de la página prohíben consultas SQL y comprueban imágenes, búsqueda, filtros, escape de entradas y cotización sin carrito.

Para retirar la sección basta quitar la importación tactical_views y su ruta en store/urls.py. No hay datos del catálogo ni migraciones que revertir.
