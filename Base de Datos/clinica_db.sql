-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 26-09-2025 a las 09:01:59
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `clinica_db`
--

DELIMITER $$
--
-- Procedimientos
--
CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_actualizar_estado_cita` (IN `p_cita_id` INT, IN `p_nuevo_estado` VARCHAR(20))   BEGIN
    UPDATE citas 
    SET estado = p_nuevo_estado,
        updated_at = NOW()
    WHERE id = p_cita_id;
    
    SELECT 'Estado actualizado exitosamente' AS mensaje;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_agendar_cita` (IN `p_paciente_id` INT, IN `p_medico_id` INT, IN `p_fecha` DATE, IN `p_hora` TIME, IN `p_duracion` INT, IN `p_motivo` TEXT)   BEGIN
    DECLARE v_existe INT;
    
    -- Verificar disponibilidad
    SELECT COUNT(*) INTO v_existe
    FROM citas
    WHERE medico_id = p_medico_id
    AND fecha = p_fecha
    AND hora = p_hora
    AND estado IN ('PENDIENTE', 'CONFIRMADA');
    
    IF v_existe > 0 THEN
        SELECT 'Horario no disponible' AS mensaje, 0 AS id;
    ELSE
        INSERT INTO citas (
            paciente_id, medico_id, fecha, hora, duracion, motivo, estado
        ) VALUES (
            p_paciente_id, p_medico_id, p_fecha, p_hora, p_duracion, p_motivo, 'PENDIENTE'
        );
        
        SELECT 'Cita agendada exitosamente' AS mensaje, LAST_INSERT_ID() AS id;
    END IF;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_cancelar_cita` (IN `p_cita_id` INT)   BEGIN
    UPDATE citas 
    SET estado = 'CANCELADA', 
        updated_at = NOW() 
    WHERE id = p_cita_id;
    
    SELECT 'Cita cancelada exitosamente' AS mensaje;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_crear_medico` (IN `p_user_id` INT, IN `p_especialidad_id` INT, IN `p_numero_colegiado` VARCHAR(50), IN `p_horario_inicio` TIME, IN `p_horario_fin` TIME, IN `p_dias_laborales` VARCHAR(50))   BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'Error al crear médico' AS mensaje;
    END;
    
    START TRANSACTION;
    
    INSERT INTO medicos (
        user_id, especialidad_id, numero_colegiado,
        horario_inicio, horario_fin, dias_laborales
    ) VALUES (
        p_user_id, p_especialidad_id, p_numero_colegiado,
        p_horario_inicio, p_horario_fin, p_dias_laborales
    );
    
    SELECT 'Médico creado exitosamente' AS mensaje;
    
    COMMIT;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_crear_paciente` (IN `p_user_id` INT, IN `p_fecha_nacimiento` DATE, IN `p_tipo_sangre` VARCHAR(5), IN `p_alergias` TEXT, IN `p_observaciones` TEXT)   BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'Error al crear paciente' AS mensaje;
    END;
    
    START TRANSACTION;
    
    INSERT INTO pacientes (
        user_id, fecha_nacimiento, tipo_sangre, alergias, observaciones
    ) VALUES (
        p_user_id, p_fecha_nacimiento, p_tipo_sangre, p_alergias, p_observaciones
    );
    
    SELECT 'Paciente creado exitosamente' AS mensaje;
    
    COMMIT;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_crear_usuario` (IN `p_username` VARCHAR(150), IN `p_email` VARCHAR(254), IN `p_password` VARCHAR(128), IN `p_first_name` VARCHAR(150), IN `p_last_name` VARCHAR(150), IN `p_role` INT, IN `p_phone` VARCHAR(20), IN `p_address` TEXT)   BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'Error al crear usuario' AS mensaje, 0 AS id;
    END;
    
    START TRANSACTION;
    
    INSERT INTO auth_user_custom (
        username, email, password, first_name, last_name, 
        role, phone, address, is_staff, is_superuser
    ) VALUES (
        p_username, p_email, p_password, p_first_name, p_last_name,
        p_role, p_phone, p_address,
        IF(p_role = 1, TRUE, FALSE),
        IF(p_role = 1, TRUE, FALSE)
    );
    
    SELECT 'Usuario creado exitosamente' AS mensaje, LAST_INSERT_ID() AS id;
    
    COMMIT;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_eliminar_usuario` (IN `p_user_id` INT)   BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'Error al eliminar usuario' AS mensaje, 0 AS success;
    END;
    
    START TRANSACTION;
    
    -- Las citas y registros de médico/paciente se eliminan por CASCADE
    DELETE FROM auth_user_custom WHERE id = p_user_id;
    
    SELECT 'Usuario eliminado exitosamente' AS mensaje, 1 AS success;
    
    COMMIT;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_historial_citas_medico` (IN `p_medico_id` INT)   BEGIN
    SELECT 
        c.id,
        c.fecha,
        c.hora,
        c.duracion,
        c.estado,
        c.motivo,
        c.observaciones,
        CONCAT(up.first_name, ' ', up.last_name) AS paciente_nombre,
        up.phone AS paciente_telefono
    FROM citas c
    INNER JOIN auth_user_custom up ON c.paciente_id = up.id
    WHERE c.medico_id = p_medico_id
    ORDER BY c.fecha DESC, c.hora DESC;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_historial_citas_paciente` (IN `p_paciente_id` INT)   BEGIN
    SELECT 
        c.id,
        c.fecha,
        c.hora,
        c.duracion,
        c.estado,
        c.motivo,
        c.observaciones,
        CONCAT(um.first_name, ' ', um.last_name) AS medico_nombre,
        e.nombre AS especialidad
    FROM citas c
    INNER JOIN auth_user_custom um ON c.medico_id = um.id
    LEFT JOIN medicos m ON um.id = m.user_id
    LEFT JOIN especialidades e ON m.especialidad_id = e.id
    WHERE c.paciente_id = p_paciente_id
    ORDER BY c.fecha DESC, c.hora DESC;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_login_usuario` (IN `p_username` VARCHAR(150), IN `p_password` VARCHAR(128))   BEGIN
    DECLARE v_user_id INT;
    
    SELECT id INTO v_user_id
    FROM auth_user_custom
    WHERE (username = p_username OR email = p_username)
    AND password = p_password
    AND is_active = TRUE;
    
    IF v_user_id IS NOT NULL THEN
        UPDATE auth_user_custom 
        SET last_login = NOW() 
        WHERE id = v_user_id;
        
        SELECT id, username, email, first_name, last_name, role, phone
        FROM auth_user_custom
        WHERE id = v_user_id;
    ELSE
        SELECT NULL AS id, 'Credenciales inválidas' AS mensaje;
    END IF;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_obtener_citas_fecha` (IN `p_fecha_inicio` DATE, IN `p_fecha_fin` DATE)   BEGIN
    SELECT 
        c.id,
        c.fecha,
        c.hora,
        c.duracion,
        c.estado,
        c.motivo,
        CONCAT(up.first_name, ' ', up.last_name) AS paciente_nombre,
        CONCAT(um.first_name, ' ', um.last_name) AS medico_nombre,
        e.nombre AS especialidad
    FROM citas c
    INNER JOIN auth_user_custom up ON c.paciente_id = up.id
    INNER JOIN auth_user_custom um ON c.medico_id = um.id
    LEFT JOIN medicos m ON um.id = m.user_id
    LEFT JOIN especialidades e ON m.especialidad_id = e.id
    WHERE c.fecha BETWEEN p_fecha_inicio AND p_fecha_fin
    AND c.estado IN ('PENDIENTE', 'CONFIRMADA')
    ORDER BY c.fecha, c.hora;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_obtener_medicos` ()   BEGIN
    SELECT 
        u.id,
        CONCAT(u.first_name, ' ', u.last_name) AS nombre_completo,
        e.nombre AS especialidad,
        m.horario_inicio,
        m.horario_fin,
        m.dias_laborales
    FROM auth_user_custom u
    INNER JOIN medicos m ON u.id = m.user_id
    LEFT JOIN especialidades e ON m.especialidad_id = e.id
    WHERE u.role = 2 AND u.is_active = TRUE
    ORDER BY u.last_name, u.first_name;
