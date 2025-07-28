from django.core.management.base import BaseCommand
from store.models import Products
import csv

class Command(BaseCommand):
    help = 'Carga datos desde un archivo CSV'

    def handle(self, *args, **kwargs):
        with open('ruta/al/archivo.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                TuModelo.objects.create(
                    campo1=row['columna_csv'],
                    campo2=row['otra_columna'],
                )
        self.stdout.write(self.style.SUCCESS('Datos cargados exitosamente'))
