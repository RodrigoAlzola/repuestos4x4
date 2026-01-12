from django.contrib import admin
from django.urls import path, include
from .settings import base
from django.conf.urls.static import static
from debug_views import test_smtp_debug

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('cart/', include('cart.urls')),
    path('payment/', include('payment.urls')),
    path('workshop/', include('workshop.urls')),
    path('debug-smtp/', test_smtp_debug),
]


if base.DEBUG:
    urlpatterns += static(base.MEDIA_URL, document_root=base.MEDIA_ROOT)
    urlpatterns += static(base.STATIC_URL, document_root=base.STATIC_ROOT)