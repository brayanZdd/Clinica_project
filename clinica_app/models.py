# clinica_app/models.py

# Importaciones necesarias para Django ORM y conexión directa a BD
from django.db import models, connection

# ========== USUARIO (tabla: auth_user_custom) ==========
class CustomUser(models.Model):
    """
    MODELO: Usuario personalizado del sistema de clínica
    
    PROPÓSITO:
    - Reemplaza el sistema de usuarios por defecto de Django
    - Maneja 3 tipos de roles: Admin (1), Médico (2), Paciente (3)
    - Se conecta a tabla existente 'auth_user_custom' en la BD
    - Funciona con backend de autenticación personalizado
    
    TABLA BD: auth_user_custom
    CAMPOS PRINCIPALES: username, email, password, role, nombres, teléfono
    """
    
    # CAMPOS BÁSICOS DE IDENTIFICACIÓN
    id = models.IntegerField(primary_key=True)  # Clave primaria - INT AUTO_INCREMENT en BD
    username = models.CharField(max_length=150, unique=True)  # Nombre de usuario único
    email = models.CharField(max_length=254, unique=True)     # Email único del usuario
    password = models.CharField(max_length=128)              # Contraseña (se guarda como texto plano)
    
    # INFORMACIÓN PERSONAL
    first_name = models.CharField(max_length=150, blank=True)  # Nombre(s)
    last_name = models.CharField(max_length=150, blank=True)   # Apellido(s)
    phone = models.CharField(max_length=20, blank=True)        # Teléfono de contacto
    address = models.TextField(blank=True)                     # Dirección completa
    
    # SISTEMA DE ROLES Y PERMISOS
    role = models.IntegerField()  # 1=Admin, 2=Médico, 3=Paciente - Define el tipo de usuario
    is_active = models.BooleanField(default=True)      # Usuario activo/inactivo
    is_staff = models.BooleanField(default=False)      # Puede acceder al admin de Django
    is_superuser = models.BooleanField(default=False)  # Permisos de superusuario
    
    # CAMPOS DE AUDITORÍA Y TIMESTAMP
    date_joined = models.DateTimeField(null=True, blank=True)   # Fecha de registro
    last_login = models.DateTimeField(null=True, blank=True)    # Último acceso
    created_at = models.DateTimeField(null=True, blank=True)    # Fecha de creación
    updated_at = models.DateTimeField(null=True, blank=True)    # Última modificación

    class Meta:
        db_table = 'auth_user_custom'  # Nombre exacto de la tabla en BD
        managed = False  # ¡CRÍTICO! Django NO maneja esta tabla (no crear/modificar)

    # PROPIEDADES REQUERIDAS PARA AUTENTICACIÓN DE DJANGO
    @property
    def is_authenticated(self):
        """
        PROPIEDAD: Requerida por Django para el sistema de autenticación
        PROPÓSITO: Siempre retorna True para usuarios válidos
        USO: En decoradores @login_required y templates
        """
        return True

    def get_full_name(self):
        """
        MÉTODO: Combina nombre y apellido en un string
        PROPÓSITO: Mostrar nombre completo en interfaces y correos
        RETORNA: "Nombre Apellido" o string vacío si no hay nombres
        USO: En templates, correos, historiales
        """
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    # PROPIEDADES DE VERIFICACIÓN DE ROLES
    @property
    def is_admin(self):
        """
        PROPIEDAD: Verifica si el usuario es administrador
        PROPÓSITO: Control de acceso en vistas y templates
        RETORNA: True si role == 1 (Admin)
        USO: Verificar permisos para gestionar usuarios, ver todo el sistema
        """
        return int(self.role) == 1

    @property
    def is_medico(self):
        """
        PROPIEDAD: Verifica si el usuario es médico
        PROPÓSITO: Control de acceso específico para médicos
        RETORNA: True si role == 2 (Médico)
        USO: Mostrar calendarios de citas, agendar para sí mismo
        """
        return int(self.role) == 2

    @property
    def is_paciente(self):
        """
        PROPIEDAD: Verifica si el usuario es paciente
        PROPÓSITO: Control de acceso para vista de paciente
        RETORNA: True si role == 3 (Paciente)
        USO: Mostrar solo citas propias, historial personal
        """
        return int(self.role) == 3
    
    def get_role_display(self):
        """
        MÉTODO: Convierte el número de rol a texto legible
        PROPÓSITO: Mostrar el rol en interfaces de usuario
        RETORNA: 'Admin', 'Médico', 'Paciente' o 'Desconocido'
        USO: En listas de usuarios, correos de bienvenida
        """
        roles = {
            1: 'Admin',
            2: 'Médico', 
            3: 'Paciente'
        }
        return roles.get(self.role, 'Desconocido')

    def __str__(self):
        """
        MÉTODO: Representación en string del objeto
        PROPÓSITO: Identificar el usuario en admin y debugging
        RETORNA: Username del usuario
        """
        return self.username


