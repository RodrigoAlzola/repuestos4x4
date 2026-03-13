from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Category


class ProductSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Product.objects.filter(
            stock__gt=0
        ) | Product.objects.filter(
            stock_international__gt=0
        )

    def location(self, obj):
        return reverse('product', args=[obj.id])


class StaticSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 1.0

    def items(self):
        return ['home', 'all_products', 'about']

    def location(self, item):
        return reverse(item)