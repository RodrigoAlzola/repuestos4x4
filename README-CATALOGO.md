# Mejoras de catálogo 4x4MAX

Rama: `mejoras-catalogo-4x4max`. Base: `main`, commit `2e41189a8f9971581f6f6f67c1f17b6b112ee419` (29 de septiembre de 2026). Las mejoras se prepararon el 1 de octubre de 2026. Subir esta rama no publica por sí mismo la web: revisar y desplegar mediante el flujo del hosting.

## Cambios visibles

- Portada con el concepto «Repuestos y soluciones para un 4x4 más fuerte». Los textos generales permiten incorporar otras marcas; cada tarjeta y ficha conserva su proveedor real.
- Identidad 4x4MAX: logo original y Montserrat local, tamaños mayores, pesos firmes y mayor contraste. Detalles en `IDENTIDAD-WEB.md`; fuente y licencia en `ecom/static/fonts/montserrat/`.
- Navegación con «Nosotros» en escritorio y móvil, y «Regístrate» para visitantes. «Mi cuenta» en el menú móvil lleva al perfil si existe sesión y a login si no; en tablet se usa el menú desplegable para conservar espacio.
- Selector dependiente de marca, modelo, serie/chasis y motor informado. Botón «Limpiar filtros» en portada y catálogo.
- Tres vehículos recientes guardados en el navegador, sin cuenta: se recuerdan al buscar marca y modelo válidos. Un clic abre sus repuestos; × quita un acceso. Una cuarta selección sustituye la más antigua. Limpiar conserva los accesos. Los datos no se sincronizan entre navegadores, dominios ni dispositivos.
- Ocho familias visibles encima del catálogo con cantidades y «Ver todos». Conservan vehículo, texto y disponibilidad al cambiar familia y vuelven a la primera página. Las cantidades consideran los filtros actuales antes de restringir a una familia. Con repuestos: rojo suave; cero resultados: gris; seleccionada: fondo oscuro. En móvil, los filtros adicionales se despliegan en «Afinar búsqueda».
- Listado con búsqueda por nombre/descripción/SKU/código, stock local e internacional, precio de oferta y paginación. Ficha con aplicaciones reales, compatibilidad, carro y consulta; datos técnicos en cero ocultos.

## Archivos principales

`store/catalog.py` contiene las reglas y familias. `store/catalog_views.py` implementa las nuevas vistas y el endpoint de opciones. `store/urls.py` conecta portada, catálogo y ficha y agrega `vehicle-options/`. Las otras rutas y vistas siguen presentes. La interfaz está en `store/templates/catalog_*.html` y el archivo común `base.html`. Los estilos son `catalog.css` y `typography.css`; las interacciones son `catalog.js` y `garage.js`.

Logo, portada, pie, marcador y fuente se sirven desde `ecom/static/`; `collectstatic` incluye todo. Las imágenes originales de productos conservan sus URL. No hay cambios de modelos ni nuevas migraciones, importación de inventario, precios, pedidos o credenciales. No se subieron copias nuevas de SQLite, `.env`, el entorno Python o archivos temporales. Los comandos recientes de Rodrigo para cargar productos e imágenes permanecen en la rama.

## Verificar y publicar

Para revisar localmente, seguir `README-LOCAL.md`. Los ajustes `ecom.settings.local` son exclusivamente de desarrollo. Las pruebas usan una base temporal, sin modificar la copia del catálogo:

```sh
python manage.py check --settings=ecom.settings.local
python manage.py test store.test_catalog --settings=ecom.settings.local
node --test tests/garage.test.cjs
python tools/verify_static.py
```

Node sólo hace falta para esa prueba; no es una dependencia del sitio. Se verificaron 13 pruebas Django, 3 pruebas JavaScript y compilación de estáticos con manifiesto WhiteNoise, además de la revisión de escritorio/móvil.

Para la nube, revisar la rama y usar el proceso habitual de despliegue del repositorio; se conservaron `Procfile`, dependencias, WSGI y ajustes de producción. Configurar el módulo efectivo de producción (`DJANGO_SETTINGS_MODULE=ecom.settings.prod` si corresponde), preservar base de datos, secretos, correo, pagos y dominios actuales, y ejecutar:

```sh
python manage.py check --settings=ecom.settings.prod
python manage.py collectstatic --noinput --settings=ecom.settings.prod
python manage.py check --deploy --settings=ecom.settings.prod
```

El `prod.py` de la rama base mantiene `DEBUG=True`: corregirlo a `False` en la configuración efectiva antes de publicar. Los cambios de esta entrega no alteran ese archivo. En Django 5.2, si se desea WhiteNoise con manifiesto, integrar el backend `whitenoise.storage.CompressedManifestStaticFilesStorage` en `STORAGES['staticfiles']`, conservando las demás entradas. La opción antigua `STATICFILES_STORAGE` del proyecto no configura ese backend en Django 5.2. Mantener `STATIC_ROOT` separado de `ecom/static/` y realizar `collectstatic` durante el build/release. Referencias: [Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) y [WhiteNoise](https://whitenoise.readthedocs.io/en/stable/django.html).

Probar con datos actuales: filtros, ocho familias, guardar/quitar/abrir vehículos, limpiar, precios, ficha, carro, login y el flujo de compra del sitio. Los pagos de nube no se ejecutaron desde el entorno local. Para volver atrás, restaurar el commit de despliegue anterior, reconstruir estáticos y desplegarlo; no hay una nueva migración que revertir.

## Datos de compatibilidad

Marca, modelo y serie deben pertenecer a una misma aplicación registrada. No se inventan rangos de año. El motor filtra el campo informado del producto, no una relación motor/chasis inexistente. La aplicación registrada requiere confirmar versión y chasis antes de comprar. El listado muestra productos con stock local o internacional; las cifras locales de `README-LOCAL.md` son una instantánea, no el stock actual de producción.
