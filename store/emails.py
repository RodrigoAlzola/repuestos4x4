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
                    Si tienes alguna pregunta, no dudes en contactarnos respondiendo a este correo contacto@4x4max.cl.
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
    
    subject = f'✅ Confirmación de Orden #{order.buy_order} - 4x4MAX'
    
    # Obtener items de la orden
    items = order.orderitem_set.all()
    
    # Separar items locales e internacionales
    local_items = [item for item in items if not item.is_international]
    international_items = [item for item in items if item.is_international]
    
    # Construir lista de productos
    products_html = ""
    for item in items:
        badge = '<span style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; letter-spacing: 0.5px;">🌎 INTERNACIONAL</span>' if item.is_international else ''
        products_html += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 16px 12px;">
                <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">{item.product.name}</div>
                <div style="font-size: 0.85em; color: #6b7280;">PN: {item.product.part_number}</div>
                {f'<div style="margin-top: 6px;">{badge}</div>' if item.is_international else ''}
            </td>
            <td style="padding: 16px 12px; text-align: center;">
                <span style="background-color: #f3f4f6; padding: 6px 16px; border-radius: 8px; font-weight: 600; color: #374151;">
                    {item.quantity}
                </span>
            </td>
            <td style="padding: 16px 12px; text-align: right; color: #6b7280; font-size: 0.95em;">
                ${item.price:,.0f}
            </td>
            <td style="padding: 16px 12px; text-align: right; font-weight: 600; color: #1f2937; font-size: 1.05em;">
                ${item.get_total():,.0f}
            </td>
        </tr>
        """
    
    # Información del cupón
    coupon_section = ""
    if order.coupon:
        coupon_section = f"""
        <div style="background: linear-gradient(to right, #fee2e2, #fecaca); padding: 20px; border-left: 5px solid #dc2626; margin: 25px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(220, 38, 38, 0.15);">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 2em; margin-right: 12px;">🎉</span>
                <strong style="font-size: 1.15em; color: #991b1b;">¡Descuento Aplicado!</strong>
            </div>
            <div style="color: #7f1d1d; line-height: 1.8;">
                Cupón <strong style="background-color: white; padding: 3px 8px; border-radius: 6px; color: #dc2626;">{order.coupon.code}</strong> aplicado exitosamente<br>
                {f'• {order.coupon.description}<br>' if order.coupon.description else ''}
                • Ahorraste: <strong>${order.coupon_discount:,.0f} CLP</strong>
            </div>
        </div>
        """
    
    # Mensaje específico según tipo de orden
    delivery_message = ""
    if order.has_international_items and local_items:
        delivery_message = """
        <div style="background: linear-gradient(to right, #fef3c7, #fde68a); padding: 20px; border-left: 5px solid #f59e0b; margin: 25px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 2em; margin-right: 12px;">📦</span>
                <strong style="font-size: 1.15em; color: #92400e;">Orden Mixta (Local + Internacional)</strong>
            </div>
            <div style="color: #78350f; line-height: 1.8;">
                • <strong>Productos locales:</strong> 5-10 días hábiles<br>
                • <strong>Productos internacionales:</strong> 15-30 días hábiles<br>
                • Recibirás notificaciones separadas para cada envío
            </div>
        </div>
        """
    elif order.has_international_items:
        delivery_message = """
        <div style="background: linear-gradient(to right, #fee2e2, #fecaca); padding: 20px; border-left: 5px solid #dc2626; margin: 25px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(220, 38, 38, 0.15);">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 2em; margin-right: 12px;">🌎</span>
                <strong style="font-size: 1.15em; color: #991b1b;">Compra Internacional</strong>
            </div>
            <div style="color: #7f1d1d; line-height: 1.8;">
                Tus productos serán importados especialmente para ti<br>
                • Tiempo estimado de entrega: <strong>15-30 días hábiles</strong>
            </div>
        </div>
        """
    else:
        delivery_message = """
        <div style="background: linear-gradient(to right, #dbeafe, #bfdbfe); padding: 20px; border-left: 5px solid #1f2937; margin: 25px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(31, 41, 55, 0.15);">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 2em; margin-right: 12px;">✓</span>
                <strong style="font-size: 1.15em; color: #1f2937;">Envío Local</strong>
            </div>
            <div style="color: #374151; line-height: 1.8;">
                Tiempo estimado de entrega: <strong>5-10 días hábiles</strong>
            </div>
        </div>
        """
    
    # Workshop message
    workshop_message = ""
    if order.workshop:
        workshop_message = f"""
        <div style="background: linear-gradient(to right, #fef3c7, #fde68a); padding: 20px; border-left: 5px solid #f59e0b; margin: 25px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 2em; margin-right: 12px;">🔧</span>
                <strong style="font-size: 1.15em; color: #92400e;">Instalación en Taller</strong>
            </div>
            <div style="color: #78350f; line-height: 1.8;">
                <strong>Taller:</strong> {order.workshop.name}<br>
                <strong>Dirección:</strong> {order.workshop.address1}, {order.workshop.commune}, {order.workshop.city}<br>
                <strong>Teléfono:</strong> {order.workshop.phone}<br>
            </div>
            <div style="margin-top: 10px; padding: 10px; background-color: rgba(255, 255, 255, 0.6); border-radius: 8px;">
                <small style="color: #92400e; font-size: 0.9em;">
                    💡 Por favor contacta al taller para agendar tu hora de instalación.
                </small>
            </div>
        </div>
        """
    
    # Next steps
    next_steps_workshop = '<li style="margin-bottom: 10px;"><strong>Contacta al taller</strong> para agendar tu instalación</li>' if order.workshop else ''
    next_steps_mixed = '<li style="margin-bottom: 10px;">Los productos <strong>locales e internacionales</strong> pueden llegar en fechas diferentes</li>' if order.has_international_items and local_items else ''
    
    # Footer de la tabla con cupón
    table_footer = ""
    if order.coupon:
        table_footer = f"""
        <tr style="background-color: #f9fafb;">
            <td colspan="3" style="padding: 14px 12px; text-align: right; font-weight: 500; color: #4b5563;">
                Subtotal:
            </td>
            <td style="padding: 14px 12px; text-align: right; font-weight: 600; color: #1f2937; font-size: 1.05em;">
                ${order.amount_before_discount:,.0f}
            </td>
        </tr>
        <tr style="background: linear-gradient(to right, #fee2e2, #fecaca);">
            <td colspan="3" style="padding: 14px 12px; text-align: right; font-weight: 600; color: #dc2626;">
                🎟️ Descuento ({order.coupon.code}):
            </td>
            <td style="padding: 14px 12px; text-align: right; font-weight: 700; color: #dc2626; font-size: 1.05em;">
                -${order.coupon_discount:,.0f}
            </td>
        </tr>
        <tr style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);">
            <td colspan="3" style="padding: 18px 12px; text-align: right; font-weight: 700; color: white; font-size: 1.1em;">
                TOTAL PAGADO:
            </td>
            <td style="padding: 18px 12px; text-align: right; color: white; font-size: 1.4em; font-weight: 700;">
                ${order.amount_pay:,.0f}
            </td>
        </tr>
        """
    else:
        table_footer = f"""
        <tr style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);">
            <td colspan="3" style="padding: 18px 12px; text-align: right; font-weight: 700; color: white; font-size: 1.1em;">
                TOTAL PAGADO:
            </td>
            <td style="padding: 18px 12px; text-align: right; color: white; font-size: 1.4em; font-weight: 700;">
                ${order.amount_pay:,.0f}
            </td>
        </tr>
        """
    
    html_message = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
            <div style="max-width: 700px; margin: 0 auto; background-color: white;">
                
                <!-- Header con colores de marca (Negro y Rojo) -->
                <div style="background: white; padding: 40px 30px; text-align: center; position: relative;">
                   
                    <!-- Logo -->
                    <img src="https://4x4max.cl/static/images/logo.png" alt="4X4MAX" style="height: 80px; margin-bottom: 20px;">
                    
                    <div style="font-size: 3em; margin-bottom: 10px;">✅</div>
                    <h1 style="color: white; margin: 0; font-size: 2em; font-weight: 700; letter-spacing: -0.5px;">
                        ¡Gracias por tu compra!
                    </h1>
                
                <div style="padding: 35px 30px;">
                    
                    <!-- Saludo -->
                    <h2 style="color: #1f2937; font-size: 1.5em; margin: 0 0 15px 0; font-weight: 600;">
                        Hola {order.full_name} 👋
                    </h2>
                    <p style="color: #4b5563; line-height: 1.6; font-size: 1.05em; margin: 0 0 30px 0;">
                        Tu pedido ha sido procesado exitosamente y está siendo preparado para envío.
                    </p>
                    
                    <!-- Card de información de orden -->
                    <div style="background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%); padding: 25px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); border-left: 4px solid #dc2626;">
                        <div style="display: grid; gap: 12px;">
                            <div style="display: flex; align-items: center; padding: 8px 0;">
                                <span style="font-size: 1.3em; margin-right: 12px;">📋</span>
                                <div>
                                    <div style="color: #6b7280; font-size: 0.85em; margin-bottom: 2px;">Número de Orden</div>
                                    <div style="color: #dc2626; font-weight: 700; font-size: 1.15em;">#{order.buy_order}</div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; padding: 8px 0;">
                                <span style="font-size: 1.3em; margin-right: 12px;">📅</span>
                                <div>
                                    <div style="color: #6b7280; font-size: 0.85em; margin-bottom: 2px;">Fecha</div>
                                    <div style="color: #1f2937; font-weight: 600;">{order.date_order.strftime('%d/%m/%Y %H:%M')}</div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; padding: 8px 0;">
                                <span style="font-size: 1.3em; margin-right: 12px;">✅</span>
                                <div>
                                    <div style="color: #6b7280; font-size: 0.85em; margin-bottom: 2px;">Estado de Pago</div>
                                    <div>
                                        <span style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 0.9em; display: inline-block;">
                                            ✓ PAGADO
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    {delivery_message}
                    
                    {coupon_section}
                    
                    {workshop_message}
                    
                    <!-- Información del Cliente -->
                    <div style="margin: 30px 0;">
                        <h3 style="color: #1f2937; font-size: 1.3em; margin: 0 0 18px 0; font-weight: 600; border-bottom: 2px solid #dc2626; padding-bottom: 10px;">
                            👤 Información del Cliente
                        </h3>
                        <div style="background-color: #f9fafb; padding: 20px; border-radius: 10px; border-left: 4px solid #1f2937;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; color: #6b7280; width: 120px; font-weight: 500;">Nombre:</td>
                                    <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{order.full_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #6b7280; font-weight: 500;">Email:</td>
                                    <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{order.email}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #6b7280; font-weight: 500;">Teléfono:</td>
                                    <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{order.phone}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #6b7280; font-weight: 500;">RUT:</td>
                                    <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{order.id_number}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                    
                    <!-- Dirección de Envío -->
                    <div style="margin: 30px 0;">
                        <h3 style="color: #1f2937; font-size: 1.3em; margin: 0 0 18px 0; font-weight: 600; border-bottom: 2px solid #dc2626; padding-bottom: 10px;">
                            📍 Dirección de Envío
                        </h3>
                        <div style="background-color: #f9fafb; padding: 20px; border-radius: 10px; border-left: 4px solid #dc2626;">
                            <p style="margin: 0; white-space: pre-line; color: #1f2937; line-height: 1.8; font-weight: 500;">
                                {order.shipping_address}
                            </p>
                        </div>
                    </div>
                    
                    <!-- Productos -->
                    <div style="margin: 30px 0;">
                        <h3 style="color: #1f2937; font-size: 1.3em; margin: 0 0 18px 0; font-weight: 600; border-bottom: 2px solid #dc2626; padding-bottom: 10px;">
                            📦 Resumen de tu Pedido
                        </h3>
                        <div style="overflow-x: auto; border-radius: 12px; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);">
                            <table style="width: 100%; border-collapse: collapse; background-color: white;">
                                <thead>
                                    <tr style="background: linear-gradient(135deg, #1f2937 0%, #111827 100%);">
                                        <th style="padding: 16px 12px; text-align: left; color: white; font-weight: 600; font-size: 0.95em; letter-spacing: 0.3px;">
                                            PRODUCTO
                                        </th>
                                        <th style="padding: 16px 12px; text-align: center; color: white; font-weight: 600; font-size: 0.95em; letter-spacing: 0.3px;">
                                            CANT.
                                        </th>
                                        <th style="padding: 16px 12px; text-align: right; color: white; font-weight: 600; font-size: 0.95em; letter-spacing: 0.3px;">
                                            PRECIO UNIT.
                                        </th>
                                        <th style="padding: 16px 12px; text-align: right; color: white; font-weight: 600; font-size: 0.95em; letter-spacing: 0.3px;">
                                            SUBTOTAL
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {products_html}
                                </tbody>
                                <tfoot>
                                    {table_footer}
                                </tfoot>
                            </table>
                        </div>
                    </div>
                    
                    <!-- Próximos pasos -->
                    <div style="margin: 35px 0; padding: 25px; background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%); border-left: 5px solid #1f2937; border-radius: 12px;">
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <span style="font-size: 2em; margin-right: 12px;">📝</span>
                            <h4 style="margin: 0; color: #1f2937; font-size: 1.2em; font-weight: 700;">
                                Próximos Pasos
                            </h4>
                        </div>
                        <ol style="margin: 0; padding-left: 20px; color: #4b5563; line-height: 1.9; font-size: 1.02em;">
                            <li style="margin-bottom: 10px;">
                                <strong>Recibirás notificaciones</strong> cuando tu pedido sea despachado
                            </li>
                            {next_steps_mixed}
                            {next_steps_workshop}
                            <li style="margin-bottom: 10px;">
                                Para solicitar <strong>factura</strong>, envíanos un correo con el número de orden
                            </li>
                            <li style="margin-bottom: 0;">
                                Si tienes dudas, contáctanos en <strong>contacto@4x4max.cl</strong>
                            </li>
                        </ol>
                    </div>
                    
                    <!-- Contacto -->
                    <div style="margin: 30px 0; padding: 20px; background: linear-gradient(to right, #fee2e2, #fecaca); border-radius: 12px; text-align: center; border: 2px solid #dc2626;">
                        <p style="margin: 0; color: #991b1b; font-size: 1.05em; line-height: 1.6;">
                            <strong style="font-size: 1.15em; color: #7f1d1d;">📞 ¿Necesitas ayuda?</strong><br>
                            Contáctanos en <a href="mailto:contacto@4x4max.cl" style="color: #dc2626; text-decoration: none; font-weight: 600;">contacto@4x4max.cl</a>
                        </p>
                    </div>
                    
                </div>
                
                <!-- Footer con colores de marca -->
                <div style="background: white; padding: 40px 30px; text-align: center; position: relative;">
                    
                    <div style="margin-bottom: 15px;">
                        <span style="font-size: 2.5em;">🚙</span>
                    </div>
                    <p style="color: #9ca3af; margin: 10px 0; font-size: 1.05em; font-weight: 500;">
                        Gracias por confiar en
                    </p>
                    <h2 style="color: white; margin: 8px 0; font-size: 1.8em; font-weight: 700; letter-spacing: 1px;">
                        <span style="color: #dc2626;">4x4 MAX</span>
                    </h2>
                    <p style="margin: 15px 0 0 0;">
                        <a href="https://4x4max.cl" style="color: #dc2626; text-decoration: none; font-weight: 600; font-size: 1.05em;">
                            🌐 4x4max.cl
                        </a>
                    </p>
                </div>
                
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
        logger.info(f"[ORDER EMAIL] ✅ Email enviado a {order.email}")
    except Exception as e:
        logger.error(f"[ORDER EMAIL] ❌ Error enviando email: {e}")
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


def send_provider_order_notification(order):
    """Envía email a cada proveedor con sus productos de la orden"""
    logger.info(f"[PROVIDER EMAIL] Iniciando envío para orden #{order.id}")
    
    # Agrupar items por proveedor
    items_by_provider = {}
    for item in order.orderitem_set.all():
        provider = item.product.provider
        if provider:
            if provider not in items_by_provider:
                items_by_provider[provider] = []
            items_by_provider[provider].append(item)
    
    # Enviar email a cada proveedor
    for provider, items in items_by_provider.items():
        if not provider.email:
            logger.warning(f"[PROVIDER EMAIL] Proveedor {provider.name} no tiene email configurado")
            continue
        
        # Calcular subtotal del proveedor (ANTES de descuento)
        provider_subtotal = sum(item.get_total() for item in items)
        
        # Calcular proporción del descuento que corresponde a este proveedor
        provider_discount = 0
        provider_total = provider_subtotal
        
        if order.coupon and order.amount_before_discount > 0:
            # Proporción de productos de este proveedor vs total
            proportion = provider_subtotal / order.amount_before_discount
            provider_discount = order.coupon_discount * float(proportion)
            provider_total = float(provider_subtotal) - provider_discount
        
        # Construir lista de productos del proveedor
        products_html = ""
        for item in items:
            badge = '<span style="background-color: #17a2b8; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.8em;">Internacional</span>' if item.is_international else ''
            products_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.product.part_number}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.product.name} {badge}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">{item.quantity}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">${item.price:,.0f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">${item.get_total():,.0f}</td>
            </tr>
            """
        
        # Footer de la tabla con cupón
        table_footer = ""
        if order.coupon and provider_discount > 0:
            table_footer = f"""
            <tr>
                <td colspan="4" style="padding: 10px; text-align: right;">Subtotal de tus productos:</td>
                <td style="padding: 10px; text-align: right;">${provider_subtotal:,.0f}</td>
            </tr>
            <tr style="background-color: #d4edda;">
                <td colspan="4" style="padding: 10px; text-align: right; color: #28a745;">
                    Descuento proporcional ({order.coupon.code}):
                </td>
                <td style="padding: 10px; text-align: right; color: #28a745;">
                    -${provider_discount:,.0f}
                </td>
            </tr>
            <tr style="background-color: #f8f9fa; font-weight: bold;">
                <td colspan="4" style="padding: 15px; text-align: right;">TOTAL DE TUS PRODUCTOS:</td>
                <td style="padding: 15px; text-align: right; color: #007bff; font-size: 1.2em;">${provider_total:,.0f}</td>
            </tr>
            """
        else:
            table_footer = f"""
            <tr style="background-color: #f8f9fa; font-weight: bold;">
                <td colspan="4" style="padding: 15px; text-align: right;">TOTAL DE TUS PRODUCTOS:</td>
                <td style="padding: 15px; text-align: right; color: #007bff; font-size: 1.2em;">${provider_total:,.0f}</td>
            </tr>
            """
        
        # Información del cupón
        coupon_info = ""
        if order.coupon:
            coupon_info = f"""
            <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; border-radius: 5px;">
                <strong>🎟️ Información de Descuento:</strong><br>
                El cliente usó el cupón <strong>{order.coupon.code}</strong><br>
                • Descuento total de la orden: <strong>${order.coupon_discount:,.0f}</strong><br>
                • Descuento aplicado a tus productos: <strong>${provider_discount:,.0f}</strong><br>
                <small style="color: #856404;">El descuento se distribuyó proporcionalmente entre todos los proveedores según el valor de sus productos.</small>
            </div>
            """
        
        # Resumen de la orden
        order_summary = f"""
        <div style="background-color: #e7f3ff; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0; border-radius: 5px;">
            <strong>📊 Resumen de la Orden Completa:</strong><br>
            • Subtotal antes de descuento: <strong>${order.amount_before_discount:,.0f}</strong><br>
            {f'• Descuento total aplicado: <strong>${order.coupon_discount:,.0f}</strong><br>' if order.coupon else ''}
            • <strong>Total pagado por el cliente: ${order.amount_pay:,.0f}</strong><br>
            <small style="color: #004085;">Tu parte corresponde a ${provider_total:,.0f} del total de la orden.</small>
        </div>
        """
        
        subject = f'Nueva Orden #{order.buy_order} - 4x4MAX'
        
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
                <div style="background-color: #007bff; color: white; padding: 20px; text-align: center;">
                    <h1>Nueva Orden de Compra</h1>
                </div>
                
                <div style="padding: 20px;">
                    <h2>Hola {provider.name},</h2>
                    <p>Se ha generado una nueva orden que incluye productos de tu catálogo.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>Número de Orden:</strong> #{order.buy_order}</p>
                        <p style="margin: 5px 0;"><strong>Fecha:</strong> {order.date_order.strftime('%d/%m/%Y %H:%M')}</p>
                        <p style="margin: 5px 0;"><strong>Estado de Pago:</strong> <span style="color: #28a745;">✓ PAGADO</span></p>
                    </div>
                    
                    {coupon_info}
                    
                    {order_summary}
                    
                    <h3>Información del Cliente</h3>
                    <p>
                        <strong>Nombre:</strong> {order.full_name}<br>
                        <strong>Email:</strong> {order.email}<br>
                        <strong>Teléfono:</strong> {order.phone}<br>
                        <strong>Rut:</strong> {order.id_number}
                    </p>
                    
                    <h3>Dirección de Envío</h3>
                    <p style="white-space: pre-line; background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{order.shipping_address}</p>
                    
                    <h3>Productos Solicitados</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #007bff; color: white;">
                                <th style="padding: 10px; text-align: left;">Part Number</th>
                                <th style="padding: 10px; text-align: left;">Producto</th>
                                <th style="padding: 10px; text-align: center;">Cantidad</th>
                                <th style="padding: 10px; text-align: right;">Precio Unit.</th>
                                <th style="padding: 10px; text-align: right;">Subtotal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {products_html}
                        </tbody>
                        <tfoot>
                            {table_footer}
                        </tfoot>
                    </table>
                    
                    <div style="margin-top: 30px; padding: 20px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px;">
                        <h4 style="margin-top: 0;">⚠️ Acción Requerida:</h4>
                        <ol style="margin-bottom: 0;">
                            <li>Confirma la disponibilidad de los productos</li>
                            <li>Prepara el despacho según tu acuerdo con 4x4MAX</li>
                            <li>Notifica cualquier problema de stock o demora</li>
                        </ol>
                    </div>
                    
                    <div style="margin-top: 20px; padding: 15px; background-color: #e7f3ff; border-radius: 5px;">
                        <p style="margin: 0;"><strong>📞 Contacto:</strong> Si tienes dudas sobre esta orden, contáctanos contacto@4x4max.cl.</p>
                    </div>
                </div>
                
                <div style="background-color: #343a40; color: white; padding: 20px; text-align: center; margin-top: 30px;">
                    <p style="margin: 5px 0;">Gracias por ser parte de 4x4MAX</p>
                    <p style="font-size: 0.9em; margin: 5px 0;">🌐 <a href="https://4x4max.cl" style="color: #28a745;">4x4max.cl</a></p>
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
                recipient_list=[provider.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"[PROVIDER EMAIL] ✅ Email enviado a {provider.name} ({provider.email})")
        except Exception as e:
            logger.error(f"[PROVIDER EMAIL] ❌ Error enviando a {provider.name}: {e}")


