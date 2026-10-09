from decimal import Decimal
from io import StringIO
from pathlib import Path
import csv
import tempfile
from urllib.parse import parse_qs, urlsplit
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from .models import Category, Product, Compatibility, Provider

class CatalogSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.front = Category.objects.create(name='DIFF FRONT')
        cls.cooling = Category.objects.create(name='COOLING')
        cls.provider = Provider.objects.create(id=1, name='Terrain Tamer')
        def add(code, name, group, subgroup, price=1000, stock=2):
            product = Product.objects.create(sku=code, part_number=code, name=name, category=group, subcategory=subgroup, price=price, stock=stock, provider=cls.provider)
            Compatibility.objects.create(product=product, brand='TOYOTA', model='LAND CRUISER', serie='FJ40')
            return product
        cls.seal = add('90311-40001', 'OIL SEAL PINION FRONT', cls.front, 'GASKETS & SEALS', 1500)
        cls.spanish = add('RET-002', 'RETÉN DE SEMIEJE DELANTERO', cls.front, 'GASKETS & SEALS', 2000)
        cls.gasket = add('GAS-001', 'GASKET DIFF FRONT', cls.front, 'GASKETS & SEALS', 500)
        cls.kit = add('KIT-001', 'OVERHAUL KIT WITH OIL SEAL', cls.front, 'OVERHAUL KIT', 9000)
        cls.pump = add('WP-001', 'WATER PUMP', cls.cooling, 'WATER PUMP', 7000)
        cls.radiator = add('RAD-001', 'RADIATOR', cls.cooling, 'RADIATOR', 10000)
        cls.no_stock = add('NOS-001', 'OIL SEAL REFERENCE', cls.front, 'SEALS', 3000, 0)
        cls.rear = add('REAR-001', 'OIL SEAL PINION REAR', Category.objects.create(name='DIFF REAR'), 'SEALS', 1700)
        Compatibility.objects.filter(product=cls.rear).update(serie='HZJ79')

    def listing(self, **params):
        return self.client.get(reverse('all_products'), params)

    def codes(self, response):
        return [p.sku for p in response.context['page_obj']]

    def test_home_has_global_search_from_first_screen(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'id="home-part-search"')
        self.assertContains(response, 'name="scope" value="all"')
        self.assertContains(response, 'Vehículos tácticos')

    def test_spanish_accent_and_english_search_share_matches(self):
        for query in ('retén', 'reten', 'retenes', 'oil seal'):
            with self.subTest(query=query):
                codes = self.codes(self.listing(search=query, scope='all'))
                self.assertIn(self.seal.sku, codes)
                self.assertIn(self.spanish.sku, codes)

    def test_multiple_terms_and_vehicle_narrow_to_front(self):
        response = self.listing(search='retén diferencial delantero', brand='TOYOTA', model='LAND CRUISER', serie='FJ40')
        self.assertIn(self.seal.sku, self.codes(response))
        self.assertNotIn(self.rear.sku, self.codes(response))
        self.assertNotIn(self.pump.sku, self.codes(response))

    def test_seals_do_not_include_gaskets_or_kits(self):
        response = self.listing(family='tren-motriz', system='DIFF FRONT', piece_type='retenes')
        self.assertEqual(set(self.codes(response)), {self.seal.sku, self.spanish.sku})
        labels = {row['label'] for row in response.context['type_options']}
        self.assertIn('Retenes', labels)
        self.assertIn('Juntas y empaquetaduras', labels)

    def test_cooling_can_select_only_water_pumps(self):
        response = self.listing(family='motor', system='COOLING', piece_type='bombas-agua')
        self.assertEqual(self.codes(response), [self.pump.sku])
        self.assertContains(response, 'Refrigeración')

    def test_exact_reference_ignores_old_vehicle_stock_and_piece_filters(self):
        self.listing(brand='TOYOTA', model='LAND CRUISER', serie='HZJ79')
        response = self.listing(search='NOS001', family='motor', system='COOLING', piece_type='radiadores', stock_type='nacional')
        self.assertTrue(response.context['exact_reference'])
        self.assertEqual(self.codes(response), [self.no_stock.sku])
        self.assertContains(response, 'Sin stock disponible')
        self.assertEqual(response.context['search_scope'], 'all')

    def test_code_prefix_before_names_and_partial_code_normalization(self):
        response = self.listing(search='9031140')
        self.assertEqual(self.codes(response), [self.seal.sku])

    def test_sale_price_sorting_and_stock_filter(self):
        self.spanish.is_sale = True
        self.spanish.sale_price = 750
        self.spanish.stock = 0
        self.spanish.stock_international = 3
        self.spanish.save()
        response = self.listing(system='DIFF FRONT', piece_type='retenes', sort='price')
        self.assertEqual(self.codes(response), [self.spanish.sku, self.seal.sku])
        self.assertEqual(self.codes(self.listing(system='DIFF FRONT', piece_type='retenes', sort='-price')), [self.seal.sku, self.spanish.sku])
        self.assertEqual(self.codes(self.listing(piece_type='retenes', stock_type='internacional')), [self.spanish.sku])

    def test_clear_piece_filters_keeps_vehicle_and_resets_page(self):
        response = self.listing(brand='TOYOTA', model='LAND CRUISER', serie='FJ40', family='tren-motriz', system='DIFF FRONT', piece_type='retenes', page=2)
        reset = parse_qs(urlsplit(response.context['reset_search_url']).query)
        self.assertEqual(reset['serie'], ['FJ40'])
        self.assertNotIn('page', reset)
        self.assertNotIn('piece_type', reset)
        chip = next(c for c in response.context['filter_chips'] if c['label'] == 'Diferencial delantero')
        self.assertNotIn('piece_type', parse_qs(urlsplit(chip['url']).query))

    def test_legacy_subcategory_links_remain_valid(self):
        response = self.listing(category='COOLING', subcategory='RADIATOR')
        self.assertEqual(self.codes(response), [self.radiator.sku])

    def test_safe_page_size_and_both_views(self):
        self.assertEqual(self.listing(per_page='999999').context['page_obj'].paginator.per_page, 24)
        self.assertEqual(self.listing(per_page='48').context['page_obj'].paginator.per_page, 48)
        self.assertContains(self.listing(view='grid'), 'max-search-grid')
        self.assertContains(self.listing(view='list'), 'max-part-row')

    def test_unknown_and_ambiguous_types_remain_accessible(self):
        product = Product.objects.create(sku='UNKNOWN', name='COMPONENT A', category=self.front, subcategory='GASKETS & SEALS', stock=1)
        response = self.listing(piece_type='juntas-retenes')
        self.assertIn(product.sku, self.codes(response))
        self.assertNotIn(product.sku, self.codes(self.listing(piece_type='retenes')))

    def test_seal_without_oil_is_found_but_sealed_alternator_is_not(self):
        seal = Product.objects.create(sku='SEAL1', name='DIFF PINION SEAL FRONT', category=self.front, subcategory='GASKETS & SEALS', stock=1)
        alternator = Product.objects.create(sku='ALT1', name='ALTERNATOR SEALED FOR MINING', category=self.cooling, stock=1)
        self.assertIn(seal.sku, self.codes(self.listing(piece_type='retenes')))
        self.assertIn(seal.sku, self.codes(self.listing(search='retén')))
        self.assertNotIn(alternator.sku, self.codes(self.listing(search='retén')))

    def test_search_query_is_escaped(self):
        response = self.listing(search='<script>alert(1)</script>')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_supplier_extra_systems_use_the_right_family_and_spanish_label(self):
        for category, family, label in [('SUSPENSION KITS', 'suspension', 'Kits de suspensión'), ('INTAKE MANIFOLD', 'motor', 'Admisión'), ('TRANSMISSION AUTOMATIC', 'transmision', 'Transmisión automática')]:
            product = Product.objects.create(sku=category, name='COMPONENT', category=Category.objects.create(name=category), stock=1)
            response = self.listing(family=family, system=category)
            self.assertIn(product.sku, self.codes(response))
            self.assertContains(response, label)

    def test_import_updates_classification_without_changing_reference(self):
        fields = ['Numero de parte', 'Minorista', 'BR SOH', 'MELSOH', 'Foto', 'Grupo', 'Subgrupo']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'catalog.csv'
            with path.open('w', newline='', encoding='latin-1') as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerow({'Numero de parte': self.seal.part_number, 'Minorista': 1000, 'BR SOH': 2, 'MELSOH': 0, 'Foto': '', 'Grupo': 'DIFF REAR', 'Subgrupo': ' OIL SEALS '})
            call_command('update_products', str(path), skip_image_check=True, stdout=StringIO())
        self.seal.refresh_from_db()
        self.assertEqual(self.seal.subcategory, 'OIL SEALS')
        self.assertEqual(self.seal.category.name, 'DIFF REAR')
        self.assertEqual(self.seal.sku, '90311-40001')
