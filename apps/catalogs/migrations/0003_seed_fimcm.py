"""
Añade la FIMCM al catálogo de facultades.

Faltaba en la lista provisional de 0002 y figura en la oferta de grado oficial
(https://www.espol.edu.ec/es/admision/oferta-academica). Va en una migración y
no solo como alta desde el admin para que toda base nueva nazca con ella: el
sembrado de datos de ESPOL le asigna estudiantes.

Idempotente por el mismo motivo que 0002.
"""

from django.db import migrations

FIMCM = ("FIMCM", "Facultad de Ingeniería Marítima y Ciencias del Mar", 80)


def seed(apps, schema_editor):
    Faculty = apps.get_model("catalogs", "Faculty")
    code, name, order = FIMCM
    Faculty.objects.get_or_create(
        code=code,
        defaults={"name": name, "display_order": order, "is_active": True},
    )


def unseed(apps, schema_editor):
    Faculty = apps.get_model("catalogs", "Faculty")
    Faculty.objects.filter(code=FIMCM[0]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalogs", "0002_seed_catalogs"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
