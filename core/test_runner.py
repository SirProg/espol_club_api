"""Runner de tests con los ajustes que solo tienen sentido al probar."""

from django.conf import settings
from django.test.runner import DiscoverRunner


class EspolclubTestRunner(DiscoverRunner):
    """
    Sustituye el hasher de contraseñas por uno rápido.

    PBKDF2 tarda ~900 ms por hash **a propósito**: esa lentitud es lo que
    protege las contraseñas reales. Pero la suite crea decenas de cuentas y ese
    coste dominaba el tiempo total (~160 s de 121 s medidos iban ahí), sin
    aportar nada: ninguna prueba verifica la fortaleza del hash.

    Se aplica desde el runner y no desde un módulo de settings aparte para que
    no dependa de que alguien recuerde pasar ``--settings``.
    """

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.PASSWORD_HASHERS = [
            "django.contrib.auth.hashers.MD5PasswordHasher",
        ]
