# clinica_app/views.py

# Importaciones necesarias para Django
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta, date
import json
from .models import CustomUser, Cita, Medico, Paciente, Especialidad
from .forms import LoginForm, RegistroForm, CitaForm

def enviar_correo_registro(user, password_temp):
    """
    FUNCIÓN: Envía correo electrónico cuando se registra un nuevo usuario
    PARÁMETROS:
    - user: Objeto del usuario recién creado
    - password_temp: Contraseña temporal para incluir en el correo
    
    PROPÓSITO: Notificar al usuario sus credenciales de acceso por email
    RETORNA: True si el correo se envió exitosamente, False si hubo error
    """
    subject = 'Bienvenido a la Clínica Dermatológica'
    # Mensaje personalizado con datos del usuario
    message = f"""
    Estimado/a {user.get_full_name()},
    
    Su cuenta ha sido creada exitosamente en nuestro sistema.
    
    Datos de acceso:
    Usuario: {user.username}
    Contraseña: {password_temp}
    Email: {user.email}
    Rol: {user.get_role_display()}
    
    Por favor, guarde estos datos en un lugar seguro.
    Puede acceder al sistema en: http://localhost:8000
    
    Atentamente,
    Clínica Valencia
    """
    
    try:
        # Intenta enviar el correo usando configuración de Django
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,  # Email del remitente configurado
            [user.email],              # Lista de destinatarios
            fail_silently=False,       # Lanza excepción si hay error
        )
        return True
    except Exception as e:
        # Si falla, imprime error y retorna False
        print(f"Error enviando email: {e}")
        return False

