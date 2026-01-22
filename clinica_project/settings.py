# clinica_project/settings.py

"""
=== ARCHIVO DE CONFIGURACIÓN PRINCIPAL DE DJANGO ===

PROPÓSITO:
- Configurar todos los aspectos del proyecto Django
- Definir conexión a base de datos MySQL existente
- Configurar sistema de autenticación personalizado
- Establecer configuración de correos electrónicos
- Configurar archivos estáticos y media
- Definir zona horaria y idioma para Guatemala

IMPORTANTE: Este archivo contiene configuraciones críticas del sistema
"""

import os
from pathlib import Path

# ========== CONFIGURACIÓN BÁSICA DEL PROYECTO ==========

# DIRECTORIO BASE: Ruta absoluta donde está el proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
# __file__ = este archivo settings.py
# .parent.parent = sube 2 niveles para llegar a la raíz del proyecto

# CLAVE SECRETA: Usada para hash, cookies, sesiones, CSRF tokens
SECRET_KEY = 'django-insecure-tu-clave-secreta-aqui-cambiar-en-produccion'
# ⚠️ CRÍTICO: Cambiar en producción por una clave única y segura
# Generar nueva: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# MODO DEBUG: Muestra errores detallados y información de desarrollo
DEBUG = True
# ⚠️ IMPORTANTE: Cambiar a False en producción para seguridad
# En producción: oculta errores, mejora rendimiento, aumenta seguridad

# HOSTS PERMITIDOS: Dominios/IPs que pueden servir esta aplicación
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
# En producción agregar: ['midominio.com', 'www.midominio.com', 'IP_servidor']
# Previene ataques HTTP Host header

# ========== APLICACIONES INSTALADAS ==========

INSTALLED_APPS = [
    # APPS DE DJANGO (sistema)
    # 'django.contrib.admin',  # ❌ DESACTIVADO: Evita conflictos con BD existente
    'django.contrib.auth',        # ✅ Sistema de autenticación (necesario para login)
    'django.contrib.contenttypes', # ✅ Sistema de tipos de contenido
    'django.contrib.sessions',     # ✅ Manejo de sesiones de usuario
    'django.contrib.messages',     # ✅ Sistema de mensajes flash
    'django.contrib.staticfiles',  # ✅ Manejo de archivos CSS/JS/imágenes
    
    # APPS PROPIAS
    'clinica_app',    # ✅ Aplicación principal de la clínica
    
    # APPS EXTERNAS
    'crispy_forms',   # ✅ Mejora el rendering de formularios con Bootstrap
]

"""
NOTA IMPORTANTE sobre django.contrib.admin:
- Está comentado porque crearía conflictos con la estructura de BD existente
- El admin de Django espera ciertas tablas que no tenemos
- Usamos nuestro propio sistema de administración en las vistas
"""

# ========== MIDDLEWARE (Procesamientos intermedios) ==========

MIDDLEWARE = [
    # SEGURIDAD: Añade headers de seguridad HTTP
    'django.middleware.security.SecurityMiddleware',
    
    # SESIONES: Maneja cookies y datos de sesión del usuario
    'django.contrib.sessions.middleware.SessionMiddleware',
    
    # COMÚN: Procesamiento general de requests/responses
    'django.middleware.common.CommonMiddleware',
    
    # CSRF: Protección contra ataques Cross-Site Request Forgery
    'django.middleware.csrf.CsrfViewMiddleware',
    
    # AUTENTICACIÓN: Añade usuario actual al request
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # MENSAJES: Permite mensajes flash entre requests
    'django.contrib.messages.middleware.MessageMiddleware',
    
    # CLICKJACKING: Protección contra ataques de clickjacking
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ========== CONFIGURACIÓN DE URLs ==========

# ARCHIVO PRINCIPAL DE URLs: Define dónde están las rutas del proyecto
ROOT_URLCONF = 'clinica_project.urls'
# Apunta al archivo clinica_project/urls.py que incluye las URLs de la app

# ========== CONFIGURACIÓN DE TEMPLATES ==========

TEMPLATES = [
    {
        # MOTOR DE TEMPLATES: Django Template Language (DTL)
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        
        # DIRECTORIOS: Dónde buscar templates (vacío = usar APP_DIRS)
        'DIRS': [],
        
        # AUTO-DESCUBRIMIENTO: Buscar templates en carpeta templates/ de cada app
        'APP_DIRS': True,
        
        # PROCESADORES DE CONTEXTO: Variables disponibles en todos los templates
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',    # {{ debug }}
                'django.template.context_processors.request',  # {{ request }}
                'django.contrib.auth.context_processors.auth', # {{ user }}
                'django.contrib.messages.context_processors.messages', # {{ messages }}
            ],
        },
    },
]

