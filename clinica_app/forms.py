# clinica_app/forms.py

"""
=== FORMULARIOS DE DJANGO PARA LA CLÍNICA ===

PROPÓSITO:
- Definir formularios para captura y validación de datos
- Aplicar estilos Bootstrap automáticamente
- Validar datos antes de guardar en BD
- Manejar lógica de negocio en la capa de presentación

TIPOS DE FORMULARIOS:
1. LoginForm: Autenticación de usuarios
2. RegistroForm: Creación de nuevos usuarios
3. CitaForm: Agendamiento de citas médicas
"""

from django import forms
from django.contrib.auth.hashers import make_password
from .models import CustomUser, Cita, Especialidad

# ========== FORMULARIO DE LOGIN ==========

class LoginForm(forms.Form):
    """
    FORMULARIO: Login de usuarios al sistema
    
    TIPO: forms.Form (no vinculado a modelo)
    
    PROPÓSITO:
    - Capturar credenciales del usuario
    - Validar que se proporcionen ambos campos
    - Aplicar estilos Bootstrap para UI consistente
    
    CAMPOS:
    - username: Puede ser username o email
    - password: Contraseña en texto plano
    
    USO: En vista login_view() para autenticar usuarios
    """
    
    # CAMPO USERNAME/EMAIL
    username = forms.CharField(
        label='Usuario o Email',      # Etiqueta visible en el formulario
        max_length=150,                # Longitud máxima permitida
        widget=forms.TextInput(attrs={
            'class': 'form-control',   # Clase CSS de Bootstrap
            'placeholder': 'Ingrese su usuario o email'  # Texto de ayuda
        })
    )
    
    # CAMPO CONTRASEÑA
    password = forms.CharField(
        label='Contraseña',            # Etiqueta visible
        widget=forms.PasswordInput(attrs={  # Input tipo password (oculta texto)
            'class': 'form-control',   # Clase CSS de Bootstrap
            'placeholder': 'Ingrese su contraseña'
        })
    )

# ========== FORMULARIO DE REGISTRO ==========

class RegistroForm(forms.ModelForm):
    """
    FORMULARIO: Registro de nuevos usuarios (solo para admins)
    
    TIPO: forms.ModelForm (vinculado al modelo CustomUser)
    
    PROPÓSITO:
    - Crear usuarios de tipo Admin, Médico o Paciente
    - Validar unicidad de email y username
    - Confirmar contraseña con campo adicional
    - Aplicar permisos automáticamente según rol
    
    VALIDACIONES:
    - Email único en el sistema
    - Contraseñas coincidentes
    - Campos requeridos completados
    
    USO: En vista registro_view() para que admin cree usuarios
    """
    
    # OPCIONES DE ROL: Define los 3 tipos de usuarios
    ROLE_CHOICES = [
        (1, 'Admin'),      # Administrador del sistema
        (2, 'Médico'),     # Personal médico
        (3, 'Paciente'),   # Pacientes de la clínica
    ]
    
    # CAMPO CONTRASEÑA PRINCIPAL
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    # CAMPO CONFIRMACIÓN DE CONTRASEÑA
    # No se guarda en BD, solo para validación
    password_confirm = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    # CAMPO ROL: Dropdown con las 3 opciones
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label='Rol',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        """
        CONFIGURACIÓN DEL MODELO:
        - Especifica qué modelo usar (CustomUser)
        - Define qué campos mostrar en el formulario
        - Aplica estilos CSS a cada campo
        """
        model = CustomUser
        
        # CAMPOS A INCLUIR en el formulario
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'phone', 'address']
        
        # WIDGETS: Personalización del HTML de cada campo
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),  # Validación HTML5 de email
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3  # Textarea de 3 líneas de altura
            }),
        }
    
    def clean_password_confirm(self):
        """
        VALIDACIÓN: Verificar que las contraseñas coincidan
        
        PROPÓSITO:
        - Prevenir errores de tipeo en contraseñas
        - Ejecutado automáticamente por Django al validar formulario
        
        PROCESO:
        1. Obtener ambas contraseñas de cleaned_data
        2. Comparar que sean idénticas
        3. Lanzar error si no coinciden
        
        RETORNA: password_confirm si es válida
        LANZA: ValidationError si no coinciden
        """
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        
        # Verificar que ambos campos existan y sean iguales
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Las contraseñas no coinciden')
        
        return password_confirm
    
    def clean_email(self):
        """
        VALIDACIÓN: Verificar que el email sea único
        
        PROPÓSITO:
        - Prevenir emails duplicados en el sistema
        - Ejecutado automáticamente por Django al validar formulario
        
        PROCESO:
        1. Obtener email del formulario
        2. Buscar si ya existe en BD
        3. Lanzar error si existe
        
        RETORNA: email si es único
        LANZA: ValidationError si ya existe
        """
        email = self.cleaned_data.get('email')
        
        # Buscar si el email ya está registrado
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Este email ya está registrado')
        
        return email
    
    def save(self, commit=True):
        """
        MÉTODO SOBRESCRITO: Guardar usuario con lógica personalizada
        
        PARÁMETROS:
        - commit: Si True, guarda inmediatamente en BD
        
        PROPÓSITO:
        - Aplicar lógica de negocio antes de guardar
        - Configurar permisos según el rol
        - Preparar contraseña para el backend
        
        PROCESO:
        1. Crear instancia de usuario sin guardar (commit=False)
        2. Asignar contraseña en texto plano (backend la hasheará)
        3. Configurar role y permisos según selección
        4. Activar usuario automáticamente
        5. Guardar si commit=True
        
        RETORNA: Objeto CustomUser (guardado o no según commit)
        """
        # Crear instancia sin guardar aún
        user = super().save(commit=False)
        
        # CONTRASEÑA: Guardar en texto plano
        # El backend SPAuthBackend la hasheará en el primer login
        user.password = self.cleaned_data['password']
        
        # CONFIGURAR PERMISOS según el rol seleccionado
        user.role = int(self.cleaned_data['role'])
        user.is_active = True  # Usuario activo desde creación
        user.is_staff = (user.role == 1)      # Solo admin puede acceder a admin de Django
        user.is_superuser = (user.role == 1)  # Solo admin tiene todos los permisos
        
        # Guardar en BD si commit=True
        if commit:
            user.save()
        
        return user

