from django.core.mail import EmailMessage
from django.conf import settings
from usuarios.models import Usuario


def get_correos_administradores():
    return list(
        Usuario.objects.filter(activo=True, id_rol__nombre__in=['Administrador'])
        .values_list('email', flat=True)
    )


def enviar_alerta_stock(alerta_dict):
    """
    alerta_dict: {'tipo', 'nombre', 'descripcion', 'producto_nombre', 'producto_codigo'}
    Equivalente a enviarAlertaStock() en emailService.js
    """
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return {'ok': False, 'message': 'Servicio de correo no configurado'}

    destinatarios = get_correos_administradores()
    if not destinatarios:
        return {'ok': False, 'message': 'No hay destinatarios'}

    es_critica = alerta_dict['tipo'] == 'Critica'
    color_badge = '#dc2626' if es_critica else '#f5a623'
    bg_badge = '#fee2e2' if es_critica else '#fef3c7'

    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:460px;margin:0 auto;background:#f1f5f9;padding:24px;">
      <div style="background:#1a2340;padding:20px 24px;border-radius:10px 10px 0 0;display:flex;align-items:center;gap:12px;">
        <div style="width:36px;height:36px;background:#f5a623;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;">⚙️</div>
        <div>
          <div style="color:#fff;font-weight:700;font-size:15px;letter-spacing:.3px;">FERRETERÍA</div>
          <div style="color:#9aa5c4;font-size:10px;letter-spacing:.5px;">INVENTARIO Y VENTAS</div>
        </div>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:22px 24px;border-radius:0 0 10px 10px;">
        <span style="display:inline-block;background:{bg_badge};color:{color_badge};padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;">
          {alerta_dict['tipo'].upper()}
        </span>
        <h2 style="margin:10px 0 6px;color:#1e293b;font-size:18px;">{alerta_dict['nombre']}</h2>
        <p style="color:#475569;font-size:14px;margin:0 0 14px;line-height:1.4;">{alerta_dict.get('descripcion','')}</p>
        {"<div style='background:#f8fafc;border-radius:8px;padding:10px 14px;font-size:13px;color:#334155;'><strong>" + alerta_dict.get('producto_nombre','') + "</strong> · " + alerta_dict.get('producto_codigo','') + "</div>" if alerta_dict.get('producto_nombre') else ""}
        <p style="color:#94a3b8;font-size:11px;margin-top:18px;margin-bottom:0;">Panel de Alertas · Sistema Ferretería</p>
      </div>
    </div>
    """

    emoji = '🔴' if es_critica else '🟡'
    email = EmailMessage(
        subject=f"{emoji} [{alerta_dict['tipo']}] {alerta_dict['nombre']} — Sistema Ferretería",
        body=html,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatarios,
    )
    email.content_subtype = 'html'
    try:
        email.send()
        return {'ok': True, 'destinatarios': destinatarios}
    except Exception as e:
        return {'ok': False, 'message': str(e)}
