from store.models import Category, Product, Compatibility, Provider

def delete_product(product_id):
    try:
        products = Product.objects.filter(name__isnull=True) | Product.objects.filter(name='')
    except Product.DoesNotExist:
        print(f"Product with id {product_id} does not exist.")
        return

    print(products[0].price)
    # Delete related Compatibility records
    Compatibility.objects.filter(product=product).delete()

    # Finally, delete the Product itself
    product[0].delete()
    print(f"Product with id {product_id} and its related records have been deleted.")