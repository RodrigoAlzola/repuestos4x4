from django.contrib import admin
from django.urls import path, include
from .settings import base
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('cart/', include('cart.urls')),
    path('payment/', include('payment.urls')),
]


if base.DEBUG:
    urlpatterns += static(base.MEDIA_URL, document_root=base.MEDIA_ROOT)
    urlpatterns += static(base.STATIC_URL, document_root=base.STATIC_ROOT)