from django.test import TestCase
from django.urls import reverse
from .models import Category, Product, Compatibility
from .catalog import filter_vehicle, family_counts


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='SUSPENSION FRONT')
        cls.product = Product.objects.create(name='Kit de suspensión', category=cls.category, sku='KIT1', part_number='TT-KIT1', price=1000, stock=3, motor='1GD')
        Compatibility.objects.create(product=cls.product, brand='TOYOTA', model='HILUX', serie='GUN126')
        # La segunda fila permite detectar combinaciones erróneas entre aplicaciones.
        Compatibility.objects.create(product=cls.product, brand='FORD', model='RANGER', serie='PX')
        cls.other = Product.objects.create(name='Repuesto especial', category=Category.objects.create(name='NUEVA CATEGORIA'), sku='OTHER', price=2000, stock_international=2)

    def test_vehicle_fields_must_match_same_application(self):
        self.assertFalse(filter_vehicle(Product.objects.all(), {'brand': 'TOYOTA', 'model': 'RANGER', 'serie': 'PX'}).exists())
        self.assertEqual(filter_vehicle(Product.objects.all(), {'brand': 'TOYOTA', 'model': 'HILUX', 'serie': 'GUN126'}).count(), 1)

    def test_motor_is_an_exact_filter(self):
        self.assertFalse(filter_vehicle(Product.objects.all(), {'motor': 'UNKNOWN'}).exists())
        self.assertEqual(filter_vehicle(Product.objects.all(), {'motor': '1GD'}).count(), 1)

    def test_family_mapping_keeps_unknown_categories(self):
        counts = family_counts(Product.objects.all())
        self.assertEqual(sum(f['count'] for f in counts), 2)
        self.assertEqual(next(f['count'] for f in counts if f['slug'] == 'otros'), 1)

    def test_vehicle_is_remembered_and_can_be_cleared(self):
        response = self.client.get(reverse('all_products'), {'brand': 'TOYOTA', 'model': 'HILUX', 'serie': 'GUN126'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertContains(self.client.get(reverse('home')), 'GUN126')
        self.assertEqual(self.client.get(reverse('all_products'), {'clear_vehicle': '1'}).context['page_obj'].paginator.count, 2)
        self.assertNotIn('catalog_vehicle', self.client.session)

    def test_invalid_vehicle_does_not_remember_old_selection(self):
        self.client.get(reverse('all_products'), {'brand': 'TOYOTA', 'model': 'HILUX'})
        response = self.client.get(reverse('all_products'), {'brand': 'TOYOTA', 'model': 'RANGER'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        self.assertNotIn('catalog_vehicle', self.client.session)

    def test_garage_remembers_only_explicit_valid_vehicle_searches(self):
        url = reverse('all_products')
        response = self.client.get(url, {'brand': 'TOYOTA', 'model': 'HILUX', 'serie': 'GUN126'})
        self.assertTrue(response.context['garage_config']['remember'])
        self.assertEqual(response.context['garage_config']['vehicle']['serie'], 'GUN126')
        self.assertFalse(self.client.get(reverse('home')).context['garage_config']['remember'])
        self.assertFalse(self.client.get(url, {'family': 'frenos'}).context['garage_config']['remember'])
        self.assertFalse(self.client.get(url, {'brand': 'TOYOTA', 'model': 'RANGER'}).context['garage_config']['remember'])
        self.assertFalse(self.client.get(url, {'brand': 'TOYOTA'}).context['garage_config']['remember'])

    def test_reset_clears_vehicle_and_all_search_filters(self):
        self.client.get(reverse('all_products'), {'brand': 'TOYOTA', 'model': 'HILUX', 'search': 'missing', 'family': 'motor'})
        response = self.client.get(reverse('all_products'), {'clear_vehicle': '1'})
        self.assertEqual(response.context['vehicle'], {})
        self.assertEqual(response.context['search_query'], '')
        self.assertEqual(response.context['selected_family'], '')
        self.assertEqual(response.context['page_obj'].paginator.count, 2)
        self.assertContains(response, 'Limpiar filtros')
        self.assertContains(response, 'data-vehicle-garage')

    def test_options_follow_vehicle_and_include_only_known_motors(self):
        data = self.client.get(reverse('vehicle_options'), {'brand': 'TOYOTA', 'model': 'HILUX', 'serie': 'GUN126'}).json()
        self.assertEqual(data['model'], ['HILUX'])
        self.assertEqual(data['serie'], ['GUN126'])
        self.assertEqual(data['motor'], ['1GD'])

    def test_search_finds_part_number_and_preserves_legacy_category(self):
        response = self.client.get(reverse('all_products'), {'search': 'TT-KIT1', 'category': 'SUSPENSION FRONT'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_visible_families_keep_search_filters_and_reset_pagination(self):
        from urllib.parse import urlsplit, parse_qs
        response = self.client.get(reverse('all_products'), {'brand': 'TOYOTA', 'model': 'HILUX', 'search': 'KIT1', 'stock_type': 'nacional', 'family': 'frenos', 'page': '2'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        self.assertEqual(response.context['family_total'], 1)
        suspension = next(item for item in response.context['families'] if item['slug'] == 'suspension')
        self.assertEqual(suspension['count'], 1)
        params = parse_qs(urlsplit(suspension['url']).query)
        self.assertEqual(params['brand'], ['TOYOTA'])
        self.assertEqual(params['search'], ['KIT1'])
        self.assertEqual(params['stock_type'], ['nacional'])
        self.assertEqual(params['family'], ['suspension'])
        self.assertNotIn('page', params)
        self.assertNotIn('family', parse_qs(urlsplit(response.context['all_families_url']).query))
        self.assertContains(response, 'Filtra por familia')
        self.assertEqual(len(response.context['families']), 8)

    def test_effective_sale_price_controls_sorting(self):
        self.other.is_sale = True
        self.other.sale_price = 500
        self.other.save()
        response = self.client.get(reverse('all_products'), {'sort': 'price'})
        self.assertEqual(response.context['page_obj'][0].pk, self.other.pk)

    def test_product_404_and_zero_specs_hidden(self):
        self.assertEqual(self.client.get(reverse('product', args=[999999])).status_code, 404)
        response = self.client.get(reverse('product', args=[self.other.pk]))
        self.assertContains(response, 'Aplicaciones del producto')
        self.assertNotContains(response, '<dt>Peso</dt>')
        self.assertNotContains(response, '<dt>Volumen</dt>')

    def test_product_application_status_and_cart(self):
        response = self.client.get(reverse('product', args=[self.product.pk]), {'brand': 'TOYOTA', 'model': 'HILUX', 'serie': 'GUN126'})
        self.assertContains(response, 'Aplicación registrada para tu selección')
        response = self.client.post(reverse('cart_add'), {'action': 'post', 'product_id': self.product.pk, 'product_quantity': 1})
        self.assertEqual(response.json()['quantity'], 1)
