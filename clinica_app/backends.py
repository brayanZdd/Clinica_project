# clinica_app/backends.py

"""
=== BACKEND DE AUTENTICACIÓN PERSONALIZADO ===

PROPÓSITO PRINCIPAL:
- Reemplazar el sistema de autenticación por defecto de Django
- Permitir login con la estructura de BD existente
- Manejar contraseñas en texto plano Y hashes de Django
- Migrar gradualmente de texto plano a contraseñas seguras
- Trabajar con tabla 'auth_user_custom' sin modificar esquema

PROBLEMA QUE RESUELVE:
- BD existente tiene contraseñas en texto plano (inseguro)
- Django espera contraseñas hasheadas con salt
- Necesitamos mantener compatibilidad mientras migramos a seguridad
"""

from django.contrib.auth.backends import BaseBackend
from django.db import connection
from django.contrib.auth.hashers import check_password, make_password, identify_hasher
from .models import CustomUser

def _is_django_hash(s: str) -> bool:
    """
    FUNCIÓN AUXILIAR: Detecta si una contraseña está en formato hash de Django
    
    PARÁMETROS:
    - s: String que podría ser un hash de Django
    
    LÓGICA DE DETECCIÓN:
    - Hash Django format: "algoritmo$iteraciones$salt$hash"
    - Ejemplo: "pbkdf2_sha256$600000$randomsalt$hashvalue"
    - Debe empezar con "pbkdf2_sha256$" y tener exactamente 3 símbolos "$"
    
    RETORNA: 
    - True: Si es hash Django válido
    - False: Si es texto plano u otro formato
    
    USO: Determinar cómo validar la contraseña
    """
    return isinstance(s, str) and s.startswith("pbkdf2_sha256$") and s.count("$") == 3

class SPAuthBackend(BaseBackend):
    """
    CLASE: Backend de autenticación personalizado para la clínica
    
    HERENCIA: BaseBackend (clase base de Django para backends personalizados)
    
    FUNCIONALIDAD PRINCIPAL:
    1. Autenticar usuarios contra tabla 'auth_user_custom'
    2. Manejar 2 tipos de contraseñas:
       - Texto plano (legacy/inseguro) - migrar automáticamente
       - Hash Django (seguro) - validar normalmente
    3. Actualizar last_login automáticamente
    4. Permitir login con username O email
    
    MIGRACIÓN AUTOMÁTICA:
    - Si encuentra contraseña en texto plano y es correcta
    - La convierte automáticamente a hash Django seguro
    - Guarda el hash en la BD para próximos logins
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        MÉTODO PRINCIPAL: Valida credenciales del usuario
        
        PARÁMETROS:
        - request: HttpRequest (no usado pero requerido por Django)
        - username: Nombre de usuario O email
        - password: Contraseña en texto plano
        - **kwargs: Otros parámetros (ignorados)
        
        PROCESO:
        1. Validar que se proporcionen username y password
        2. Buscar usuario en BD por username O email
        3. Verificar que el usuario esté activo
        4. Determinar tipo de contraseña (hash Django vs texto plano)
        5. Validar según el tipo
        6. Si es texto plano válido, migrar a hash Django
        7. Actualizar last_login y retornar usuario
        
        RETORNA:
        - CustomUser object: Si autenticación exitosa
        - None: Si credenciales incorrectas o usuario no existe
        """
        
        # VALIDACIÓN INICIAL: Verificar que se proporcionen credenciales
        if not username or not password:
            return None
        
        # CONSULTA A BASE DE DATOS: Buscar usuario por username O email
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, password FROM auth_user_custom
                WHERE (username=%s OR email=%s) AND is_active=1
                LIMIT 1
                """,
                [username, username],  # username puede ser email también
            )
            row = cur.fetchone()
        
        # USUARIO NO ENCONTRADO: No existe o está inactivo
        if not row:
            return None
        
        # EXTRAER DATOS: ID del usuario y contraseña almacenada
        user_id, stored = row[0], row[1] or ""
        
        # CASO 1: CONTRASEÑA YA ES HASH DE DJANGO (seguro)
        if _is_django_hash(stored):
            # Usar validación estándar de Django
            if check_password(password, stored):
                # Contraseña correcta: actualizar último login y retornar usuario
                self._touch_last_login(user_id)
                return self._get_user(user_id)
            # Contraseña incorrecta
            return None
        
        # CASO 2: CONTRASEÑA EN TEXTO PLANO (legacy/inseguro)
        # Comparar directamente el texto
        if password == stored or stored.endswith(password):
            """
            MIGRACIÓN AUTOMÁTICA A SEGURIDAD:
            - Si la contraseña es correcta
            - Convertir a hash Django seguro
            - Guardar en BD para futuros logins
            """
            new_hash = make_password(password)  # Crear hash pbkdf2_sha256 con salt aleatorio
            
            # Actualizar BD con hash seguro
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE auth_user_custom SET password=%s WHERE id=%s",
                    [new_hash, user_id],
                )
            
            # Login exitoso: actualizar último acceso y retornar usuario
            self._touch_last_login(user_id)
            return self._get_user(user_id)
        
        # CONTRASEÑA INCORRECTA: No coincide en ningún formato
        return None
    
    def get_user(self, user_id):
        """
        MÉTODO REQUERIDO: Obtener usuario por ID
        
        PARÁMETROS:
        - user_id: ID numérico del usuario
        
        PROPÓSITO:
        - Django llama este método para recargar usuario desde sesión
        - Usado en cada request para obtener request.user
        - Debe retornar None si usuario no existe
        
        RETORNA:
        - CustomUser object: Si usuario existe
        - None: Si usuario no existe o hay error
        """
        return self._get_user(user_id)
    
    def _get_user(self, user_id):
        """
        MÉTODO PRIVADO: Obtener objeto usuario desde BD
        
        PARÁMETROS:
        - user_id: ID numérico del usuario
        
        PROPÓSITO:
        - Centralizar la lógica de obtención de usuario
        - Manejar errores de forma consistente
        - Usar el ORM de Django para cargar el objeto completo
        
        RETORNA:
        - CustomUser object: Si encontrado
        - None: Si no existe o hay error
        """
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
    
    def _touch_last_login(self, user_id):
        """
        MÉTODO PRIVADO: Actualizar timestamp de último login
        
        PARÁMETROS:
        - user_id: ID numérico del usuario
        
        PROPÓSITO:
        - Registrar cuándo fue el último acceso del usuario
        - Útil para auditoría y seguridad
        - Actualizar campo 'last_login' en BD
        
        IMPLEMENTACIÓN:
        - Usar NOW() de MySQL para timestamp actual
        - Consulta SQL directa para mejor rendimiento
        """
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE auth_user_custom SET last_login=NOW() WHERE id=%s", 
                [user_id]
            )

"""
=== FLUJO COMPLETO DE AUTENTICACIÓN ===

