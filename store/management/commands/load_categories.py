import pandas as pd
from django.core.management.base import BaseCommand
from store.models import Category  # ajusta si tu modelo está en otra app

class Command(BaseCommand):
    help = 'Carga categorías únicas desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Ruta del archivo CSV')

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv_path']

        try:
            df = pd.read_csv(csv_path, encoding='latin-1')  # ajusta encoding si es necesario
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al leer el CSV: {e}"))
            return

        if 'Grupo                         ' not in df.columns:
            self.stderr.write(self.style.ERROR("El archivo debe tener una columna llamada 'Grupo                         '"))
            return

        nombres_unicos = df['Grupo                         '].dropna().unique()

        creadas = 0
        for nombre in nombres_unicos:
            nombre = nombre.strip()
            if not Category.objects.filter(name=nombre).exists():
                Category.objects.create(name=nombre)
                creadas += 1

        self.stdout.write(self.style.SUCCESS(f'Se cargaron {creadas} nuevas categorías.'))

