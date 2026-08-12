"""
Siembra los catálogos cerrados de MASTER §7.3.

Idempotente: usa get_or_create, así que volver a aplicarla no duplica filas ni
pisa las ediciones hechas desde el admin.

La lista de facultades es provisional (PPD-01): no se ha especificado la lista
oficial completa de ESPOL. Ampliarla es un alta desde el admin, no una
migración — por eso el catálogo es una tabla y no un enum de código.
"""

from django.db import migrations

FACULTIES = [
    ("FIEC", "Facultad de Ingeniería en Electricidad y Computación", 10),
    ("FCNM", "Facultad de Ciencias Naturales y Matemáticas", 20),
    ("FIMCP", "Facultad de Ingeniería en Mecánica y Ciencias de la Producción", 30),
    ("FICT", "Facultad de Ingeniería en Ciencias de la Tierra", 40),
    ("FCSH", "Facultad de Ciencias Sociales y Humanísticas", 50),
    ("FCV", "Facultad de Ciencias de la Vida", 60),
    ("FADCOM", "Facultad de Arte, Diseño y Comunicación Audiovisual", 70),
]

INTEREST_AREAS = [
    ("Tecnología", 10),
    ("Ciencia", 20),
    ("Cultura", 30),
    ("Deporte", 40),
    ("Emprendimiento", 50),
    ("Social", 60),
    ("Arte", 70),
    ("Académico", 80),
]


def seed(apps, schema_editor):
    Faculty = apps.get_model("catalogs", "Faculty")
    InterestArea = apps.get_model("catalogs", "InterestArea")

    for code, name, order in FACULTIES:
        Faculty.objects.get_or_create(
            code=code,
            defaults={"name": name, "display_order": order, "is_active": True},
        )

    for name, order in INTEREST_AREAS:
        InterestArea.objects.get_or_create(
            name=name,
            defaults={"display_order": order, "is_active": True},
        )


def unseed(apps, schema_editor):
    """
    Revierte solo las entradas sembradas por esta migración.

    No hace un delete masivo: para cuando esto se revierta pueden existir
    catálogos añadidos por GBP desde el admin, y borrarlos sería pérdida de
    datos que la migración no introdujo.
    """
    Faculty = apps.get_model("catalogs", "Faculty")
    InterestArea = apps.get_model("catalogs", "InterestArea")

    Faculty.objects.filter(code__in=[code for code, _, _ in FACULTIES]).delete()
    InterestArea.objects.filter(name__in=[name for name, _ in INTEREST_AREAS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalogs", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
