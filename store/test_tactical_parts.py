from urllib.parse import parse_qs, urlsplit

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from .tactical_parts import load_references


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class TacticalPageTests(SimpleTestCase):
    """SimpleTestCase prohíbe SQL: la hoja no depende del catálogo ni lo modifica."""

    def test_all_references_render_without_queries_or_fake_inventory(self):
        response = self.client.get(reverse('tactical_parts'))
        self.assertContains(response, 'Consultar precio', count=28)
        self.assertContains(response, '>Imagen referencial</span>', count=28)
        self.assertContains(response, 'Referencia de prueba', count=13)
        self.assertContains(response, 'Número de parte por validar')
        self.assertEqual(len(response.context['references']), 28)
        self.assertNotContains(response, 'demostración')
        self.assertNotContains(response, 'cart_add')
        self.assertTrue(all(row['stock'] is None for row in response.context['references']))

    def test_images_and_page_css_are_in_the_static_source(self):
        for row in load_references()['references']:
            with self.subTest(product=row['name']):
                self.assertIsNotNone(finders.find(row['image']))
        response = self.client.get(reverse('tactical_parts'))
        self.assertContains(response, '/static/css/tactical.css')

    def test_search_and_filters_use_the_special_references_only(self):
        url = reverse('tactical_parts')
        response = self.client.get(url, {'q': 'caliper', 'familia': 'frenos', 'brand': 'TOYOTA'})
        self.assertEqual(response.context['result_count'], 9)
        self.assertTrue(all(row['category'] == 'frenos' for row in response.context['references']))
        self.assertEqual(self.client.get(url, {'familia': 'admision'}).context['result_count'], 14)
        self.assertEqual(self.client.get(url, {'familia': 'frenos'}).context['result_count'], 14)
        self.assertEqual(self.client.get(url, {'q': 'BH35-KLTV'}).context['result_count'], 1)
        self.assertEqual(self.client.get(url, {'familia': 'invalid'}).context['result_count'], 28)

    def test_empty_results_and_query_escape(self):
        response = self.client.get(reverse('tactical_parts'), {'q': '<script>alert(1)</script>'})
        self.assertEqual(response.context['result_count'], 0)
        self.assertContains(response, 'No encontramos esa referencia')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_quote_omits_pending_code_and_identifies_proposals(self):
        rows = load_references()['references']
        pending = next(row for row in rows if row['sku_pending'])
        text = parse_qs(urlsplit(pending['quote_url']).query)['text'][0]
        self.assertIn(pending['name'], text)
        self.assertIn('por confirmar', text)
        self.assertNotIn('ADP-AFKLTV-35', text)
        demo = next(row for row in rows if row['is_demo'])
        text = parse_qs(urlsplit(demo['quote_url']).query)['text'][0]
        self.assertIn('Código interno de prueba', text)
        self.assertNotIn(demo['ref'], text)

    def test_page_is_read_only(self):
        self.assertEqual(self.client.post(reverse('tactical_parts')).status_code, 405)
