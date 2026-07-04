from django.core.management.base import BaseCommand
from payment.models import Order
from store.emails import send_order_confirmation_email, send_provider_order_notification

class Command(BaseCommand):
    help = 'Envía email de confirmación al cliente y al proveedor para una orden existente'

    def add_arguments(self, parser):
        parser.add_argument('order_id', type=str, help='Buy order de la orden (ej: 20260410-000048)')
        parser.add_argument(
            '--solo-cliente',
            action='store_true',
            help='Enviar solo al cliente',
        )
        parser.add_argument(
            '--solo-proveedor',
            action='store_true',
            help='Enviar solo al proveedor',
        )

    def handle(self, *args, **kwargs):
        order_id = kwargs['order_id']
        solo_cliente = kwargs['solo_cliente']
        solo_proveedor = kwargs['solo_proveedor']

        try:
            order = Order.objects.get(buy_order=order_id)
        except Order.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Orden #{order_id} no encontrada'))
            return

        self.stdout.write(f'📦 Procesando orden #{order.buy_order} - {order.full_name}')

        if not solo_proveedor:
            try:
                send_order_confirmation_email(order)
                self.stdout.write(self.style.SUCCESS(f'✅ Email enviado al cliente: {order.email}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error enviando al cliente: {e}'))

        if not solo_cliente:
            try:
                send_provider_order_notification(order)
                self.stdout.write(self.style.SUCCESS(f'✅ Emails enviados a los proveedores'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error enviando a proveedores: {e}'))