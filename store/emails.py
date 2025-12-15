from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from threading import Thread
import logging


logger = logging.getLogger(__name__)

def send_registration_email(user_email, full_name):
    """Envía email de bienvenida cuando se registra un usuario"""
    subject = '¡Bienvenido a 4x4MAX!'
    
    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px;">
                <h1 style="margin: 0;">¡Bienvenido a 4x4MAX!</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f8f9fa; margin-top: 20px; border-radius: 5px;">
                <h2 style="color: #333;">¡Hola {full_name}!</h2>
                <p style="color: #555; line-height: 1.6;">
                    Gracias por registrarte en <strong>4x4MAX</strong>.
                </p>
                <p style="color: #555; line-height: 1.6;">
                    Estamos emocionados de tenerte con nosotros. Ya puedes comenzar a explorar 
                    nuestro catálogo de repuestos 4x4.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://4x4max.cl/all_products/" 
                       style="background-color: #28a745; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver Catálogo
                    </a>
                </div>
                
                <p style="color: #555; line-height: 1.6;">
                    Si tienes alguna pregunta, no dudes en contactarnos respondiendo a este correo.
                </p>
            </div>
            
            <div style="margin-top: 20px; padding: 20px; text-align: center; color: #777; font-size: 0.9em;">
                <p style="margin: 5px 0;">Saludos,<br><strong>El equipo de 4x4MAX</strong></p>
                <p style="margin: 5px 0;">🌐 <a href="https://4x4max.cl" style="color: #28a745;">4x4max.cl</a></p>
            </div>
        </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )

        # logger.info(f"[EMAIL] ✅ Email enviado exitosamente a {user_email}")
        # print(f"✅ Email de bienvenida enviado a {user_email}")
    except Exception as e:
        # print(f"❌ Error enviando email de bienvenida a {user_email}: {e}")
        raise  # Re-lanza el error para que el thread lo capture


def send_registration_email_async(user_email, full_name):
    """Envía email de bienvenida de forma asíncrona"""
    def send_in_background():
        try:
            send_registration_email(user_email, full_name)
        except Exception as e:
            # El error ya se imprimió en send_registration_email
            pass
    
    email_thread = Thread(target=send_in_background)
    email_thread.daemon = True
    email_thread.start()
    logger.info("[EMAIL] Thread iniciado para envío asíncrono")

