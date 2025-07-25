from django.contrib import admin
from .models import ShippingAddress, Order, OrderItem
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
    readonly_fields = ["date_order"]
    fields = ["user", "full_name", "email", "phone", "shipping_address", "amount_pay", "date_order", "shipped", "date_shipped"]
    inlines = [OrderItemInline]

# Unregister old
admin.site.unregister(Order)

# Reregister 
admin.site.register(Order, OrderAdmin)