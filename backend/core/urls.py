# core/urls.py
from django.urls import path
from . import views

urlpatterns = [

    path('api/auth/login/', views.login_view),
    path('api/auth/forgot-password/', views.forgot_password_view),
    path('api/auth/verify-code/', views.verify_code_view),
    path('api/auth/reset-password/', views.reset_password_view),

    # ── Productos (los que usa productos.html) ──────────────
    path('api/productos/stock-bajo/', views.stock_bajo_view),
    path('api/productos/mas-vendidos/', views.productos_mas_vendidos_view),
    path('api/productos/', views.productos_ui_view),                # GET listar + POST crear
    path('api/productos/<int:procve>/', views.producto_ui_detail_view),  # PUT/DELETE

    # ── Categorías ────────────────────────────────────────────
    path('api/categorias/', views.categorias_con_conteo_view),  # ⚠ necesita también aceptar POST (ver abajo)

    # ── Usuarios (usuarios.html) ─────────────────────────────
    path('api/usuarios/', views.usuarios_view),
    path('api/usuarios/<int:empcve>/', views.usuario_detail_view),
    path('api/sucursales/', views.sucursales_view),

    # ── Clientes ──────────────────────────────────────────────
    path('api/clientes/crear/', views.crear_cliente_view),
    path('api/clientes/listar/', views.listar_clientes_view),
    path('api/clientes/<int:clicve>/', views.actualizar_cliente_view),

    # ── Ventas ────────────────────────────────────────────────
    path('api/ventas/crear/', views.crear_venta_view),
    path('api/ventas/listar/', views.listar_ventas_view),
    path('api/ventas/', views.ventas_recientes_view),

    # ── Alertas ───────────────────────────────────────────────
    path('api/alertas/', views.alertas_view),
    path('api/alertas/<int:alertcve>/notificar/', views.alerta_notificar_view),
    path('api/alertas/<int:alertcve>/resolver/', views.alerta_resolver_view),

    #  Movimientos de inventario (Admin + Vendedor) ─────────
    path('api/movimientos/', views.movimientos_view),

    #  Reportes (solo Administrador) ────────────────────────
    path('api/reportes/', views.reportes_view),
    path('api/reportes/inventario/', views.reporte_inventario_view),
    path('api/reportes/ventas/', views.reporte_ventas_view),
    path('api/reportes/stock-bajo/', views.reporte_stock_bajo_view),
    path('api/reportes/movimientos/', views.reporte_movimientos_view),

    # ── Dashboard ─────────────────────────────────────────────
    path('api/dashboard/stats/', views.dashboard_stats_view),
    path('api/dashboard/ventas-semana/', views.ventas_semana_view),

    # ── Rutas viejas (opcional conservarlas para Postman) ────
    path('api/empleados/', views.crear_empleado_view),
    path('api/empleados/listar/', views.listar_empleados_view),
    path('api/empleados/<int:empcve>/', views.actualizar_empleado_view),
    path('api/categorias/crear/', views.crear_categoria_view),
    path('api/categorias/listar/', views.listar_categorias_view),
    path('api/categorias/<int:catcve>/', views.actualizar_categoria_view),

]