const {test} = require('node:test');
const assert = require('node:assert/strict');
const {normalize, decode, remember} = require('../ecom/static/js/garage.js');
const vehicle = (model, serie = '') => ({brand: 'TOYOTA', model, serie, motor: ''});

test('persiste tres vehículos, mueve duplicados al inicio y reemplaza el más antiguo', () => {
  let saved = [];
  for (const model of ['HILUX', 'PRADO', 'LANDCRUISER']) saved = remember(saved, vehicle(model));
  saved = remember(saved, vehicle('HILUX'));
  assert.deepEqual(saved.map(item => item.model), ['HILUX', 'LANDCRUISER', 'PRADO']);
  saved = remember(saved, vehicle('FORTUNER'));
  assert.deepEqual(saved.map(item => item.model), ['FORTUNER', 'HILUX', 'LANDCRUISER']);
  assert.deepEqual(decode(JSON.stringify(saved)), saved);
});
test('distingue las series y motores de un mismo modelo', () => {
  let saved = remember([], vehicle('HILUX', 'GUN126'));
  saved = remember(saved, {...vehicle('HILUX', 'GUN126'), motor: '1GD'});
  saved = remember(saved, vehicle('HILUX', 'KUN26'));
  assert.equal(saved.length, 3);
});
test('recupera datos corruptos, elimina duplicados y rechaza selecciones incompletas', () => {
  assert.deepEqual(decode('invalid json'), []);
  assert.deepEqual(decode('{"brand":"TOYOTA"}'), []);
  assert.equal(normalize({brand: 'TOYOTA'}), null);
  assert.equal(normalize({...vehicle('HILUX'), motor: '1GD'}), null);
  assert.equal(normalize({...vehicle('HILUX'), model: 42}), null);
  assert.equal(decode(JSON.stringify([null, vehicle('HILUX'), vehicle('HILUX'), vehicle('PRADO')])).length, 2);
});
