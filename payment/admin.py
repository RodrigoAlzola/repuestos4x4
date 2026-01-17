from django.contrib import admin
from .models import ShippingAddress, Order, OrderItem, Coupon, CouponUsage
from django.contrib.auth.models import User


# Register the model in the admin section
admin.site.register(ShippingAddress)
admin.site.register(Order)
admin.site.register(OrderItem)

# Create an Order Item Inline
class OrderItemInline(admin.StackedInline):
    model = OrderItem
    extra = 0

# Extend Order model
class OrderAdmin(admin.ModelAdmin):
    model = Order
    readonly_fields = ["date_order", "buy_order"]
    
    list_display = ['buy_order', 'full_name', 'email', 'payment_method', 'order_status', 'amount_pay', 'date_order', 'shipped']
    list_filter = ['payment_method', 'order_status', 'shipped', 'date_order']
    search_fields = ['buy_order', 'full_name', 'email', 'phone']
    
    fieldsets = (
        ('Estado de la Orden', {
            'fields': ('buy_order', 'date_order', 'payment_method', 'order_status')
        }),
        ('Información del Cliente', {
            'fields': ('user', 'full_name', 'email', 'phone', 'id_number')
        }),
        ('Información de Envío', {
            'fields': ('shipping_address', 'workshop', 'shipped', 'date_shipped', 'has_international_items')
        }),
        ('Información de Pago', {
            'fields': ('amount_pay', 'amount_before_discount', 'coupon', 'coupon_discount')
        }),
        ('Detalles de Transacción Transbank', {
            'fields': ('transaction_date', 'authorization_code', 'payment_type_code', 
                      'installments_number', 'card_number'),
            'classes': ('collapse',),
            'description': 'Estos campos solo se completan para pagos con Transbank'
        }),
    )
    
    inlines = [OrderItemInline]

# Unregister old
admin.site.unregister(Order)

# Reregister 
admin.site.register(Order, OrderAdmin)

# Cupones
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'times_used', 'max_uses', 'is_active', 'valid_from', 'valid_until']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'description']
    readonly_fields = ['times_used', 'created_at', 'updated_at']

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'user', 'order', 'used_at']
    list_filter = ['used_at', 'coupon']
    search_fields = ['coupon__code', 'user__username']