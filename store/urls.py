from django.urls import path
from . import views
from payment.views import test_smtp_debug

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/', views.register_user, name='register'),
    path('update_user/', views.update_user, name='update_user'),
    path('update_info/', views.update_info, name='update_info'),
    path('delete_address/<int:address_id>/', views.delete_shipping_address, name='delete_address'),
    path('set_default_address/<int:address_id>/', views.set_default_address, name='set_default_address'),
    path('edit_address/<int:address_id>/', views.edit_shipping_address, name='edit_address'),
    path('update_password/', views.update_password, name='update_password'),
    path('product/<int:pk>', views.product, name='product'),
    path('category/<str:foo>', views.category, name='category'),
    path('all_products/', views.all_products, name='all_products'),
    path('get-dynamic-filters/', views.get_dynamic_filters, name='get_dynamic_filters'),
    path('category_summary/', views.category_summary, name='category_summary'),
    path('search/', views.search, name='search'),
    path('debug-smtp/', test_smtp_debug),
]