# ========== ESPECIALIDADES (tabla: especialidades) ==========
class Especialidad(models.Model):
    """
    MODELO: Catálogo de especialidades médicas
    
    PROPÓSITO:
    - Definir las diferentes especialidades que puede tener un médico
    - Tabla de referencia para clasificar médicos
    - Ejemplos: Dermatología, Cardiología, Pediatría, etc.
    
    TABLA BD: especialidades
    RELACIÓN: Un médico tiene UNA especialidad (OneToMany)
    """
    
    id = models.AutoField(primary_key=True)          # ID autoincremental
    nombre = models.CharField(max_length=100)        # Nombre de la especialidad
    descripcion = models.TextField(blank=True)       # Descripción detallada (opcional)
    created_at = models.DateTimeField(null=True, blank=True)  # Fecha de creación

    class Meta:
        db_table = 'especialidades'  # Tabla exacta en BD
        managed = False             # Django NO maneja esta tabla

    def __str__(self):
        """
        MÉTODO: Representación en string
        PROPÓSITO: Mostrar nombre de especialidad en dropdowns y listas
        RETORNA: Nombre de la especialidad
        """
        return self.nombre


# ========== MÉDICOS (tabla: medicos) ==========
class Medico(models.Model):
    """
    MODELO: Información adicional específica de médicos
    
    PROPÓSITO:
    - Extiende CustomUser con datos específicos de médicos
    - Almacena horarios, especialidad, número colegiado
    - Se relaciona 1:1 con CustomUser (un usuario médico = un registro médico)
    
    TABLA BD: medicos
    RELACIONES: 
    - OneToOne con CustomUser (user_id)
    - ForeignKey con Especialidad (especialidad_id)
    """
    
    id = models.AutoField(primary_key=True)
    
    # RELACIÓN 1:1 CON USUARIO
    user = models.OneToOneField(
        CustomUser,                    # Modelo relacionado
        on_delete=models.CASCADE,      # Si se elimina usuario, eliminar médico
        db_column='user_id',           # Columna real en BD
        related_name='medico'          # Acceso: usuario.medico
    )
    
    # RELACIÓN CON ESPECIALIDAD
    especialidad = models.ForeignKey(
        Especialidad,                  # Modelo relacionado
        on_delete=models.SET_NULL,     # Si se elimina especialidad, poner NULL
        null=True,                     # Puede ser NULL
        db_column='especialidad_id',   # Columna real en BD
        related_name='medicos'         # Acceso: especialidad.medicos.all()
    )
    
    # INFORMACIÓN PROFESIONAL
    numero_colegiado = models.CharField(max_length=50, blank=True)  # Número de colegio médico
    
    # CONFIGURACIÓN DE HORARIOS
    horario_inicio = models.TimeField(null=True, blank=True)  # Hora de inicio (ej: 08:00)
    horario_fin = models.TimeField(null=True, blank=True)     # Hora de fin (ej: 17:00)
    dias_laborales = models.CharField(max_length=50, blank=True)  # "LUN,MAR,MIE,JUE,VIE"
    
    # AUDITORÍA
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'medicos'  # Tabla exacta en BD
        managed = False       # Django NO maneja esta tabla

    def __str__(self):
        """
        MÉTODO: Representación en string
        PROPÓSITO: Mostrar nombre del médico con título profesional
        RETORNA: "Dr./Dra. Nombre Completo" o "Dr./Dra. username"
        USO: En listas de médicos, citas, correos
        """
        return f"Dr./Dra. {self.user.get_full_name() or self.user.username}"


