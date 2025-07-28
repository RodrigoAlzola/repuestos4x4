import pandas as pd
from store.models import Category

custcat = pd.read_csv(r'C:\Users\rodri\Downloads\custcat\custcat.csv', encoding='latin-1')

group = custcat['Grupo                         ']


print(len(custcat.columns))
print(custcat.shape)
print(custcat.columns)


print(pd.unique(group))
print(len(pd.unique(group)))


# Agrupar por 'Nombre' y contar cuántas marcas únicas hay para cada uno
marca_por_producto = custcat.groupby('Numero de parte     ')['Marca               '].nunique()

# Filtrar aquellos productos que tienen más de una marca distinta
productos_con_varias_marcas = marca_por_producto[marca_por_producto > 1]

print("Productos con más de una marca:")
print(productos_con_varias_marcas)
