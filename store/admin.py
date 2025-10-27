from django.contrib import admin
from .models import Category, Customer, Product, Order, Profile, Compatibility
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
# admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Profile)

# Mix Profile info with User info
class ProfileInline(admin.StackedInline):
    model = Profile

class UserAdmin(admin.ModelAdmin):
    model = User
    field = ["username", "first_name", "last_name", "email"]
    inlines = [ProfileInline]

# Unregister the old way
admin.site.unregister(User)

# Re register the new way
admin.site.register(User, UserAdmin)


class CompatibilityInline(admin.TabularInline):
    model = Compatibility
    extra = 0

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'part_number', 'price', 'stock')
    inlines = [CompatibilityInline]

admin.site.register(Product, ProductAdmin)