def enviar_correo_cita(cita):
    """
    FUNCIÓN: Envía correos de confirmación cuando se agenda una cita
    PARÁMETROS:
    - cita: Objeto de la cita recién creada
    
    PROPÓSITO: Notificar tanto al paciente como al médico sobre la nueva cita
    RETORNA: True si ambos correos se enviaron, False si hubo error
    """
    
    # CORREO PARA EL PACIENTE
    subject_paciente = 'Confirmación de Cita - Clínica Valencia'
    message_paciente = f"""
    Estimado/a {cita.paciente.get_full_name()},
    
    Su cita ha sido agendada exitosamente:
    
    Fecha: {cita.fecha.strftime('%d/%m/%Y')}
    Hora: {cita.hora.strftime('%H:%M')}
    Médico: Dr./Dra. {cita.medico.get_full_name()}
    Duración: {cita.duracion}minutos
    Motivo: {cita.motivo}
    
    Por favor, llegue 10 minutos antes de su cita.
    
    Atentamente,
    Clínica Valencia.
    """
    
    # CORREO PARA EL MÉDICO
    subject_medico = 'Nueva Cita Agendada - Clínica Valencia'
    message_medico = f"""
    Dr./Dra. {cita.medico.get_full_name()},
    
    Se ha agendado una nueva cita:
    
    Fecha: {cita.fecha.strftime('%d/%m/%Y')}
    Hora: {cita.hora.strftime('%H:%M')}
    Paciente: {cita.paciente.get_full_name()}
    Teléfono: {cita.paciente.phone}
    Duración: {cita.duracion} minutos
    Motivo: {cita.motivo}
    
    Atentamente,
    Sistema de Clínica Valencia.
    """
    
    try:
        # Enviar correo al paciente
        send_mail(
            subject_paciente,
            message_paciente,
            settings.EMAIL_HOST_USER,
            [cita.paciente.email],
            fail_silently=False,
        )
        
        # Enviar correo al médico
        send_mail(
            subject_medico,
            message_medico,
            settings.EMAIL_HOST_USER,
            [cita.medico.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error enviando emails de cita: {e}")
        return False

def login_view(request):
    """
    VISTA: Maneja el login de usuarios
    
    PROPÓSITO: 
    - Mostrar formulario de login en GET
    - Procesar credenciales y autenticar en POST
    - Redirigir a home si ya está autenticado
    """
    
    # Si el usuario ya está logueado, redirigir a home
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Procesar formulario de login
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Intentar autenticar con las credenciales
            user = authenticate(request, username=username, password=password)
            
            if user:
                # Si la autenticación es exitosa
                login(request, user, backend='clinica_app.backends.SPAuthBackend')
                messages.success(request, f'Bienvenido {user.get_full_name() or user.username}')
                return redirect('home')
            else:
                # Si las credenciales son incorrectas
                messages.error(request, 'Usuario o contraseña incorrectos')
    else:
        # GET request - mostrar formulario vacío
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def registro_view(request):
    """
    VISTA: Permite a administradores registrar nuevos usuarios
    
    PROPÓSITO:
    - Solo admins pueden acceder
    - Crear usuarios con diferentes roles (admin, médico, paciente)
    - Crear registros adicionales según el rol (médico/paciente)
    - Enviar correo de bienvenida con credenciales
    """
    
    # VERIFICAR PERMISOS: Solo administradores
    if not request.user.is_authenticated or not request.user.is_admin:
        messages.error(request, 'Solo administradores pueden registrar usuarios')
        return redirect('login')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                # Extraer datos del formulario
                username = form.cleaned_data['username']
                email = form.cleaned_data['email']
                password = form.cleaned_data['password']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']
                role = int(form.cleaned_data['role'])  # 1=admin, 2=medico, 3=paciente
                phone = form.cleaned_data.get('phone', '')
                address = form.cleaned_data.get('address', '')
                
                # INSERCIÓN EN BASE DE DATOS usando SQL directo
                with connection.cursor() as cursor:
                    # Crear usuario principal en tabla auth_user_custom
                    cursor.execute("""
                        INSERT INTO auth_user_custom 
                        (username, email, password, first_name, last_name, role, 
                         is_active, is_staff, is_superuser, phone, address, date_joined)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, [
                        username, email, password, first_name, last_name, role,
                        1,  # is_active = True
                        1 if role == 1 else 0,  # is_staff solo para admin
                        1 if role == 1 else 0,  # is_superuser solo para admin
                        phone, address
                    ])
                    
                    user_id = cursor.lastrowid  # Obtener ID del usuario creado
                    
                    # CREAR REGISTRO ADICIONAL SEGÚN EL ROL
                    if role == 2:  # Si es médico
                        especialidad_id = request.POST.get('especialidad', 1)
                        cursor.execute("""
                            INSERT INTO medicos 
                            (user_id, especialidad_id, numero_colegiado, horario_inicio, horario_fin, dias_laborales)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, [
                            user_id, 
                            especialidad_id,
                            request.POST.get('numero_colegiado', ''),
                            request.POST.get('horario_inicio', '08:00'),
                            request.POST.get('horario_fin', '17:00'),
                            request.POST.get('dias_laborales', 'LUN,MAR,MIE,JUE,VIE')
                        ])
                    
                    elif role == 3:  # Si es paciente
                        fecha_nac = request.POST.get('fecha_nacimiento')
                        if not fecha_nac:
                            fecha_nac = None
                        
                        cursor.execute("""
                            INSERT INTO pacientes 
                            (user_id, fecha_nacimiento, tipo_sangre, alergias, observaciones)
                            VALUES (%s, %s, %s, %s, %s)
                        """, [
                            user_id,
                            fecha_nac,
                            request.POST.get('tipo_sangre', ''),
                            request.POST.get('alergias', ''),
                            request.POST.get('observaciones', '')
                        ])
                
                # Obtener el usuario creado para enviar email
                new_user = CustomUser.objects.get(id=user_id)
                
                # ENVIAR CORREO DE BIENVENIDA
                if enviar_correo_registro(new_user, password):
                    messages.success(request, f'Usuario {username} creado y correo enviado exitosamente')
                else:
                    messages.warning(request, f'Usuario {username} creado pero no se pudo enviar el correo')
                
                return redirect('gestionar_usuarios')
                
            except Exception as e:
                messages.error(request, f'Error al crear usuario: {str(e)}')
                print(f"Error detallado: {e}")
    else:
        # GET request - mostrar formulario vacío
        form = RegistroForm()
    
    # Obtener especialidades para el dropdown de médicos
    try:
        especialidades = Especialidad.objects.all()
    except:
        especialidades = []
    
    return render(request, 'register.html', {
        'form': form,
        'especialidades': especialidades
    })

@login_required
def home_view(request):
    """
    VISTA: Página principal del sistema después del login
    
    PROPÓSITO:
    - Mostrar dashboard personalizado según el rol del usuario
    - Médicos: ven sus citas del día
    - Pacientes: ven sus próximas citas
    - Admin: vista general del sistema
    """
    
    # Contexto base para todos los usuarios
    context = {
        'user': request.user,
        'es_admin': request.user.is_admin,
        'es_medico': request.user.is_medico,
        'es_paciente': request.user.is_paciente,
    }
    
    # DASHBOARD PARA MÉDICOS: Citas del día actual
    if request.user.is_medico:
        hoy = date.today()
        citas_hoy = Cita.objects.filter(
            medico=request.user,  # Solo citas de este médico
            fecha=hoy,           # Solo de hoy
            estado__in=['PENDIENTE', 'CONFIRMADA']  # Solo activas
        ).order_by('hora')
        context['citas_hoy'] = citas_hoy
    
    # DASHBOARD PARA PACIENTES: Próximas 5 citas
    elif request.user.is_paciente:
        citas_proximas = Cita.objects.filter(
            paciente=request.user,        # Solo citas de este paciente
            fecha__gte=date.today(),      # Desde hoy en adelante
            estado__in=['PENDIENTE', 'CONFIRMADA']  # Solo activas
        ).order_by('fecha', 'hora')[:5]   # Las 5 más próximas
        context['citas_proximas'] = citas_proximas
    
    return render(request, 'home.html', context)

@login_required
def calendario_view(request):
    """
    VISTA: Muestra calendario de citas con filtros por rol
    
    PROPÓSITO:
    - Mostrar citas del mes seleccionado
    - Filtrar según el rol: pacientes ven solo las suyas, médicos las suyas, admin todas
    - Permitir navegación entre meses
    - Preparar datos para visualización en JavaScript
    """
    
    # Obtener mes y año de los parámetros GET (por defecto: mes actual)
    mes = int(request.GET.get('mes', datetime.now().month))
    año = int(request.GET.get('año', datetime.now().year))
    
    # Calcular rango de fechas del mes
    fecha_inicio = date(año, mes, 1)  # Primer día del mes
    if mes == 12:
        fecha_fin = date(año + 1, 1, 1) - timedelta(days=1)  # Último día de diciembre
    else:
        fecha_fin = date(año, mes + 1, 1) - timedelta(days=1)  # Último día del mes
    
    # FILTRAR CITAS SEGÚN EL ROL DEL USUARIO
    if request.user.is_paciente:
        # Pacientes: solo sus propias citas
        citas = Cita.objects.filter(
            paciente=request.user,
            fecha__range=[fecha_inicio, fecha_fin],
            estado__in=['PENDIENTE', 'CONFIRMADA']
        ).select_related('medico', 'paciente')  # Optimización: join con tablas relacionadas
        
    elif request.user.is_medico:
        # Médicos: solo sus propias citas
        citas = Cita.objects.filter(
            medico=request.user,
            fecha__range=[fecha_inicio, fecha_fin],
            estado__in=['PENDIENTE', 'CONFIRMADA']
        ).select_related('medico', 'paciente')
        
    else:
        # Administradores: todas las citas
        citas = Cita.objects.filter(
            fecha__range=[fecha_inicio, fecha_fin],
            estado__in=['PENDIENTE', 'CONFIRMADA']
        ).select_related('medico', 'paciente')
    
    # CONVERTIR CITAS A FORMATO JSON para JavaScript
    citas_json = []
    for cita in citas:
        citas_json.append({
            'id': cita.id,
            'fecha': str(cita.fecha),
            'hora': str(cita.hora),
            'duracion': cita.duracion,
            'estado': cita.estado,
            'motivo': cita.motivo,
            'paciente_nombre': cita.paciente.get_full_name(),
            'medico_nombre': cita.medico.get_full_name(),
        })
    
    # Obtener lista de médicos activos para el formulario de agendar
    medicos = CustomUser.objects.filter(role=2, is_active=True)
    
    context = {
        'mes': mes,
        'año': año,
        'citas': json.dumps(citas_json),  # Convertir a JSON para JavaScript
        'medicos': medicos,
        'puede_agendar': request.user.is_admin or request.user.is_medico,
    }
    
    return render(request, 'calendar.html', context)

@login_required
def agendar_cita_view(request):
    """
    VISTA: Permite agendar nuevas citas
    
    PROPÓSITO:
    - Solo admin y médicos pueden agendar citas
    - Médicos solo pueden agendar para sí mismos
    - Verificar disponibilidad de horarios
    - Enviar notificaciones por correo
    """
    
    # VERIFICAR PERMISOS
    if not (request.user.is_admin or request.user.is_medico):
        messages.error(request, 'No tiene permisos para agendar citas')
        return redirect('calendario')
    
    if request.method == 'POST':
        try:
            # Extraer datos del formulario
            paciente_id = request.POST.get('paciente')
            medico_id = request.POST.get('medico')
            fecha = request.POST.get('fecha')
            hora = request.POST.get('hora')
            duracion = request.POST.get('duracion', 30)  # Por defecto 30 minutos
            motivo = request.POST.get('motivo')
            
            # RESTRICCIÓN: Si es médico, solo puede agendar sus propias citas
            if request.user.is_medico:
                medico_id = request.user.id
            
            # VERIFICAR DISPONIBILIDAD DEL HORARIO
            cita_existente = Cita.objects.filter(
                medico_id=medico_id,
                fecha=fecha,
                hora=hora,
                estado__in=['PENDIENTE', 'CONFIRMADA']  # Solo citas activas
            ).exists()
            
            if cita_existente:
                messages.error(request, 'Ya existe una cita en ese horario')
                return redirect('agendar_cita')
            
            # CREAR LA CITA usando SQL directo
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO citas (paciente_id, medico_id, fecha, hora, duracion, motivo, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, 'PENDIENTE')
                """, [paciente_id, medico_id, fecha, hora, duracion, motivo])
                
                cita_id = cursor.lastrowid  # Obtener ID de la cita creada
            
            # Obtener la cita completa para enviar emails
            cita = Cita.objects.get(id=cita_id)
            
            # ENVIAR NOTIFICACIONES POR CORREO
            if enviar_correo_cita(cita):
                messages.success(request, 'Cita agendada y notificaciones enviadas exitosamente')
            else:
                messages.warning(request, 'Cita agendada pero no se pudieron enviar las notificaciones')
            
            return redirect('calendario')
            
        except Exception as e:
            messages.error(request, f'Error al agendar cita: {str(e)}')
            return redirect('agendar_cita')
    
    # GET REQUEST - Mostrar formulario
    
    # Preparar lista de médicos según el rol
    if request.user.is_admin:
        medicos = CustomUser.objects.filter(role=2, is_active=True)  # Todos los médicos
    else:
        medicos = [request.user]  # Solo el médico actual
    
    # Lista de todos los pacientes activos
    pacientes = CustomUser.objects.filter(role=3, is_active=True)
    
    # Si viene con fecha preseleccionada desde el calendario
    fecha_preseleccionada = request.GET.get('fecha', '')
    
    return render(request, 'agendar_cita.html', {
        'medicos': medicos,
        'pacientes': pacientes,
        'fecha_preseleccionada': fecha_preseleccionada,
    })

@login_required
def eliminar_usuario_view(request, user_id):
    """
    VISTA: Elimina un usuario del sistema (solo administradores)
    
    PROPÓSITO:
    - Solo admin puede eliminar usuarios
    - Prevenir auto-eliminación del admin
    - Usar stored procedure para eliminación segura
    """
    
    # VERIFICAR PERMISOS
    if not request.user.is_admin:
        return HttpResponseForbidden("No tiene permisos para eliminar usuarios")
    
    # PREVENIR AUTO-ELIMINACIÓN
    if user_id == request.user.id:
        messages.error(request, 'No puede eliminar su propia cuenta')
        return redirect('gestionar_usuarios')
    
    try:
        # ELIMINAR USANDO STORED PROCEDURE
        with connection.cursor() as cursor:
            cursor.callproc('sp_eliminar_usuario', [user_id])
            result = cursor.fetchone()
            
        messages.success(request, 'Usuario eliminado exitosamente')
    except Exception as e:
        messages.error(request, f'Error al eliminar usuario: {str(e)}')
    
    return redirect('gestionar_usuarios')

@login_required
def historial_citas_view(request):
    """
    VISTA: Muestra el historial completo de citas según el rol
    
    PROPÓSITO:
    - Pacientes: ven solo su historial personal
    - Médicos: ven historial de sus pacientes
    - Admin: ve todo el historial del sistema
    - Usar consultas SQL optimizadas con JOIN
    """
    
    citas = []
    
    with connection.cursor() as cursor:
        if request.user.is_paciente:
            # PACIENTES: Solo sus propias citas con datos del médico
            cursor.execute("""
                SELECT 
                    c.id, c.fecha, c.hora, c.duracion, c.estado, c.motivo,
                    c.medico_id,
                    CONCAT(um.first_name, ' ', um.last_name) AS medico_nombre,
                    e.nombre AS especialidad
                FROM citas c
                INNER JOIN auth_user_custom um ON c.medico_id = um.id
                LEFT JOIN medicos m ON um.id = m.user_id
                LEFT JOIN especialidades e ON m.especialidad_id = e.id
                WHERE c.paciente_id = %s
                ORDER BY c.fecha DESC, c.hora DESC
            """, [request.user.id])
            
        elif request.user.is_medico:
            # MÉDICOS: Sus citas con datos del paciente
            cursor.execute("""
                SELECT 
                    c.id, c.fecha, c.hora, c.duracion, c.estado, c.motivo,
                    c.medico_id,
                    CONCAT(up.first_name, ' ', up.last_name) AS paciente_nombre,
                    up.phone AS paciente_telefono
                FROM citas c
                INNER JOIN auth_user_custom up ON c.paciente_id = up.id
                WHERE c.medico_id = %s
                ORDER BY c.fecha DESC, c.hora DESC
            """, [request.user.id])
            
        else:  # ADMIN: Todas las citas
            cursor.execute("""
                SELECT 
                    c.id, c.fecha, c.hora, c.duracion, c.estado, c.motivo,
                    c.medico_id, c.paciente_id,
                    CONCAT(up.first_name, ' ', up.last_name) AS paciente_nombre,
                    CONCAT(um.first_name, ' ', um.last_name) AS medico_nombre
                FROM citas c
                INNER JOIN auth_user_custom up ON c.paciente_id = up.id
                INNER JOIN auth_user_custom um ON c.medico_id = um.id
                ORDER BY c.fecha DESC, c.hora DESC
            """)
        
        # Convertir resultado a lista de diccionarios
        columns = [col[0] for col in cursor.description]  # Nombres de columnas
        for row in cursor.fetchall():
            citas.append(dict(zip(columns, row)))  # Combinar nombres con valores
    
    return render(request, 'historial_citas.html', {
        'citas': citas,
        'es_admin': request.user.is_admin,
        'es_medico': request.user.is_medico,
        'es_paciente': request.user.is_paciente,
    })

@login_required
def gestionar_usuarios_view(request):
    """
    VISTA: Panel de administración de usuarios (solo admin)
    
    PROPÓSITO:
    - Mostrar lista completa de usuarios del sistema
    - Separar por roles para mejor organización
    - Punto de acceso para editar/eliminar usuarios
    """
    
    # VERIFICAR PERMISOS
    if not request.user.is_admin:
        messages.error(request, 'No tiene permisos para gestionar usuarios')
        return redirect('home')
    
    # Obtener todos los usuarios ordenados por rol y apellido
    usuarios = CustomUser.objects.all().order_by('role', 'last_name')
    
    # Separar por roles para la vista
    medicos = usuarios.filter(role=2)    # role=2 son médicos
    pacientes = usuarios.filter(role=3)  # role=3 son pacientes
    
    return render(request, 'gestionar_usuarios.html', {
        'usuarios': usuarios,
        'medicos': medicos,
        'pacientes': pacientes,
    })

@login_required
def cancelar_cita_view(request, cita_id):
    """
    VISTA: Cancela una cita existente
    
    PROPÓSITO:
    - Permitir cancelación solo a usuarios autorizados
    - Usar stored procedure para cancelación segura
    - Cambiar estado de la cita a 'CANCELADA'
    """
    
    try:
        cita = Cita.objects.get(id=cita_id)
        
        # VERIFICAR PERMISOS: Admin, médico de la cita, o paciente de la cita
        if not (request.user.is_admin or 
                request.user.id == cita.medico_id or 
                request.user.id == cita.paciente_id):
            messages.error(request, 'No tiene permisos para cancelar esta cita')
            return redirect('historial_citas')
        
        # CANCELAR USANDO STORED PROCEDURE
        with connection.cursor() as cursor:
            cursor.callproc('sp_cancelar_cita', [cita_id])
        
        messages.success(request, 'Cita cancelada exitosamente')
    except Exception as e:
        messages.error(request, f'Error al cancelar cita: {str(e)}')
    
    return redirect('historial_citas')

@csrf_exempt  # Excluir de verificación CSRF para API
@login_required
def api_citas_disponibles(request):
    """
    API: Devuelve horarios disponibles de un médico en una fecha específica
    
    PROPÓSITO:
    - Endpoint para AJAX desde el frontend
    - Calcular horarios libres basado en citas existentes
    - Generar slots de 30 minutos entre 8:00 y 17:00
    """
    
    if request.method == 'POST':
        # Decodificar JSON del request
        data = json.loads(request.body)
        medico_id = data.get('medico_id')
        fecha = data.get('fecha')
        
        # OBTENER HORARIOS YA OCUPADOS
        citas_ocupadas = Cita.objects.filter(
            medico_id=medico_id,
            fecha=fecha,
            estado__in=['PENDIENTE', 'CONFIRMADA']
        ).values_list('hora', flat=True)  # Solo obtener las horas
        
        # GENERAR HORARIOS DISPONIBLES
        # Slots cada 30 minutos desde 8:00 hasta 17:00
        horarios_disponibles = []
        hora_actual = datetime.strptime('08:00', '%H:%M')
        hora_fin = datetime.strptime('17:00', '%H:%M')
        
        while hora_actual < hora_fin:
            hora_str = hora_actual.strftime('%H:%M')
            # Si el horario no está ocupado, agregarlo como disponible
            if hora_str not in [h.strftime('%H:%M') for h in citas_ocupadas]:
                horarios_disponibles.append(hora_str)
            hora_actual += timedelta(minutes=30)  # Incrementar 30 minutos
        
        return JsonResponse({'horarios': horarios_disponibles})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def actualizar_estado_cita(request, cita_id):
    """
    VISTA: Actualiza el estado de una cita (PENDIENTE/CONFIRMADA/COMPLETADA)
    
    PROPÓSITO:
    - Solo admin o el médico de la cita pueden cambiar estado
    - Usar stored procedure para actualización segura
    - Permitir marcar citas como completadas
    """
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        
        # VERIFICAR PERMISOS
        try:
            cita = Cita.objects.get(id=cita_id)
            
            # Solo admin o el médico de la cita pueden cambiar estado
            if not (request.user.is_admin or request.user.id == cita.medico_id):
                messages.error(request, 'No tiene permisos para cambiar el estado de esta cita')
                return redirect('historial_citas')
            
            # ACTUALIZAR ESTADO usando stored procedure
            with connection.cursor() as cursor:
                cursor.callproc('sp_actualizar_estado_cita', [cita_id, nuevo_estado])
            
            messages.success(request, f'Cita marcada como {nuevo_estado}')
        except Exception as e:
            messages.error(request, f'Error al actualizar estado: {str(e)}')
    
    return redirect('historial_citas')

@login_required
def editar_usuario_view(request, user_id):
    """
    VISTA: Permite editar información de un usuario existente (solo admin)
    
    PROPÓSITO:
    - Solo administradores pueden editar usuarios
    - Actualizar datos personales (nombre, email, teléfono, etc.)
    - Cambiar contraseña y enviar notificación por correo
    - Validar que el usuario existe antes de editar
    """
    
    # VERIFICAR PERMISOS
    if not request.user.is_admin:
        messages.error(request, 'No tiene permisos para editar usuarios')
        return redirect('home')
    
    # VERIFICAR QUE EL USUARIO EXISTE
    try:
        usuario = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('gestionar_usuarios')
    
    if request.method == 'POST':
        # ACTUALIZAR DATOS BÁSICOS del usuario
        usuario.first_name = request.POST.get('first_name', usuario.first_name)
        usuario.last_name = request.POST.get('last_name', usuario.last_name)
        usuario.email = request.POST.get('email', usuario.email)
        usuario.phone = request.POST.get('phone', usuario.phone)
        usuario.address = request.POST.get('address', usuario.address)
        
        # CAMBIO DE CONTRASEÑA (opcional)
        nueva_password = request.POST.get('nueva_password')
        if nueva_password:
            # Guardar nueva contraseña (el backend la hasheará automáticamente)
            usuario.password = nueva_password
            
            # ENVIAR CORREO CON NUEVA CONTRASEÑA
            try:
                subject = 'Cambio de Contraseña - Clínica Dermatológica'
                message = f"""
                Estimado/a {usuario.get_full_name()},
                
                Su contraseña ha sido actualizada por el administrador.
                
                Nueva contraseña: {nueva_password}
                
                Por favor, guarde esta información de forma segura.
                
                Atentamente,
                Clínica Dermatológica
                """
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [usuario.email],
                    fail_silently=False,
                )
                messages.success(request, 'Contraseña actualizada y correo enviado')
            except:
                messages.warning(request, 'Contraseña actualizada pero no se pudo enviar el correo')
        
        # GUARDAR CAMBIOS DIRECTAMENTE EN LA BASE DE DATOS
        with connection.cursor() as cursor:
            if nueva_password:
                # Si hay nueva contraseña, actualizarla también
                cursor.execute("""
                    UPDATE auth_user_custom 
                    SET first_name=%s, last_name=%s, email=%s, phone=%s, 
                        address=%s, password=%s, updated_at=NOW()
                    WHERE id=%s
                """, [
                    usuario.first_name, usuario.last_name, usuario.email,
                    usuario.phone, usuario.address, nueva_password, user_id
                ])
            else:
                # Solo actualizar datos personales, no la contraseña
                cursor.execute("""
                    UPDATE auth_user_custom 
                    SET first_name=%s, last_name=%s, email=%s, phone=%s, 
                        address=%s, updated_at=NOW()
                    WHERE id=%s
                """, [
                    usuario.first_name, usuario.last_name, usuario.email,
                    usuario.phone, usuario.address, user_id
                ])
        
        messages.success(request, 'Usuario actualizado exitosamente')
        return redirect('gestionar_usuarios')
    
    # GET REQUEST - Mostrar formulario con datos actuales
    
    # OBTENER DATOS ADICIONALES si es médico
    especialidades = []
    medico_info = None
    if usuario.role == 2:  # Si es médico
        try:
            medico_info = Medico.objects.get(user_id=usuario.id)
            especialidades = Especialidad.objects.all()
        except:
            pass  # Si no tiene registro de médico, ignorar
    
    return render(request, 'editar_usuario.html', {
        'usuario_editar': usuario,
        'especialidades': especialidades,
        'medico_info': medico_info
    })

def logout_view(request):
    """
    VISTA: Maneja el cierre de sesión del usuario
    
    PROPÓSITO:
    - Cerrar la sesión actual del usuario
    - Limpiar todas las variables de sesión
    - Redirigir al login con mensaje de confirmación
    - No requiere autenticación (cualquiera puede cerrar sesión)
    """
    
    logout(request)  # Función de Django para cerrar sesión
    messages.success(request, 'Sesión cerrada exitosamente')
    return redirect('login')

"""
=== RESUMEN GENERAL DEL ARCHIVO views.py ===

FUNCIONES DE CORREO:
- enviar_correo_registro(): Envía credenciales a nuevos usuarios
- enviar_correo_cita(): Notifica cita nueva a paciente y médico

VISTAS DE AUTENTICACIÓN:
- login_view(): Maneja login con backend personalizado
- logout_view(): Cierra sesión y redirige
- registro_view(): Solo admin puede crear usuarios

VISTAS PRINCIPALES:
- home_view(): Dashboard personalizado por rol
- calendario_view(): Vista de calendario con filtros por rol
- agendar_cita_view(): Crear nuevas citas (admin/médicos)

GESTIÓN DE USUARIOS (solo admin):
- gestionar_usuarios_view(): Lista todos los usuarios
- editar_usuario_view(): Modificar datos de usuarios
- eliminar_usuario_view(): Eliminar usuarios del sistema

GESTIÓN DE CITAS:
- historial_citas_view(): Historial filtrado por rol
- cancelar_cita_view(): Cancelar citas existentes
- actualizar_estado_cita(): Cambiar estado de citas

API/AJAX:
- api_citas_disponibles(): Endpoint para obtener horarios libres

CARACTERÍSTICAS IMPORTANTES:
1. Seguridad: Verificación de permisos en cada vista
2. Roles: Admin (1), Médico (2), Paciente (3)
3. SQL directo: Usa stored procedures y consultas optimizadas
4. Notificaciones: Sistema de correos automáticos
5. Filtros: Cada rol ve solo datos relevantes
6. Manejo de errores: Try/catch en operaciones críticas

PERMISOS POR ROL:
- ADMIN: Acceso total, puede gestionar usuarios y ver todo
- MÉDICO: Ve sus citas, puede agendar para sí mismo
- PACIENTE: Solo ve sus propias citas y datos

BASE DE DATOS:
- auth_user_custom: Tabla principal de usuarios
- citas: Tabla de citas médicas
- medicos: Datos adicionales de médicos
- pacientes: Datos adicionales de pacientes
- especialidades: Catálogo de especialidades médicas
"""