def send_order_confirmation_email(order):
    """Envía email de confirmación de compra"""
    logger.info(f"[ORDER EMAIL] Iniciando envío para orden #{order.id}")
    
    subject = f'Confirmación de Orden #{order.id} - 4x4MAX'
    
    # Obtener items de la orden
    items = order.orderitem_set.all()
    
    # Separar items locales e internacionales
    local_items = [item for item in items if not item.is_international]
    international_items = [item for item in items if item.is_international]
    
    # Construir lista de productos
    products_html = ""
    for item in items:
        badge = '<span style="background-color: #17a2b8; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.8em;">Internacional</span>' if item.is_international else ''
        products_html += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.product.name} {badge}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">{item.quantity}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">${item.price:,.0f}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">${item.get_total():,.0f}</td>
        </tr>
        """
    
    # Mensaje específico según tipo de orden
    delivery_message = ""
    if order.has_international_items and local_items:
        delivery_message = """
        <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
            <strong>⚠️ Orden Mixta (Local + Internacional):</strong><br>
            • Los productos locales llegarán en 3-5 días hábiles<br>
            • Los productos internacionales llegarán en 15-30 días hábiles<br>
            Recibirás notificaciones separadas para cada envío.
        </div>
        """
    elif order.has_international_items:
        delivery_message = """
        <div style="background-color: #d1ecf1; padding: 15px; border-left: 4px solid #17a2b8; margin: 20px 0;">
            <strong>🌎 Compra Internacional:</strong><br>
            Tus productos serán importados especialmente para ti.<br>
            Tiempo estimado de entrega: <strong>15-30 días hábiles</strong>
        </div>
        """
    else:
        delivery_message = """
        <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
            <strong>✓ Envío Local:</strong><br>
            Tiempo estimado de entrega: <strong>3-5 días hábiles</strong>
        </div>
        """
    
    # Workshop message
    workshop_message = ""
    if order.workshop:
        workshop_message = f"""
        <div style="background-color: #d1ecf1; padding: 15px; border-left: 4px solid #0c5460; margin: 20px 0;">
            <strong>🔧 Taller:</strong> {order.workshop.name}<br>
            <strong>Dirección:</strong> {order.workshop.address1}, {order.workshop.commune}, {order.workshop.city}<br>
            <strong>Teléfono:</strong> {order.workshop.phone}<br><br>
            <em>Por favor contacta al taller para agendar tu hora de instalación.</em>
        </div>
        """
    
    # Next steps
    next_steps_workshop = '<li>Contacta al taller para agendar tu instalación</li>' if order.workshop else ''
    next_steps_mixed = '<li>Los productos locales e internacionales pueden llegar en fechas diferentes</li>' if order.has_international_items and local_items else ''
    
    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #28a745; color: white; padding: 20px; text-align: center;">
                <h1>¡Gracias por tu compra!</h1>
            </div>
            
            <div style="padding: 20px;">
                <h2>Orden #{order.id}</h2>
                <p><strong>Fecha:</strong> {order.date_order.strftime('%d/%m/%Y %H:%M')}</p>
                
                {delivery_message}
                
                <h3>Información del Cliente</h3>
                <p>
                    <strong>Nombre:</strong> {order.full_name}<br>
                    <strong>Email:</strong> {order.email}<br>
                    <strong>Teléfono:</strong> {order.phone}
                </p>
                
                <h3>Dirección de Envío</h3>
                <p style="white-space: pre-line;">{order.shipping_address}</p>
                
                {workshop_message}
                
                <h3>Productos</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Producto</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Cantidad</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Precio</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
                        {products_html}
                    </tbody>
                    <tfoot>
                        <tr style="background-color: #f8f9fa; font-weight: bold;">
                            <td colspan="3" style="padding: 15px; text-align: right;">TOTAL:</td>
                            <td style="padding: 15px; text-align: right; color: #28a745; font-size: 1.2em;">${order.amount_pay:,.0f}</td>
                        </tr>
                    </tfoot>
                </table>
                
                <div style="margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 5px;">
                    <h4>Próximos Pasos:</h4>
                    <ol>
                        <li>Recibirás notificaciones cuando tu(s) pedido(s) sea(n) despachado(s)</li>
                        {next_steps_mixed}
                        {next_steps_workshop}
                        <li>Si tienes alguna pregunta, contáctanos respondiendo a este correo</li>
                    </ol>
                </div>
            </div>
            
            <div style="background-color: #343a40; color: white; padding: 20px; text-align: center; margin-top: 30px;">
                <p>Gracias por confiar en 4x4MAX</p>
                <p style="font-size: 0.9em;">🌐 <a href="https://4x4max.cl" style="color: #28a745;">4x4max.cl</a></p>
            </div>
        </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            html_message=html_message,
            fail_silently=False,
        )
        # logger.info(f"[ORDER EMAIL] ✅ Email enviado exitosamente a {order.email}")
        # print(f"✅ Email de confirmación enviado a {order.email} para orden #{order.id}")
    except Exception as e:
        # logger.error(f"[ORDER EMAIL] ❌ Error enviando email: {e}")
        # print(f"❌ Error enviando email de orden #{order.id}: {e}")
        raise


def send_order_confirmation_email_async(order):
    """Envía email de confirmación de orden de forma asíncrona"""
    def send_in_background():
        try:
            send_order_confirmation_email(order)
        except Exception as e:
            logger.error(f"[ORDER EMAIL ASYNC] Error en thread: {e}")
    
    email_thread = Thread(target=send_in_background)
    email_thread.daemon = True
    email_thread.start()
    # logger.info(f"[ORDER EMAIL] Thread iniciado para orden #{order.id}")