END$$

DELIMITER ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_group`
--

CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL,
  `name` varchar(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_group_permissions`
--

CREATE TABLE `auth_group_permissions` (
  `id` bigint(20) NOT NULL,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_permission`
--

CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `auth_permission`
--

INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
(1, 'Can add permission', 1, 'add_permission'),
(2, 'Can change permission', 1, 'change_permission'),
(3, 'Can delete permission', 1, 'delete_permission'),
(4, 'Can view permission', 1, 'view_permission'),
(5, 'Can add group', 2, 'add_group'),
(6, 'Can change group', 2, 'change_group'),
(7, 'Can delete group', 2, 'delete_group'),
(8, 'Can view group', 2, 'view_group'),
(9, 'Can add content type', 3, 'add_contenttype'),
(10, 'Can change content type', 3, 'change_contenttype'),
(11, 'Can delete content type', 3, 'delete_contenttype'),
(12, 'Can view content type', 3, 'view_contenttype'),
(13, 'Can add custom user', 4, 'add_customuser'),
(14, 'Can change custom user', 4, 'change_customuser'),
(15, 'Can delete custom user', 4, 'delete_customuser'),
(16, 'Can view custom user', 4, 'view_customuser'),
(17, 'Can add cita', 5, 'add_cita'),
(18, 'Can change cita', 5, 'change_cita'),
(19, 'Can delete cita', 5, 'delete_cita'),
(20, 'Can view cita', 5, 'view_cita'),
(21, 'Can add Especialidad', 6, 'add_especialidad'),
(22, 'Can change Especialidad', 6, 'change_especialidad'),
(23, 'Can delete Especialidad', 6, 'delete_especialidad'),
(24, 'Can view Especialidad', 6, 'view_especialidad'),
(25, 'Can add medico', 7, 'add_medico'),
(26, 'Can change medico', 7, 'change_medico'),
(27, 'Can delete medico', 7, 'delete_medico'),
(28, 'Can view medico', 7, 'view_medico'),
(29, 'Can add paciente', 8, 'add_paciente'),
(30, 'Can change paciente', 8, 'change_paciente'),
(31, 'Can delete paciente', 8, 'delete_paciente'),
(32, 'Can view paciente', 8, 'view_paciente'),
(33, 'Can add session', 9, 'add_session'),
(34, 'Can change session', 9, 'change_session'),
(35, 'Can delete session', 9, 'delete_session'),
(36, 'Can view session', 9, 'view_session');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_user_custom`
--

CREATE TABLE `auth_user_custom` (
  `id` int(11) NOT NULL,
  `username` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `password` varchar(128) NOT NULL,
  `first_name` varchar(150) DEFAULT NULL,
  `last_name` varchar(150) DEFAULT NULL,
  `role` int(11) NOT NULL DEFAULT 3,
  `is_active` tinyint(1) DEFAULT 1,
  `is_staff` tinyint(1) DEFAULT 0,
  `is_superuser` tinyint(1) DEFAULT 0,
  `date_joined` datetime DEFAULT current_timestamp(),
  `last_login` datetime DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `auth_user_custom`
--

INSERT INTO `auth_user_custom` (`id`, `username`, `email`, `password`, `first_name`, `last_name`, `role`, `is_active`, `is_staff`, `is_superuser`, `date_joined`, `last_login`, `phone`, `address`, `created_at`, `updated_at`) VALUES
(6, 'Brayan', 'juegoopes@gmail.com', 'pbkdf2_sha256$600000$7TfF6eA7DtG7K9HXWjX0Ha$+q5zKQnw8CEMY7VvcAAY9dkmqqK5gN6kY+U9p8O5H1g=', 'Brayan David', 'Camacho', 2, 1, 0, 0, '2025-08-08 22:26:49', '2025-09-26 03:28:05', '38184787', 'zona19', '2025-08-09 04:26:49', '2025-09-26 04:23:28'),
(11, 'Administrador', 'brayanzdd7@gmail.com', 'pbkdf2_sha256$600000$g5sb4SCb48gjbModnZTJ4T$xicEYuI5/OL82Ul+6ivkd1AzVmBil5oOlc3y52QPKn0=', 'Brayan', 'zdd', 1, 1, 1, 1, '2025-09-24 19:02:36', '2025-09-26 06:40:41', '38184787', 'Casa', '2025-09-25 01:02:36', '2025-09-26 06:40:41'),
(13, 'Messi', 'estanlyfabian@gmail.com', 'pbkdf2_sha256$600000$FnP00pAPmsI3eNAPYm5yT8$yLSMCeSO+vcROkUQbCy63VCha5XQjPzDPNeea5fzvEA=', 'Lionel Andrés', 'Messi Cuccitini', 3, 1, 0, 0, '2025-09-25 03:16:29', '2025-09-26 05:03:36', '38184787', 'Buenos Aires Argentina', '2025-09-25 09:16:29', '2025-09-26 05:03:36');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `citas`
--

CREATE TABLE `citas` (
  `id` int(11) NOT NULL,
  `paciente_id` int(11) NOT NULL,
  `medico_id` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `hora` time NOT NULL,
  `duracion` int(11) DEFAULT 30,
  `motivo` text DEFAULT NULL,
  `estado` enum('PENDIENTE','CONFIRMADA','CANCELADA','COMPLETADA') DEFAULT 'PENDIENTE',
  `observaciones` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `citas`
--

INSERT INTO `citas` (`id`, `paciente_id`, `medico_id`, `fecha`, `hora`, `duracion`, `motivo`, `estado`, `observaciones`, `created_at`, `updated_at`) VALUES
(4, 13, 6, '2025-09-26', '13:00:00', 45, 'Ver la patita', 'COMPLETADA', NULL, '2025-09-25 09:18:37', '2025-09-26 04:58:05');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_admin_log`
--

CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) UNSIGNED NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_content_type`
--

CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `django_content_type`
--

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(2, 'auth', 'group'),
(1, 'auth', 'permission'),
(5, 'clinica_app', 'cita'),
(4, 'clinica_app', 'customuser'),
(6, 'clinica_app', 'especialidad'),
(7, 'clinica_app', 'medico'),
(8, 'clinica_app', 'paciente'),
(3, 'contenttypes', 'contenttype'),
(9, 'sessions', 'session');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_migrations`
--

CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `django_migrations`
--

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2025-08-08 22:25:03.365463'),
(2, 'contenttypes', '0002_remove_content_type_name', '2025-08-08 22:25:03.455437'),
(3, 'auth', '0001_initial', '2025-08-08 22:25:03.823841'),
(4, 'auth', '0002_alter_permission_name_max_length', '2025-08-08 22:25:03.910071'),
(5, 'auth', '0003_alter_user_email_max_length', '2025-08-08 22:25:03.918587'),
(6, 'auth', '0004_alter_user_username_opts', '2025-08-08 22:25:03.926110'),
(7, 'auth', '0005_alter_user_last_login_null', '2025-08-08 22:25:03.933619'),
(8, 'auth', '0006_require_contenttypes_0002', '2025-08-08 22:25:03.938625'),
(9, 'auth', '0007_alter_validators_add_error_messages', '2025-08-08 22:25:03.943879'),
(10, 'auth', '0008_alter_user_username_max_length', '2025-08-08 22:25:03.949787'),
(11, 'auth', '0009_alter_user_last_name_max_length', '2025-08-08 22:25:03.957311'),
(12, 'auth', '0010_alter_group_name_max_length', '2025-08-08 22:25:03.972342'),
(13, 'auth', '0011_update_proxy_permissions', '2025-08-08 22:25:03.978985'),
(14, 'auth', '0012_alter_user_first_name_max_length', '2025-08-08 22:25:03.987506'),
(15, 'clinica_app', '0001_initial', '2025-08-09 00:07:28.313369'),
(16, 'sessions', '0001_initial', '2025-08-09 00:19:13.323775');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_session`
--

CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `django_session`
--

INSERT INTO `django_session` (`session_key`, `session_data`, `expire_date`) VALUES
('6yo6cu5dpydiztt9y6jpasvadyr1j9kf', '.eJyrVopPLC3JiC8tTi2Kz0xRslIyNFTSQRZMSkzOTs0DySTnZOZlJifGJxYU6EFFi_WCAxyBSp2gilB0ZiQWZwC1KdUCACHNI8M:1v228H:J6AgsJ9spt5hiTGAGODcXu3IfUzsQjHTNZTcisHCrU4', '2025-10-10 06:40:41.106908'),
('8gs41074lsk1qsjz8ueiqi5fhd7rxtwm', '.eJyrVopPLC3JiC8tTi2Kz0xRslIyVNJBFktKTM5OzQNJJOdk5mUmJ8YnFhToQUWL9YIDHIFKnaCKUHRmJBZnALUp1QIAC3Mjkg:1ukqh5:zhI-XaVbUgvRDTd6Cq6Jaj4BAwyMUZpM-TQwjnDjsyQ', '2025-08-23 21:01:35.688303');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `especialidades`
--

CREATE TABLE `especialidades` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `especialidades`
--

INSERT INTO `especialidades` (`id`, `nombre`, `descripcion`, `created_at`) VALUES
(1, 'Dermatología General', 'Diagnóstico y tratamiento de enfermedades de la piel', '2025-08-08 22:01:15'),
(2, 'Dermatología Cosmética', 'Procedimientos estéticos y cuidado de la piel', '2025-08-08 22:01:15'),
(3, 'Dermatología Pediátrica', 'Tratamiento de condiciones de piel en niños', '2025-08-08 22:01:15'),
(4, 'Cirugía Dermatológica', 'Procedimientos quirúrgicos menores de piel', '2025-08-08 22:01:15');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `medicos`
--

CREATE TABLE `medicos` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `especialidad_id` int(11) DEFAULT NULL,
  `numero_colegiado` varchar(50) DEFAULT NULL,
  `horario_inicio` time DEFAULT NULL,
  `horario_fin` time DEFAULT NULL,
  `dias_laborales` varchar(50) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `medicos`
--

INSERT INTO `medicos` (`id`, `user_id`, `especialidad_id`, `numero_colegiado`, `horario_inicio`, `horario_fin`, `dias_laborales`, `created_at`) VALUES
(2, 6, 2, NULL, '08:00:00', '17:00:00', 'LUN,MAR,MIE,JUE,VIE', '2025-08-09 04:26:49');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `pacientes`
--

CREATE TABLE `pacientes` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `fecha_nacimiento` date DEFAULT NULL,
  `tipo_sangre` varchar(5) DEFAULT NULL,
  `alergias` text DEFAULT NULL,
  `observaciones` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_spanish_ci;

--
-- Volcado de datos para la tabla `pacientes`
--

INSERT INTO `pacientes` (`id`, `user_id`, `fecha_nacimiento`, `tipo_sangre`, `alergias`, `observaciones`, `created_at`) VALUES
(4, 13, '2025-09-25', 'A-', 'Al fracaso', 'Campeon del Mundo', '2025-09-25 09:16:29');

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vista_calendario`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `vista_calendario` (
`fecha` date
,`hora` time
,`hora_formato` varchar(10)
,`hora_fin` time
,`estado` enum('PENDIENTE','CONFIRMADA','CANCELADA','COMPLETADA')
,`medico` varchar(301)
,`medico_id` int(11)
);

-- --------------------------------------------------------

--
-- Estructura para la vista `vista_calendario`
--
DROP TABLE IF EXISTS `vista_calendario`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vista_calendario`  AS SELECT `c`.`fecha` AS `fecha`, `c`.`hora` AS `hora`, time_format(`c`.`hora`,'%H:%i') AS `hora_formato`, addtime(`c`.`hora`,sec_to_time(`c`.`duracion` * 60)) AS `hora_fin`, `c`.`estado` AS `estado`, concat(`um`.`first_name`,' ',`um`.`last_name`) AS `medico`, `um`.`id` AS `medico_id` FROM (`citas` `c` join `auth_user_custom` `um` on(`c`.`medico_id` = `um`.`id`)) WHERE `c`.`estado` in ('PENDIENTE','CONFIRMADA') ORDER BY `c`.`fecha` ASC, `c`.`hora` ASC ;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `auth_group`
--
ALTER TABLE `auth_group`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indices de la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  ADD KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`);

--
-- Indices de la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`);

--
-- Indices de la tabla `auth_user_custom`
--
ALTER TABLE `auth_user_custom`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indices de la tabla `citas`
--
ALTER TABLE `citas`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_cita` (`medico_id`,`fecha`,`hora`),
  ADD KEY `idx_fecha_hora` (`fecha`,`hora`),
  ADD KEY `fk_citas_paciente` (`paciente_id`);

--
-- Indices de la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD PRIMARY KEY (`id`),
  ADD KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`);

--
-- Indices de la tabla `django_content_type`
--
ALTER TABLE `django_content_type`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`);

--
-- Indices de la tabla `django_migrations`
--
ALTER TABLE `django_migrations`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `django_session`
--
ALTER TABLE `django_session`
  ADD PRIMARY KEY (`session_key`),
  ADD KEY `django_session_expire_date_a5c62663` (`expire_date`);

--
-- Indices de la tabla `especialidades`
--
ALTER TABLE `especialidades`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `medicos`
--
ALTER TABLE `medicos`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `user_id` (`user_id`),
  ADD KEY `especialidad_id` (`especialidad_id`);

--
-- Indices de la tabla `pacientes`
--
ALTER TABLE `pacientes`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `user_id` (`user_id`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `auth_group`
--
ALTER TABLE `auth_group`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=37;

--
-- AUTO_INCREMENT de la tabla `auth_user_custom`
--
ALTER TABLE `auth_user_custom`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- AUTO_INCREMENT de la tabla `citas`
--
ALTER TABLE `citas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `django_content_type`
--
ALTER TABLE `django_content_type`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT de la tabla `django_migrations`
--
ALTER TABLE `django_migrations`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT de la tabla `especialidades`
--
ALTER TABLE `especialidades`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `medicos`
--
ALTER TABLE `medicos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `pacientes`
--
ALTER TABLE `pacientes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);

--
-- Filtros para la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);

--
-- Filtros para la tabla `citas`
--
ALTER TABLE `citas`
  ADD CONSTRAINT `fk_citas_medico` FOREIGN KEY (`medico_id`) REFERENCES `auth_user_custom` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_citas_paciente` FOREIGN KEY (`paciente_id`) REFERENCES `auth_user_custom` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);

--
-- Filtros para la tabla `medicos`
--
ALTER TABLE `medicos`
  ADD CONSTRAINT `medicos_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `auth_user_custom` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `medicos_ibfk_2` FOREIGN KEY (`especialidad_id`) REFERENCES `especialidades` (`id`);

--
-- Filtros para la tabla `pacientes`
--
ALTER TABLE `pacientes`
  ADD CONSTRAINT `pacientes_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `auth_user_custom` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