# ========== CONFIGURACIÓN WSGI ==========

# APLICACIÓN WSGI: Para deployment en servidores web
WSGI_APPLICATION = 'clinica_project.wsgi.application'

# ========== CONFIGURACIÓN DE BASE DE DATOS ==========

DATABASES = {
    'default': {
        # MOTOR: MySQL/MariaDB
        'ENGINE': 'django.db.backends.mysql',
        
        # DATOS DE CONEXIÓN: Base de datos existente en FreeSQLDatabase
        'NAME': 'clinica_db',                    # Nombre de la BD
        'USER': 'root',                    # Usuario de BD
        'PASSWORD': '',               # Contraseña de BD
        'HOST': 'localhost',     # Servidor de BD
        'PORT': '3307',                         # Puerto MySQL estándar
        
        # OPCIONES ADICIONALES
        'OPTIONS': {
            'charset': 'utf8mb4',               # Soporte completo UTF-8 (emojis, acentos)
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",  # Modo estricto SQL
        }
    }
}

"""
IMPORTANTE sobre la base de datos:
- Conecta a una BD MySQL existente con datos reales
- NO usar migraciones (managed=False en models)
- La estructura ya existe: tablas, SPs, funciones, etc.
- Django solo lee/escribe, no modifica estructura
"""

# ========== SISTEMA DE AUTENTICACIÓN PERSONALIZADO ==========

AUTHENTICATION_BACKENDS = [
    # BACKEND PERSONALIZADO: Usa stored procedure para login
    'clinica_app.backends.SPAuthBackend',
]

"""
EXPLICACIÓN del backend personalizado:
- Reemplaza el sistema de auth por defecto de Django
- Usa stored procedure 'sp_login' en lugar de consultas ORM
- Permite autenticación con contraseñas en texto plano
- Maneja el sistema de roles personalizado (1=admin, 2=médico, 3=paciente)
"""

# ========== VALIDADORES DE CONTRASEÑA ==========

