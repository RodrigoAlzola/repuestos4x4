document.querySelectorAll('[data-catalog-filters]').forEach(details => {
  const mobile = window.matchMedia('(max-width: 780px)');
  details.open = !mobile.matches;
  mobile.addEventListener('change', event => { details.open = !event.matches; });
});

document.querySelectorAll('img[data-fallback]').forEach(image => {
  const fallback = () => { if (image.dataset.fallback) { const source = image.dataset.fallback; delete image.dataset.fallback; image.src = source; } };
  image.addEventListener('error', fallback);
  if (image.complete && image.naturalWidth === 0) fallback();
});

document.querySelectorAll('[data-vehicle-fields]').forEach(group => {
  const fields = [...group.querySelectorAll('select')];
  const status = group.querySelector('[data-vehicle-status]');
  const placeholders = ['Elige marca', 'Elige modelo', 'Todas', 'Todos'];
  let controller;
  fields.forEach((field, index) => field.addEventListener('change', async () => {
    if (index === fields.length - 1) return;
    controller?.abort();
    controller = new AbortController();
    const signal = controller.signal;
    fields.slice(index + 1).forEach((select, offset) => { select.replaceChildren(new Option(placeholders[index + offset + 1], '')); select.disabled = true; });
    const params = new URLSearchParams();
    fields.forEach(select => { if (select.value) params.set(select.name, select.value); });
    status.textContent = 'Cargando aplicaciones…';
    try {
      const response = await fetch(`${group.dataset.endpoint}?${params}`, {signal});
      if (!response.ok) throw new Error('options');
      const options = await response.json();
      fields.slice(index + 1).forEach(select => {
        (options[select.name] || []).forEach(value => select.append(new Option(value, value)));
        const position = fields.indexOf(select);
        select.disabled = !fields[position - 1].value || !(options[select.name] || []).length;
      });
      status.textContent = index === 2 && !(options.motor || []).length ? 'Esta serie no tiene motor informado. Puedes buscar por serie.' : '';
    } catch (error) {
      if (error.name !== 'AbortError') status.textContent = 'No pudimos cargar las opciones. Vuelve a seleccionar o busca por marca.';
    }
  }));
});

document.querySelectorAll('[data-add-cart]').forEach(form => form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button');
  const status = form.querySelector('[data-cart-status]');
  button.disabled = true;
  status.textContent = 'Agregando…';
  try {
    const response = await fetch(form.getAttribute('action'), {method: 'POST', body: new FormData(form), headers: {'X-Requested-With': 'XMLHttpRequest'}});
    if (!response.ok) throw new Error('cart');
    const data = await response.json();
    if (data.error || data.quantity === undefined) throw new Error(data.error || 'cart');
    document.getElementById('cart_quantity').textContent = data.quantity;
    status.textContent = 'Producto agregado al carro.';
  } catch (error) { status.textContent = 'No pudimos agregar el producto. Revisa la cantidad e inténtalo de nuevo.'; }
  finally { button.disabled = false; }
}));
