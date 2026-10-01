/* Accesos locales; sin cuentas, cambios de base de datos ni dependencias. */
(function () {
  'use strict';
  const STORAGE_KEY = '4x4max.vehicles.v1';
  const FIELDS = ['brand', 'model', 'serie', 'motor'];
  const LIMIT = 3;

  function normalize(value) {
    if (!value || typeof value !== 'object') return null;
    const vehicle = {};
    for (const field of FIELDS) {
      if (value[field] !== undefined && (typeof value[field] !== 'string' || value[field].length > 150)) return null;
      vehicle[field] = (value[field] || '').trim();
    }
    if (!vehicle.brand || !vehicle.model || (!vehicle.serie && vehicle.motor)) return null;
    return vehicle;
  }
  function key(vehicle) { return JSON.stringify(FIELDS.map(field => vehicle[field])); }
  function decode(raw) {
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      const seen = new Set();
      return parsed.map(normalize).filter(vehicle => {
        if (!vehicle || seen.has(key(vehicle))) return false;
        seen.add(key(vehicle));
        return true;
      }).slice(0, LIMIT);
    } catch (_) { return []; }
  }
  function remember(vehicles, value) {
    const vehicle = normalize(value);
    if (!vehicle) return vehicles;
    return [vehicle, ...vehicles.filter(item => key(item) !== key(vehicle))].slice(0, LIMIT);
  }
  // Exportar las reglas puras permite verificar límite y persistencia con Node.
  if (typeof module !== 'undefined' && module.exports) module.exports = {normalize, decode, remember, key};
  if (typeof document === 'undefined') return;

  const garage = document.querySelector('[data-vehicle-garage]');
  const configElement = document.getElementById('catalog-garage-data');
  if (!garage || !configElement) return;
  const list = garage.querySelector('[data-garage-list]');
  const status = garage.querySelector('[data-garage-status]');
  let vehicles = [];
  let storageAvailable = true;
  function read() {
    try { return decode(window.localStorage.getItem(STORAGE_KEY)); }
    catch (_) { storageAvailable = false; return []; }
  }
  function write() {
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(vehicles)); }
    catch (_) { storageAvailable = false; }
  }
  function render() {
    garage.hidden = false;
    list.replaceChildren();
    if (!vehicles.length) {
      const empty = document.createElement('p');
      empty.className = 'max-garage-empty';
      empty.textContent = 'Busca por marca y modelo: tu vehículo aparecerá aquí para la próxima vez.';
      list.append(empty);
    }
    vehicles.forEach(vehicle => {
      const label = FIELDS.map(field => vehicle[field]).filter(Boolean).join(' · ');
      const chip = document.createElement('div');
      chip.className = 'max-garage-chip';
      const link = document.createElement('a');
      // Los campos vacíos explícitos limpian la serie/motor de la selección anterior.
      link.href = `${garage.dataset.catalogUrl}?${new URLSearchParams(vehicle)}`;
      link.textContent = label;
      link.setAttribute('aria-label', `Ver repuestos para ${label}`);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `Quitar ${label} de tus vehículos`);
      remove.addEventListener('click', () => {
        vehicles = vehicles.filter(item => key(item) !== key(vehicle));
        write();
        render();
        if (storageAvailable) status.textContent = 'Vehículo quitado de tus accesos rápidos.';
        const next = list.querySelector('a');
        (next || garage.querySelector('h3')).focus();
      });
      chip.append(link, remove);
      list.append(chip);
    });
    garage.querySelector('h3').tabIndex = -1;
    status.textContent = storageAvailable ? '' : 'Este navegador no permite guardar vehículos. Los accesos durarán sólo en esta página.';
  }
  vehicles = read();
  try {
    const config = JSON.parse(configElement.textContent);
    const navigationType = window.performance?.getEntriesByType('navigation')[0]?.type;
    if (config.remember && navigationType !== 'reload' && navigationType !== 'back_forward' && normalize(config.vehicle)) {
      vehicles = remember(vehicles, config.vehicle);
      write();
    }
  } catch (_) { /* Un dato inválido no debe impedir buscar. */ }
  render();
  window.addEventListener('storage', event => {
    if (event.key === STORAGE_KEY || event.key === null) { vehicles = read(); render(); }
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) { vehicles = read(); render(); }
  });
})();
