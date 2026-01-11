from django.contrib import admin
from .models import Category, Customer, Product, Profile, Compatibility, Provider
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
# admin.site.register(Product)
# admin.site.register(Order)
admin.site.register(Profile)
admin.site.register(Provider)

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
    from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Búsqueda por SKU, nombre, part_number, etc.
    search_fields = ['sku', 'name', 'part_number', 'description']
    
    # Filtros en el panel lateral
    list_filter = ['category', 'provider', 'is_sale']
    
    # Campos a mostrar en la lista
    list_display = ['sku', 'name', 'category', 'price', 'stock', 'stock_international', 'provider']
    
    # Ordenamiento por defecto
    ordering = ['sku']
    
    # Paginación
    list_per_page = 50

