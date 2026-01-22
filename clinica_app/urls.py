# clinica_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    
    # Páginas principales
    path('home/', views.home_view, name='home'),
    path('calendario/', views.calendario_view, name='calendario'),
    path('agendar-cita/', views.agendar_cita_view, name='agendar_cita'),
    path('historial-citas/', views.historial_citas_view, name='historial_citas'),
    
    # Gestión de usuarios (solo admin)
    path('gestionar-usuarios/', views.gestionar_usuarios_view, name='gestionar_usuarios'),
    path('eliminar-usuario/<int:user_id>/', views.eliminar_usuario_view, name='eliminar_usuario'),
    path('editar-usuario/<int:user_id>/', views.editar_usuario_view, name='editar_usuario'), 
    # Acciones sobre citas
    path('cancelar-cita/<int:cita_id>/', views.cancelar_cita_view, name='cancelar_cita'),
    path('actualizar-estado-cita/<int:cita_id>/', views.actualizar_estado_cita, name='actualizar_estado_cita'),  
    # APIs
    path('api/citas-disponibles/', views.api_citas_disponibles, name='api_citas_disponibles'),
    # Agregar estas líneas a tu clinica_app/urls.py

    
]