"""
Errores de dominio.

Cada uno lleva un ``code`` estable para poder mapearlo a un status HTTP y a un
mensaje de UI sin depender del texto, que cambia. Los servicios levantan estas
excepciones; nunca devuelven None o False para señalar una regla violada.
"""


class DomainError(Exception):
    """Raíz de todos los errores de negocio."""

    code = "domain_error"
    default_message = "No se pudo completar la operación."
    #: Status HTTP sugerido cuando esto cruce la frontera de la API (Etapa 4).
    http_status = 400

    def __init__(self, message=None, *, code=None, field=None):
        self.message = message or self.default_message
        self.code = code or self.code
        #: Campo del formulario al que atribuir el error, cuando aplica.
        self.field = field
        super().__init__(self.message)

    def __str__(self):
        return self.message


class DomainValidationError(DomainError):
    """
    Los datos no pasan la validación de los modelos.

    Envuelve el ``ValidationError`` de Django para que **todos** los servicios
    fallen con la misma familia de excepciones. Sin esto, la misma regla produce
    un tipo distinto según la atrape ``full_clean()`` o la base de datos, y cada
    llamador tendría que capturar dos jerarquías sin saber cuál toca.

    ``errors`` conserva el detalle por campo (``{'email': ['...']}``) para poder
    devolverlo tal cual en la respuesta de la API.
    """

    code = "validation_error"
    default_message = "Los datos enviados no son válidos."
    http_status = 400

    def __init__(self, errors=None, message=None, code=None):
        self.errors = errors or {}
        super().__init__(message, code=code)


class BusinessRuleViolation(DomainError):
    """
    Una regla de negocio (RN-1..RN-7) impide la operación.

    Ejemplo: postular a un club donde ya se tiene una solicitud pendiente.
    """

    code = "business_rule_violation"
    default_message = "La operación viola una regla de negocio."
    http_status = 409


class StateTransitionError(DomainError):
    """
    La transición de estado solicitada no existe en la máquina de estados (§5).

    Ejemplo: aprobar una solicitud que ya fue rechazada.
    """

    code = "invalid_state_transition"
    default_message = "La transición de estado solicitada no es válida."
    http_status = 409


class ConfigurationError(DomainError):
    """
    Falta una precondición de configuración del sistema, no un dato del usuario.

    Ejemplo: aprobar una solicitud sin ningún PaoPeriod activo. Es un error del
    administrador, no de quien opera, y por eso no se reporta como error de
    validación de un campo.
    """

    code = "configuration_error"
    default_message = "El sistema no está configurado para completar esta operación."
    http_status = 503


class PermissionDeniedError(DomainError):
    """
    El actor no tiene el permiso de club requerido (§8).

    Se distingue de la autenticación: aquí el usuario es conocido, pero su rol en
    ese club no habilita la acción.
    """

    code = "permission_denied"
    default_message = "No tienes permiso para realizar esta acción."
    http_status = 403