# ========== FORMULARIO DE CITAS ==========

class CitaForm(forms.ModelForm):
    """
    FORMULARIO: Agendamiento de citas médicas
    
    TIPO: forms.ModelForm (vinculado al modelo Cita)
    
    PROPÓSITO:
    - Agendar citas entre pacientes y médicos
    - Seleccionar fecha, hora y duración
    - Especificar motivo de consulta
    - Aplicar estilos Bootstrap y validación HTML5
    
    CAMPOS:
    - paciente: Selección de paciente (dropdown)
    - medico: Selección de médico (dropdown)
    - fecha: Selector de fecha (date picker)
    - hora: Selector de hora (time picker)
    - duracion: Minutos de la cita (15-120 en pasos de 15)
    - motivo: Descripción de la consulta (textarea)
    
    VALIDACIONES HTML5:
    - Fecha: Solo fechas válidas del calendario
    - Hora: Intervalos de 30 minutos (step=1800 segundos)
    - Duración: Entre 15 y 120 minutos, pasos de 15
    
    USO: En vista agendar_cita_view() para crear nuevas citas
    """
    
    class Meta:
        """
        CONFIGURACIÓN DEL MODELO:
        - Vinculado a modelo Cita
        - Define campos del formulario
        - Personaliza cada widget con estilos y validaciones
        """
        model = Cita
        
        # CAMPOS A INCLUIR en el formulario
        fields = ['paciente', 'medico', 'fecha', 'hora', 'duracion', 'motivo']
        
        # WIDGETS: Personalización detallada de cada campo
        widgets = {
            # SELECCIÓN DE PACIENTE: Dropdown con todos los pacientes activos
            'paciente': forms.Select(attrs={'class': 'form-control'}),
            
            # SELECCIÓN DE MÉDICO: Dropdown con todos los médicos activos
            'medico': forms.Select(attrs={'class': 'form-control'}),
            
            # FECHA DE LA CITA: Date picker HTML5
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'  # Activa date picker nativo del navegador
            }),
            
            # HORA DE LA CITA: Time picker HTML5
            'hora': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',      # Activa time picker nativo
                'step': '1800'       # Intervalos de 30 minutos (1800 segundos)
            }),
            
            # DURACIÓN: Input numérico con restricciones
            'duracion': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',    # Mínimo 15 minutos
                'max': '120',   # Máximo 2 horas
                'step': '15'    # Incrementos de 15 minutos
            }),
            
            # MOTIVO: Textarea para descripción
            'motivo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,      # 3 líneas de altura
                'placeholder': 'Describa el motivo de la consulta'
            }),
        }

"""
=== RESUMEN GENERAL DEL ARCHIVO forms.py ===

FORMULARIOS IMPLEMENTADOS:
1. LoginForm: Autenticación simple con username/email y password
2. RegistroForm: Creación completa de usuarios con roles
3. CitaForm: Agendamiento de citas médicas

VALIDACIONES IMPLEMENTADAS:
- Email único en el sistema
- Contraseñas coincidentes en registro
- Campos requeridos verificados automáticamente
- Validaciones HTML5 (fecha, hora, números)

CARACTERÍSTICAS:
✅ Estilos Bootstrap aplicados automáticamente
✅ Placeholders informativos en campos
✅ Validación del lado del cliente (HTML5)
✅ Validación del lado del servidor (Django)
✅ Mensajes de error personalizados
✅ Tipos de input específicos (email, password, date, time)

INTEGRACIÓN CON VISTAS:
- LoginForm → login_view()
- RegistroForm → registro_view()
- CitaForm → agendar_cita_view()

SEGURIDAD:
- Contraseñas ocultas (PasswordInput)
- Validación de unicidad de email
- Confirmación de contraseña en registro
- Permisos aplicados según rol

USABILIDAD:
- Dropdowns para selecciones (paciente, médico, rol)
- Date/time pickers nativos del navegador
- Restricciones de duración (15-120 min)
- Intervalos de tiempo de 30 minutos
- Textareas dimensionadas apropiadamente

PROCESAMIENTO:
1. Usuario llena formulario en template
2. Django valida automáticamente al enviar
3. Métodos clean_* ejecutan validaciones personalizadas
4. Si válido, método save() procesa y guarda
5. Si inválido, muestra errores en el formulario

FLUJO DE VALIDACIÓN:
GET → Formulario vacío se muestra
POST → Django valida automáticamente:
  1. Validaciones de campo (max_length, required, etc.)
  2. Validaciones personalizadas (clean_email, clean_password_confirm)
  3. Si todo válido → save() y redirect
  4. Si inválido → Re-renderizar con errores

PERSONALIZACIÓN:
- Todos los campos tienen clase 'form-control' para Bootstrap
- Widgets personalizados para mejor UX
- Labels en español para usuarios
- Placeholders descriptivos donde necesario
"""