# ========== PACIENTES (tabla: pacientes) ==========
class Paciente(models.Model):
    """
    MODELO: Información adicional específica de pacientes
    
    PROPÓSITO:
    - Extiende CustomUser con datos médicos del paciente
    - Almacena historial médico básico (alergias, tipo sangre, etc.)
    - Se relaciona 1:1 con CustomUser (un usuario paciente = un registro paciente)
    
    TABLA BD: pacientes
    RELACIÓN: OneToOne con CustomUser (user_id)
    """
    
    id = models.AutoField(primary_key=True)
    
    # RELACIÓN 1:1 CON USUARIO
    user = models.OneToOneField(
        CustomUser,                    # Modelo relacionado
        on_delete=models.CASCADE,      # Si se elimina usuario, eliminar paciente
        db_column='user_id',           # Columna real en BD
        related_name='paciente'        # Acceso: usuario.paciente
    )
    
    # INFORMACIÓN MÉDICA BÁSICA
    fecha_nacimiento = models.DateField(null=True, blank=True)  # Para calcular edad
    tipo_sangre = models.CharField(max_length=5, blank=True)    # A+, O-, etc.
    alergias = models.TextField(blank=True)                     # Alergias conocidas
    observaciones = models.TextField(blank=True)                # Notas médicas adicionales
    
    # AUDITORÍA
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pacientes'  # Tabla exacta en BD
        managed = False         # Django NO maneja esta tabla

    def __str__(self):
        """
        MÉTODO: Representación en string
        PROPÓSITO: Identificar al paciente en listas y referencias
        RETORNA: Nombre completo del paciente o username
        USO: En historiales, listas de citas, comunicaciones
        """
        return self.user.get_full_name() or self.user.username


# ========== CITAS (tabla: citas) ==========
class Cita(models.Model):
    """
    MODELO: Sistema de citas médicas
    
    PROPÓSITO:
    - Gestionar todas las citas entre médicos y pacientes
    - Controlar estados (pendiente, confirmada, cancelada, completada)
    - Evitar conflictos de horarios con constraint único
    - Almacenar detalles de la consulta
    
    TABLA BD: citas
    RELACIONES:
    - ForeignKey con CustomUser (paciente_id)
    - ForeignKey con CustomUser (medico_id)
    CONSTRAINT: unique_cita (medico, fecha, hora)
    """
    
    # OPCIONES DE ESTADO DE LA CITA
    ESTADOS = (
        ('PENDIENTE', 'PENDIENTE'),      # Agendada pero no confirmada
        ('CONFIRMADA', 'CONFIRMADA'),    # Confirmada por ambas partes
        ('CANCELADA', 'CANCELADA'),      # Cancelada por cualquier motivo
        ('COMPLETADA', 'COMPLETADA'),    # Cita realizada exitosamente
    )

    id = models.AutoField(primary_key=True)
    
    # RELACIONES CON USUARIOS (PACIENTE Y MÉDICO)
    paciente = models.ForeignKey(
        CustomUser,                           # Usuario que es paciente
        on_delete=models.CASCADE,             # Si se elimina usuario, eliminar citas
        db_column='paciente_id',              # Columna real en BD
        related_name='citas_como_paciente'    # Acceso: usuario.citas_como_paciente.all()
    )
    medico = models.ForeignKey(
        CustomUser,                           # Usuario que es médico
        on_delete=models.CASCADE,             # Si se elimina usuario, eliminar citas
        db_column='medico_id',                # Columna real en BD
        related_name='citas_como_medico'      # Acceso: usuario.citas_como_medico.all()
    )
    
    # INFORMACIÓN DE PROGRAMACIÓN
    fecha = models.DateField()                        # Fecha de la cita (YYYY-MM-DD)
    hora = models.TimeField()                         # Hora de inicio (HH:MM)
    duracion = models.IntegerField(default=30)        # Duración en minutos (default: 30)
    
    # DETALLES DE LA CITA
    motivo = models.TextField(blank=True)             # Razón de la consulta
    estado = models.CharField(                        # Estado actual de la cita
        max_length=20, 
        choices=ESTADOS, 
        default='PENDIENTE'
    )
    observaciones = models.TextField(blank=True)      # Notas adicionales del médico
    
    # AUDITORÍA
    created_at = models.DateTimeField(null=True, blank=True)   # Cuándo se agendó
    updated_at = models.DateTimeField(null=True, blank=True)   # Última modificación

    class Meta:
        db_table = 'citas'  # Tabla exacta en BD
        managed = False     # Django NO maneja esta tabla
        
        # CONSTRAINT ÚNICO: Un médico no puede tener 2 citas al mismo tiempo
        unique_together = (('medico', 'fecha', 'hora'),)  # Coincide con unique_cita en BD

    def __str__(self):
        """
        MÉTODO: Representación en string
        PROPÓSITO: Identificar la cita de forma legible
        RETORNA: "YYYY-MM-DD HH:MM - Nombre del Paciente"
        USO: En listas, logs, debugging
        """
        return f"{self.fecha} {self.hora} - {self.paciente.get_full_name()}"