def send_provider_order_notification_async(order):
    """Envía emails a proveedores de forma asíncrona"""
    def send_in_background():
        try:
            send_provider_order_notification(order)
        except Exception as e:
            logger.error(f"[PROVIDER EMAIL ASYNC] Error en thread: {e}")
    
    email_thread = Thread(target=send_in_background)
    email_thread.daemon = True
    email_thread.start()
    logger.info(f"[PROVIDER EMAIL] Thread iniciado para orden #{order.id}")


def send_pending_order_email(order):
    """
    Envía email de confirmación para pedido pendiente (transferencia bancaria)
    """
    logger.info(f"[PENDING ORDER EMAIL] Iniciando envío para orden #{order.id}")
    
    # Datos bancarios (puedes moverlos a settings.py)
    bank_info = {
        'bank_name': 'Banco Estado',
        'account_type': 'Cuenta Corriente',
        'account_number': '12345678-9',
        'rut': '76.XXX.XXX-X',
        'account_holder': '4X4MAX REPUESTOS LTDA',
        'email': 'contacto@4x4max.cl'
    }
    
    # Obtener items de la orden
    order_items = order.orderitem_set.all()
    
    # Construir lista de productos
    products_html = ""
    for item in order_items:
        badge = '<span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; letter-spacing: 0.5px;">🌎 INTERNACIONAL</span>' if item.is_international else ''
        products_html += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 16px 12px;">
                <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">{item.product.name}</div>
                <div style="font-size: 0.85em; color: #6b7280;">PN: {item.product.part_number}</div>
                {f'<div style="margin-top: 6px;">{badge}</div>' if item.is_international else ''}
            </td>
            <td style="padding: 16px 12px; text-align: center;">
                <span style="background-color: #f3f4f6; padding: 6px 16px; border-radius: 8px; font-weight: 600; color: #374151;">
                    {item.quantity}
                </span>
            </td>
            <td style="padding: 16px 12px; text-align: right; color: #6b7280; font-size: 0.95em;">
                ${item.price:,.0f}
            </td>
            <td style="padding: 16px 12px; text-align: right; font-weight: 600; color: #1f2937; font-size: 1.05em;">
                ${item.get_total():,.0f}
            </td>
        </tr>
        """
    
    # Footer de la tabla
    table_footer = ""
    if order.coupon and order.coupon_discount > 0:
        table_footer = f"""
        <tr style="background-color: #f9fafb;">
            <td colspan="3" style="padding: 14px 12px; text-align: right; font-weight: 500; color: #4b5563;">
                Subtotal:
            </td>
            <td style="padding: 14px 12px; text-align: right; font-weight: 600; color: #1f2937; font-size: 1.05em;">
                ${order.amount_before_discount:,.0f}
            </td>
        </tr>
        <tr style="background: linear-gradient(to right, #ecfdf5, #d1fae5);">
            <td colspan="3" style="padding: 14px 12px; text-align: right; font-weight: 600; color: #059669;">
                🎟️ Descuento ({order.coupon.code}):
            </td>
            <td style="padding: 14px 12px; text-align: right; font-weight: 700; color: #059669; font-size: 1.05em;">
                -${order.coupon_discount:,.0f}
            </td>
        </tr>
        <tr style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
            <td colspan="3" style="padding: 18px 12px; text-align: right; font-weight: 700; color: white; font-size: 1.1em;">
                TOTAL A PAGAR:
            </td>
            <td style="padding: 18px 12px; text-align: right; color: white; font-size: 1.4em; font-weight: 700;">
                ${order.amount_pay:,.0f}
            </td>
        </tr>
        """
    else:
        table_footer = f"""
        <tr style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
            <td colspan="3" style="padding: 18px 12px; text-align: right; font-weight: 700; color: white; font-size: 1.1em;">
                TOTAL A PAGAR:
            </td>
            <td style="padding: 18px 12px; text-align: right; color: white; font-size: 1.4em; font-weight: 700;">
                ${order.amount_pay:,.0f}
            </td>
        </tr>
        """
    
    # Información del cupón
    coupon_info = ""
    if order.coupon:
        coupon_info = f"""
        <div style="background: linear-gradient(to right, #d1fae5, #a7f3d0); padding: 20px; border-left: 5px solid #10b981; margin: 25px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.15);">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 2em; margin-right: 12px;">🎉</span>
                <strong style="font-size: 1.15em; color: #065f46;">¡Descuento Aplicado!</strong>
            </div>
            <div style="color: #047857; line-height: 1.8;">
                Cupón <strong style="background-color: white; padding: 3px 8px; border-radius: 6px; color: #10b981;">{order.coupon.code}</strong> aplicado exitosamente<br>
                {f'• {order.coupon.description}<br>' if order.coupon.description else ''}
                • Ahorraste: <strong>${order.coupon_discount:,.0f} CLP</strong>
            </div>
        </div>
        """
    
    subject = f'⏳ Pedido #{order.buy_order} - Pendiente de Pago - 4x4MAX'
    
    html_message = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
            <div style="max-width: 700px; margin: 0 auto; background-color: white;">
                
                <!-- Header con degradado naranja/amarillo -->
                <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 40px 30px; text-align: center;">
                    <div style="font-size: 3em; margin-bottom: 10px;">⏳</div>
                    <h1 style="color: white; margin: 0; font-size: 2em; font-weight: 700; letter-spacing: -0.5px;">
                        ¡Pedido Recibido!
                    </h1>
                    <p style="color: rgba(255, 255, 255, 0.95); margin: 10px 0 0 0; font-size: 1.05em;">
                        Pendiente de Confirmación de Pago
                    </p>
                </div>
                
                <div style="padding: 35px 30px;">
                    
                    <!-- Saludo -->
                    <h2 style="color: #1f2937; font-size: 1.5em; margin: 0 0 15px 0; font-weight: 600;">
                        Hola {order.full_name} 👋
                    </h2>
                    <p style="color: #4b5563; line-height: 1.6; font-size: 1.05em; margin: 0 0 30px 0;">
                        Tu pedido ha sido recibido exitosamente y está <strong>pendiente de pago</strong>. 
                        A continuación encontrarás los datos para realizar la transferencia bancaria.
                    </p>
                    
                    <!-- Card de información de orden -->
                    <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 25px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15); border-left: 5px solid #f59e0b;">
                        <div style="display: grid; gap: 12px;">
                            <div style="display: flex; align-items: center; padding: 8px 0;">
                                <span style="font-size: 1.3em; margin-right: 12px;">📋</span>
                                <div>
                                    <div style="color: #78350f; font-size: 0.85em; margin-bottom: 2px;">Número de Orden</div>
                                    <div style="color: #92400e; font-weight: 700; font-size: 1.15em;">#{order.buy_order}</div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; padding: 8px 0;">
                                <span style="font-size: 1.3em; margin-right: 12px;">📅</span>
                                <div>
                                    <div style="color: #78350f; font-size: 0.85em; margin-bottom: 2px;">Fecha</div>
                                    <div style="color: #92400e; font-weight: 600;">{order.date_order.strftime('%d/%m/%Y %H:%M')}</div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; padding: 8px 0;">
                                <span style="font-size: 1.3em; margin-right: 12px;">⏳</span>
                                <div>
                                    <div style="color: #78350f; font-size: 0.85em; margin-bottom: 2px;">Estado</div>
                                    <div>
                                        <span style="background-color: white; color: #d97706; padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 0.9em; display: inline-block; border: 2px solid #f59e0b;">
                                            ⏳ PENDIENTE DE PAGO
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Datos Bancarios - DESTACADO -->
                    <div style="background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); padding: 30px; border-radius: 12px; margin: 30px 0; box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2); border: 3px solid #3b82f6;">
                        <div style="text-align: center; margin-bottom: 20px;">
                            <span style="font-size: 2.5em; display: block; margin-bottom: 10px;">🏦</span>
                            <h3 style="color: #1e3a8a; margin: 0; font-size: 1.5em; font-weight: 700;">
                                Datos para Transferencia
                            </h3>
                        </div>
                        
                        <div style="background-color: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 12px 0; color: #4b5563; font-weight: 500; border-bottom: 1px solid #e5e7eb;">Banco:</td>
                                    <td style="padding: 12px 0; color: #1f2937; font-weight: 700; text-align: right; border-bottom: 1px solid #e5e7eb;">{bank_info['bank_name']}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; color: #4b5563; font-weight: 500; border-bottom: 1px solid #e5e7eb;">Tipo de Cuenta:</td>
                                    <td style="padding: 12px 0; color: #1f2937; font-weight: 700; text-align: right; border-bottom: 1px solid #e5e7eb;">{bank_info['account_type']}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; color: #4b5563; font-weight: 500; border-bottom: 1px solid #e5e7eb;">Número de Cuenta:</td>
                                    <td style="padding: 12px 0; color: #1f2937; font-weight: 700; text-align: right; border-bottom: 1px solid #e5e7eb; font-size: 1.15em;">{bank_info['account_number']}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; color: #4b5563; font-weight: 500; border-bottom: 1px solid #e5e7eb;">RUT:</td>
                                    <td style="padding: 12px 0; color: #1f2937; font-weight: 700; text-align: right; border-bottom: 1px solid #e5e7eb;">{bank_info['rut']}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; color: #4b5563; font-weight: 500; border-bottom: 1px solid #e5e7eb;">Titular:</td>
                                    <td style="padding: 12px 0; color: #1f2937; font-weight: 700; text-align: right; border-bottom: 1px solid #e5e7eb;">{bank_info['account_holder']}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; color: #4b5563; font-weight: 500;">Email para Comprobante:</td>
                                    <td style="padding: 12px 0; color: #2563eb; font-weight: 700; text-align: right;">{bank_info['email']}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <!-- Monto a pagar - DESTACADO -->
                        <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 20px; border-radius: 10px; margin-top: 20px; text-align: center; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);">
                            <div style="color: rgba(255, 255, 255, 0.9); font-size: 0.9em; margin-bottom: 5px; font-weight: 600; letter-spacing: 1px;">MONTO A TRANSFERIR</div>
                            <div style="color: white; font-size: 2.5em; font-weight: 700; letter-spacing: -1px;">
                                ${order.amount_pay:,.0f} CLP
                            </div>
                        </div>
                    </div>
                    
                    <!-- Instrucciones importantes -->
                    <div style="background: linear-gradient(to right, #fef3c7, #fde68a); padding: 25px; border-left: 5px solid #f59e0b; margin: 30px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);">
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <span style="font-size: 2em; margin-right: 12px;">⚠️</span>
                            <h4 style="margin: 0; color: #92400e; font-size: 1.2em; font-weight: 700;">
                                Muy Importante
                            </h4>
                        </div>
                        <div style="color: #78350f; line-height: 1.8; font-size: 1.02em;">
                            <strong>Al realizar la transferencia, por favor indica en el mensaje o glosa:</strong>
                            <div style="background-color: white; padding: 15px; margin: 15px 0; border-radius: 8px; text-align: center;">
                                <span style="color: #f59e0b; font-size: 1.3em; font-weight: 700;">
                                    "Orden #{order.buy_order}"
                                </span>
                            </div>
                            Esto nos ayudará a identificar tu pago rápidamente y procesar tu pedido sin demoras.
                        </div>
                    </div>
                    
                    {coupon_info}
                    
                    <!-- Productos ordenados -->
                    <div style="margin: 30px 0;">
                        <h3 style="color: #1f2937; font-size: 1.3em; margin: 0 0 18px 0; font-weight: 600; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">
                            📦 Resumen de tu Pedido
                        </h3>
                        <div style="overflow-x: auto; border-radius: 12px; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);">
                            <table style="width: 100%; border-collapse: collapse; background-color: white;">
                                <thead>
                                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                                        <th style="padding: 16px 12px; text-align: left; color: white; font-weight: 600; font-size: 0.95em; letter-spacing: 0.3px;">
                                            PRODUCTO
                                        </th>
                                        <th style="padding: 16px 12px; text-align: center; color: white; font-weight: 600; font-size: 0.95em; letter-spacing: 0.3px;">
                                            CANT.
                                        </th>
                                        <th style="padding: 16px 12px; text-align: right; color: white; font-weight: 600; font-size: 0.95em; letter-spacing: 0.3px;">
                                            PRECIO UNIT.
                                        </th>
                                        <th style="padding: 16px 12px; text-align: right; color: white; font-weight: 600; font-size: 0.95em; letter-spacing: 0.3px;">
                                            SUBTOTAL
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {products_html}
                                </tbody>
                                <tfoot>
                                    {table_footer}
                                </tfoot>
                            </table>
                        </div>
                    </div>
                    
                    <!-- Próximos pasos -->
                    <div style="margin: 35px 0; padding: 25px; background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%); border-left: 5px solid #667eea; border-radius: 12px;">
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <span style="font-size: 2em; margin-right: 12px;">📝</span>
                            <h4 style="margin: 0; color: #1f2937; font-size: 1.2em; font-weight: 700;">
                                Próximos Pasos
                            </h4>
                        </div>
                        <ol style="margin: 0; padding-left: 20px; color: #4b5563; line-height: 1.9; font-size: 1.02em;">
                            <li style="margin-bottom: 10px;">
                                <strong>Realiza la transferencia</strong> con los datos bancarios proporcionados arriba
                            </li>
                            <li style="margin-bottom: 10px;">
                                <strong>Envía el comprobante</strong> a <a href="mailto:{bank_info['email']}" style="color: #2563eb; text-decoration: none; font-weight: 600;">{bank_info['email']}</a> indicando tu número de orden
                            </li>
                            <li style="margin-bottom: 10px;">
                                <strong>Confirmaremos tu pago</strong> en un plazo de 24 horas hábiles
                            </li>
                            <li style="margin-bottom: 0;">
                                Una vez confirmado, <strong>prepararemos tu pedido</strong> para envío
                            </li>
                        </ol>
                    </div>
                    
                    <!-- Información adicional -->
                    <div style="margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); border-radius: 12px; text-align: center;">
                        <p style="margin: 0 0 10px 0; color: #1e40af; font-size: 1.05em; line-height: 1.6;">
                            <strong style="font-size: 1.15em;">📧 Confirmación Enviada</strong><br>
                            Hemos enviado este email a <strong>{order.email}</strong>
                        </p>
                        <p style="margin: 10px 0 0 0; color: #1e40af; font-size: 0.95em;">
                            Si no recibiste este correo, revisa tu carpeta de spam o contáctanos.
                        </p>
                    </div>
                    
                    <!-- Contacto -->
                    <div style="margin: 30px 0; padding: 20px; background-color: #f9fafb; border-radius: 12px; text-align: center; border: 2px dashed #d1d5db;">
                        <p style="margin: 0; color: #4b5563; font-size: 1.05em; line-height: 1.6;">
                            <strong style="font-size: 1.15em; color: #1f2937;">📞 ¿Necesitas ayuda?</strong><br>
                            Contáctanos en <a href="mailto:contacto@4x4max.cl" style="color: #2563eb; text-decoration: none; font-weight: 600;">contacto@4x4max.cl</a>
                        </p>
                    </div>
                    
                </div>
                
                <!-- Footer -->
                <div style="background: linear-gradient(135deg, #1f2937 0%, #111827 100%); padding: 35px 30px; text-align: center;">
                    <div style="margin-bottom: 15px;">
                        <span style="font-size: 2.5em;">🚙</span>
                    </div>
                    <p style="color: #9ca3af; margin: 10px 0; font-size: 1.05em; font-weight: 500;">
                        Gracias por tu compra
                    </p>
                    <h2 style="color: white; margin: 8px 0; font-size: 1.8em; font-weight: 700; letter-spacing: 1px;">
                        4X4MAX
                    </h2>
                    <p style="margin: 15px 0 0 0;">
                        <a href="https://4x4max.cl" style="color: #10b981; text-decoration: none; font-weight: 600; font-size: 1.05em;">
                            🌐 4x4max.cl
                        </a>
                    </p>
                </div>
                
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
        logger.info(f"[PENDING ORDER EMAIL] ✅ Email enviado a {order.email}")
        return True
    except Exception as e:
        logger.error(f"[PENDING ORDER EMAIL] ❌ Error enviando email: {e}")
        return False


def send_pending_order_email_async(order):
    """Envía email de orden pendiente de forma asíncrona"""
    def send_in_background():
        try:
            send_pending_order_email(order)
        except Exception as e:
            logger.error(f"[PENDING ORDER EMAIL ASYNC] Error en thread: {e}")
    
    email_thread = Thread(target=send_in_background)
    email_thread.daemon = True
    email_thread.start()
    logger.info(f"[PENDING ORDER EMAIL] Thread iniciado para orden #{order.id}")