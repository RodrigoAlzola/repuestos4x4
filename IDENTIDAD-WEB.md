# Tipografía y marca en la web

Referencia: `manual_4x4.pdf`, proporcionado por el usuario. La página de tipografía identifica Montserrat; la propuesta web adapta sus pesos y tamaños para lectura en pantalla.

## Propuesta aplicada

Montserrat normal en todos los textos. Pesos 400 para lectura, 500 para campos de formulario, 650 para nombres de producto y 700 para navegación, títulos, botones y precios. Se refuerzan el tamaño y el contraste manteniendo espacios amplios y una interfaz limpia.

Referencia de presencia visual: https://rhino4x4.co.za/. Se toma la jerarquía firme, navegación marcada y contraste de fotografía/texto; la fuente, paleta y logotipo siguen siendo los de 4x4MAX.

| Elemento | Escritorio | Móvil | Peso |
| --- | --- | --- | --- |
| Título principal | 40–52 px, según ancho | 38 px; 35 en móviles pequeños | 700 |
| Títulos de sección | 34 px | 29 px | 700 |
| Texto descriptivo | 17 px | 16 px | 400; portada 500 |
| Navegación | 15 px | 16 px en menú | 700; menú móvil 600 |
| Nombre de producto en tarjeta | 16 px | 14 px | 650 |
| SKU y disponibilidad | 13 px | 12 px | 400–500 |
| Botones | 14 px | 14 px | 700 |
| Título de ficha | 32 px | 28 px | 700 |

La navegación principal y los botones usan mayúsculas; el resto conserva su estilo de texto para mantener la lectura ligera. Las descripciones secundarias usan un gris más oscuro y la fotografía de portada tiene una capa de fondo más contrastada.

La fuente variable está en `ecom/static/fonts/montserrat/` con su licencia OFL. No depende de Google Fonts en tiempo de ejecución. Los ajustes están separados en `ecom/static/css/typography.css` para poder revisarlos sin cambiar los filtros del catálogo.

## Recursos de identidad

Carpeta compartida: https://drive.google.com/drive/folders/1tZitqbHAHaEARWfIt6QVP-jkCpIO46g3

Se revisaron las subcarpetas Archivos PNG, Archivos vectoriales y Manual y fuente. Esta última contiene el manual en PDF y AI; no se encontró allí un archivo de fuente. Montserrat se descargó del repositorio oficial de Google Fonts.

Logo completo positivo utilizado: https://drive.google.com/file/d/1mkjyG9qwUczRdE9emOOFzraKGpJxOZ4r/view

El logo se conserva sin alterar su composición, colores o proporción y se sirve como `ecom/static/images/logo-brand.png`.

Los acentos utilizan el hexadecimal rojo `#E01F1A` y el texto principal `#1F140F` del manual. Su tabla presenta una discrepancia entre el RGB y el hexadecimal del rojo; para CSS se usó el valor hexadecimal explícito.

Los respaldos del diseño anterior permanecen en `var/design-backup/` y `var/design-backup-rhino/` de la máquina de trabajo original. No se incluyen en esta rama; Git permite revisar y recuperar los cambios del repositorio.