# ======== FUNCIONES AUXILIARES: Llamadas a Stored Procedures ========

def obtener_citas_fecha(fecha_inicio, fecha_fin):
    """
    FUNCIÓN: Obtiene citas en un rango de fechas usando stored procedure
    
    PARÁMETROS:
    - fecha_inicio: Fecha inicial del rango (YYYY-MM-DD)
    - fecha_fin: Fecha final del rango (YYYY-MM-DD)
    
    PROPÓSITO:
    - Usar SP existente 'sp_obtener_citas_fecha' para consultas optimizadas
    - Retornar datos como lista de diccionarios para fácil manejo
    
    RETORNA: Lista de diccionarios con datos de citas
    [{'id': 1, 'fecha': '2024-01-15', 'paciente': 'Juan Pérez', ...}, ...]
    
    USO: Cuando necesites citas de un período específico con JOIN optimizado
    """
    with connection.cursor() as cur:
        # Llamar al stored procedure con los parámetros
        cur.callproc('sp_obtener_citas_fecha', [fecha_inicio, fecha_fin])
        
        # Obtener nombres de columnas del resultado
        cols = [c[0] for c in cur.description]
        
        # Convertir cada fila a diccionario usando nombres de columna
        return [dict(zip(cols, r)) for r in cur.fetchall()]

def obtener_medicos_disponibles():
    """
    FUNCIÓN: Obtiene lista de médicos activos usando stored procedure
    
    PROPÓSITO:
    - Usar SP existente 'sp_obtener_medicos' para consulta optimizada
    - Obtener médicos con datos de especialidad y horarios
    - Filtrar solo médicos activos y disponibles
    
    RETORNA: Lista de diccionarios con datos de médicos
    [{'id': 1, 'nombre': 'Dr. García', 'especialidad': 'Cardiología', ...}, ...]
    
    USO: Para poblar dropdowns de médicos en formularios de citas
    """
    with connection.cursor() as cur:
        # Llamar al stored procedure (sin parámetros)
        cur.callproc('sp_obtener_medicos')
        
        # Obtener nombres de columnas del resultado
        cols = [c[0] for c in cur.description]
        
        # Convertir cada fila a diccionario usando nombres de columna
        return [dict(zip(cols, r)) for r in cur.fetchall()]

"""
=== RESUMEN GENERAL DEL ARCHIVO models.py ===

MODELOS PRINCIPALES:
1. CustomUser: Usuario base con sistema de roles (admin/médico/paciente)
2. Especialidad: Catálogo de especialidades médicas
3. Medico: Extensión de usuario para médicos (horarios, especialidad)
4. Paciente: Extensión de usuario para pacientes (datos médicos)
5. Cita: Sistema de citas médicas con estados y validaciones

CARACTERÍSTICAS IMPORTANTES:
- managed = False: Django NO modifica las tablas existentes
- db_column: Mapeo exacto con columnas de BD existente
- related_name: Acceso inverso a relaciones (usuario.medico, usuario.citas_como_paciente)
- unique_together: Previene conflictos de horarios en citas

RELACIONES:
- CustomUser 1:1 Medico (un usuario médico tiene un perfil médico)
- CustomUser 1:1 Paciente (un usuario paciente tiene un perfil paciente)
- Especialidad 1:N Medico (una especialidad tiene muchos médicos)
- CustomUser 1:N Citas (como médico: un médico tiene muchas citas)
- CustomUser 1:N Citas (como paciente: un paciente tiene muchas citas)

SISTEMA DE ROLES:
- role = 1: Administrador (gestiona sistema completo)
- role = 2: Médico (ve sus citas, agenda para sí mismo)
- role = 3: Paciente (ve solo sus citas)

FUNCIONES AUXILIARES:
- obtener_citas_fecha(): Consulta optimizada de citas por rango
- obtener_medicos_disponibles(): Lista de médicos activos para formularios

PROPIEDADES ÚTILES:
- is_admin, is_medico, is_paciente: Verificación rápida de roles
- get_full_name(): Nombre completo para mostrar en interfaces
- get_role_display(): Nombre del rol en español para interfaces
"""