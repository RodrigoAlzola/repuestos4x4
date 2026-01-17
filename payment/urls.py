from django.urls import path
from . import views

urlpatterns = [
    path('evaluate_payment', views.evaluate_payment, name='evaluate_payment'),
    path('payment_success/', views.payment_success, name='payment_success'),
    path('payment_failed', views.payment_failed, name='payment_failed'),
    path('checkout', views.checkout, name='checkout'),
    path('billing_info', views.billing_info, name='billing_info'),
    path('shipped_orders_dash', views.shipped_orders_dash, name='shipped_orders_dash'),
    path('confirmed_orders_dash', views.confirmed_orders_dash, name='confirmed_orders_dash'),
    path('pending_orders_dash', views.pending_orders_dash, name='pending_orders_dash'),
    path('order/<int:pk>', views.orders, name='orders'),
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('order-pending/<int:order_id>/', views.order_pending, name='order_pending'),
]