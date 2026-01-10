from django.urls import path
from . import views

urlpatterns = [
    path('evaluate_payment', views.evaluate_payment, name='evaluate_payment'),
    path('payment_success/', views.payment_success, name='payment_success'),
    path('payment_failed', views.payment_failed, name='payment_failed'),
    path('checkout', views.checkout, name='checkout'),
    path('billing_info', views.billing_info, name='billing_info'),
    path('shipped_dash', views.shipped_dash, name='shipped_dash'),
    path('not_shipped_dash', views.not_shipped_dash, name='not_shipped_dash'),
    path('order/<int:pk>', views.orders, name='orders'),
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
]