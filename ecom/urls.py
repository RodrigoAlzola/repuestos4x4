from django.contrib import admin
from django.urls import path, re_path, include
from django.contrib.sitemaps.views import sitemap
from django.views.static import serve
from store.sitemaps import ProductSitemap, StaticSitemap
from .settings import base
from django.conf.urls.static import static

sitemaps = {
    'products': ProductSitemap,
    'static': StaticSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('store.urls')),
    path('cart/', include('cart.urls')),
    path('payment/', include('payment.urls')),
    path('workshop/', include('workshop.urls')),
    # static() no sirve nada con DEBUG=False; los logos de talleres viven en /media/
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': base.MEDIA_ROOT}),
]

if base.DEBUG:
    urlpatterns += static(base.STATIC_URL, document_root=base.STATIC_ROOT)