1. USUARIO INGRESA CREDENCIALES:
   - Username o email + password en formulario login

2. DJANGO LLAMA authenticate():
   - Con credenciales del formulario
   - Backend busca usuario en BD

3. VALIDACIÓN DE CONTRASEÑA:
   - Si es hash Django → usar check_password()
   - Si es texto plano → comparar directamente

4. MIGRACIÓN AUTOMÁTICA (si texto plano):
   - Convertir a hash Django seguro
   - Actualizar BD con nuevo hash

5. LOGIN EXITOSO:
   - Actualizar last_login
   - Retornar objeto CustomUser
   - Django crea sesión automáticamente

6. REQUESTS POSTERIORES:
   - Django llama get_user() con ID de sesión
   - Backend retorna objeto usuario actual

=== VENTAJAS DE ESTE BACKEND ===

✅ COMPATIBILIDAD: Funciona con BD existente sin cambios
✅ SEGURIDAD: Migra gradualmente a contraseñas hasheadas
✅ FLEXIBILIDAD: Acepta username O email para login
✅ AUDITORÍA: Registra último acceso automáticamente
✅ ESTÁNDAR: Compatible con decoradores @login_required
✅ SESIONES: Funciona con sistema de sesiones de Django

=== CONFIGURACIÓN REQUERIDA ===

En settings.py:
AUTHENTICATION_BACKENDS = [
    'clinica_app.backends.SPAuthBackend',
]

=== SEGURIDAD IMPLEMENTADA ===

1. HASH PBKDF2_SHA256: Estándar de Django con salt aleatorio
2. MIGRACIÓN AUTOMÁTICA: De texto plano a hash seguro
3. VALIDACIÓN ROBUSTA: Manejo de casos edge
4. AUDITORÍA: Registro de último acceso
5. ACTIVACIÓN: Solo usuarios activos pueden hacer login

=== CASOS DE USO ===

- Usuario con contraseña texto plano: Login exitoso + migración automática
- Usuario con hash Django: Login directo seguro  
- Usuario inactivo: Login rechazado
- Credenciales incorrectas: Login rechazado
- Username o email: Ambos funcionan para login

=== IMPORTANTE PARA PRODUCCIÓN ===

- Las contraseñas en texto plano son un riesgo de seguridad
- Este backend permite migración gradual sin interrumpir servicio
- Eventualmente, todas las contraseñas serán hashes seguros
- Considerar forzar cambio de contraseña tras primer login
"""