AUTH_PASSWORD_VALIDATORS = [
    # SIMILITUD: Evita contraseñas similares al username/email
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    # LONGITUD MÍNIMA: Requiere mínimo 8 caracteres
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    # CONTRASEÑAS COMUNES: Evita contraseñas muy obvias
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    # SOLO NÚMEROS: Evita contraseñas que son solo números
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

"""
NOTA: Estos validadores se aplican en formularios Django
Como usamos SP para login, no afectan la autenticación actual
Útiles si implementas cambio de contraseña desde la interfaz
"""

# ========== CONFIGURACIÓN REGIONAL ==========

# IDIOMA: Español de Guatemala
LANGUAGE_CODE = 'es-gt'
# Afecta: mensajes del admin, formatos de fecha, mensajes de error

# ZONA HORARIA: Centroamérica
TIME_ZONE = 'America/Guatemala'
# Afecta: timestamps en BD, fechas mostradas en templates

# INTERNACIONALIZACIÓN: Habilita traducción de textos
USE_I18N = True

# ZONAS HORARIAS: Usar timezone-aware datetimes
USE_TZ = True

# ========== ARCHIVOS ESTÁTICOS (CSS, JS, IMÁGENES) ==========

# URL BASE: Cómo acceder a archivos estáticos desde el navegador
STATIC_URL = '/static/'
# Ejemplo: /static/css/style.css

# DIRECTORIO DE PRODUCCIÓN: Dónde se recopilan todos los archivos estáticos
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Se usa con: python manage.py collectstatic

# ========== ARCHIVOS MEDIA (subidos por usuarios) ==========

# URL BASE: Cómo acceder a archivos subidos desde el navegador
MEDIA_URL = '/media/'
# Ejemplo: /media/uploads/foto_perfil.jpg

# DIRECTORIO: Dónde se guardan archivos subidos
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ========== CONFIGURACIÓN DE MODELOS ==========

# CAMPO AUTO POR DEFECTO: Tipo de primary key automática
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========== CONFIGURACIÓN DE LOGIN/LOGOUT ==========

# URL DE LOGIN: A dónde redirigir si no está autenticado
LOGIN_URL = 'login'
# Se usa en @login_required

# REDIRECCIÓN DESPUÉS DE LOGIN: A dónde ir tras login exitoso
LOGIN_REDIRECT_URL = 'home'

# REDIRECCIÓN DESPUÉS DE LOGOUT: A dónde ir tras cerrar sesión
LOGOUT_REDIRECT_URL = 'login'

# ========== CONFIGURACIÓN DE CORREO ELECTRÓNICO ==========

# BACKEND: Usar SMTP real para enviar correos
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# CONFIGURACIÓN SMTP: Gmail como proveedor
EMAIL_HOST = 'smtp.gmail.com'           # Servidor SMTP de Gmail
EMAIL_PORT = 587                        # Puerto para TLS
EMAIL_USE_TLS = True                    # Usar encriptación TLS

# CREDENCIALES: Cuenta de Gmail para enviar correos
EMAIL_HOST_USER = 'ofmers1@gmail.com'   # Email del remitente
EMAIL_HOST_PASSWORD = 'sdobentaxaulyffr'  # App password de Gmail

"""
CONFIGURACIÓN DE CORREO - IMPORTANTE:
- EMAIL_HOST_PASSWORD debe ser una "App Password" de Gmail, NO la contraseña normal
- Para obtener App Password:
  1. Ir a Google Account settings
  2. Security → 2-Step Verification (debe estar habilitado)
  3. App passwords → Generate new
  4. Usar esa contraseña de 16 caracteres aquí

USOS del sistema de correo:
- Enviar credenciales a nuevos usuarios registrados
- Notificar citas agendadas a pacientes y médicos
- Enviar nuevas contraseñas cuando admin las cambia
"""

# ========== CONFIGURACIÓN DE CRISPY FORMS ==========

# TEMPLATE PACK: Usar Bootstrap 4 para styling de formularios
CRISPY_TEMPLATE_PACK = 'bootstrap4'

"""
CRISPY FORMS:
- Mejora automáticamente el aspecto de los formularios Django
- Aplica clases CSS de Bootstrap automáticamente
- Hace formularios responsivos y profesionales
- Se usa en templates con: {% load crispy_forms_tags %} y {{ form|crispy }}
"""

# ========== CONFIGURACIÓN ALTERNATIVA PARA DESARROLLO ==========

# OPCIÓN DE DESARROLLO: Mostrar emails en consola en lugar de enviarlos
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

"""
BACKEND DE CONSOLA:
- Para desarrollo/pruebas sin enviar correos reales
- Los emails aparecen en la terminal donde corre el servidor
- Útil para debug sin spam de correos reales
- Descomentar esta línea y comentar la configuración SMTP para usarlo
"""

"""
=== RESUMEN GENERAL DEL ARCHIVO settings.py ===

CONFIGURACIONES CRÍTICAS:
1. Conexión a BD MySQL existente (no usar migraciones)
2. Backend de autenticación personalizado con SP
3. Sistema de correos para notificaciones automáticas
4. Configuración regional para Guatemala (zona horaria, idioma)

CONFIGURACIONES DE SEGURIDAD:
- SECRET_KEY: Cambiar en producción
- DEBUG = False en producción
- ALLOWED_HOSTS: Agregar dominio real en producción
- CSRF y middleware de seguridad habilitados

CARACTERÍSTICAS ESPECIALES:
- Admin de Django deshabilitado (conflictos con BD)
- Crispy Forms para formularios bonitos
- Sistema de archivos estáticos configurado
- Redirecciones automáticas de login/logout

VARIABLES DE ENTORNO RECOMENDADAS (producción):
- SECRET_KEY como variable de entorno
- Credenciales de BD como variables de entorno
- EMAIL_HOST_PASSWORD como variable de entorno
- DEBUG = False

DEPENDENCIAS EXTERNAS:
- mysqlclient: Para conexión MySQL
- django-crispy-forms: Para formularios mejorados
- Bootstrap 4: Para estilos CSS (crispy forms)
"""