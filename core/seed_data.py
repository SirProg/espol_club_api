"""
Datos semilla de MASTER §17 — declaración pura.

Separados del comando para que el conjunto de datos sea legible de un vistazo y
comparable contra el documento maestro sin leer código de orquestación.

La coherencia entre estos datos es deliberada: cada uno existe para poder probar
una regla concreta (MASTER §17.12).
"""

import datetime

# §17.5 — Períodos académicos.
PAO_PERIODS = [
    {
        "pao_period": "2025-II",
        "start_date": datetime.date(2025, 10, 13),
        "end_date": datetime.date(2026, 2, 27),
        "activate": False,
    },
    {
        "pao_period": "2026-I",
        "start_date": datetime.date(2026, 5, 1),
        "end_date": datetime.date(2026, 9, 15),
        "activate": True,
    },
]

# §17.1 — Perfiles. Las contraseñas son las del prototipo de la Fase 1 y solo
# tienen sentido en desarrollo.
STUDENTS = [
    {
        "enrollment": "202311346",
        "first_name": "Kevin",
        "last_name": "Maldonado",
        "email": "kmaldon@espol.edu.ec",
        "password": "estudiante123",
        "birth_date": datetime.date(2005, 5, 14),
        "faculty": "FIEC",
        "career": "Computación",
        "semester": 6,
        "description": "Enfocado en data science y software libre.",
        "skills": ["Python", "React", "SQL"],
        "social_media": [{"network": "GitHub", "link": "https://github.com/kmaldon"}],
        "note": "No es miembro de KOKOA. Su solicitud fue rechazada (Etapa 6).",
    },
    {
        "enrollment": "202055789",
        "first_name": "María",
        "last_name": "Cevallos",
        "email": "mcevallos@espol.edu.ec",
        "password": "miembro123",
        "birth_date": datetime.date(2004, 3, 22),
        "faculty": "FIEC",
        "career": "Telemática",
        "semester": 7,
        "note": "Miembro activa de KOKOA y con membresía congelada de 2025-II.",
    },
    {
        "enrollment": "201899001",
        "first_name": "Diego",
        "last_name": "Ponce",
        "email": "dponce@espol.edu.ec",
        "password": "lider123",
        "birth_date": datetime.date(2002, 11, 8),
        "faculty": "FIEC",
        "career": "Computación",
        "semester": 9,
        "note": "Presidente/a de KOKOA.",
    },
    {
        "enrollment": "GBP-001",
        "first_name": "Ana",
        "last_name": "Rivas",
        "email": "arivas@espol.edu.ec",
        "password": "gbp123",
        "is_gbp_admin": True,
        "note": "Administradora GBP. Sin facultad, carrera ni semestre.",
    },
    {
        "enrollment": "202144556",
        "first_name": "Lucía",
        "last_name": "Torres",
        "email": "ltorres@espol.edu.ec",
        "password": "estudiante123",
        "birth_date": datetime.date(2006, 7, 2),
        "faculty": "FCNM",
        "career": "Matemática",
        "semester": 4,
        "note": "Autora de la solicitud pendiente (Etapa 6).",
    },
    {
        "enrollment": "201977882",
        "first_name": "Andrés",
        "last_name": "Vera",
        "email": "avera@espol.edu.ec",
        "password": "miembro123",
        "birth_date": datetime.date(2003, 1, 30),
        "faculty": "FIEC",
        "career": "Computación",
        "semester": 8,
        "note": "Rol personalizado. Escanea asistencias como Staff (Etapa 7).",
    },
]

SEEDED_ENROLLMENTS = [entry["enrollment"] for entry in STUDENTS]

# Matrícula comprometida como líder de Mecatrónica que **no tiene cuenta**.
# Es el dato que hace verificable RF-12 y la decisión D-01.
PENDING_LEADER_ENROLLMENT = "202099777"

# §17.2 — Clubes.
CLUBS = [
    {
        "name": "Club de Software Libre KOKOA",
        "acronym": "KOKOA",
        "description": (
            "Comunidad dedicada a la difusión del software libre, la "
            "colaboración en proyectos de código abierto y la formación "
            "técnica de la comunidad politécnica."
        ),
        "location": "FIEC 11D",
        "faculty": "FIEC",
        "interest_areas": ["Tecnología", "Académico"],
        "leader_enrollment": "201899001",
        "expected_status": "Active",
    },
    {
        "name": "Club de Mecatrónica",
        "acronym": "MECATRÓNICA",
        "description": (
            "Espacio de construcción de prototipos robóticos y sistemas "
            "automatizados para competencias nacionales."
        ),
        "location": "FIMCP 22A",
        "faculty": "FIMCP",
        "interest_areas": ["Tecnología", "Ciencia"],
        "leader_enrollment": PENDING_LEADER_ENROLLMENT,
        "expected_status": "Pending Leader",
    },
]

# §17.3 — Rol personalizado de KOKOA (los otros cuatro los crea el alta).
CUSTOM_ROLES = [
    {
        "club": "KOKOA",
        "role_name": "Encargado de Documentos",
        "is_leadership": False,
        "permissions": {"access_web_panel": True, "manage_documents": True},
    },
]

# §17.4 — Membresías del período vigente. La de Diego la crea el alta del club.
MEMBERSHIPS = [
    {"enrollment": "202055789", "club": "KOKOA", "role": "Miembro"},
    {"enrollment": "201977882", "club": "KOKOA", "role": "Encargado de Documentos"},
]

# §17.4 — Membresía histórica: María en 2025-II, que quedará congelada. Es lo
# que permite probar la renovación de nómina (RF-21) y RN-4.
HISTORICAL_MEMBERSHIPS = [
    {"enrollment": "202055789", "club": "KOKOA", "role": "Miembro", "pao": "2025-II"},
]

# Fecha con la que se congela la nómina histórica. Fija a propósito: si se usara
# la fecha real, el resultado del sembrado cambiaría según el día en que se
# ejecute, y el conjunto dejaría de ser reproducible.
FREEZE_REFERENCE_DATE = datetime.date(2026, 2, 28)

# §17.2 — Documentos de KOKOA. Cubren los dos lados de RF-16.
CLUB_DOCUMENTS = [
    {
        "club": "KOKOA",
        "title": "Estatutos del Club",
        "filename": "kokoa_estatutos.pdf",
        "is_public": False,
    },
    {
        "club": "KOKOA",
        "title": "Brochure 2026",
        "filename": "kokoa_brochure_2026.pdf",
        "is_public": True,
    },
]

# §17.12 — Qué permite probar cada dato. Se imprime al terminar para que quede
# claro por qué el conjunto es el que es.
COVERAGE = [
    ("Club MECATRÓNICA sin líder", "RF-12, D-01, club en solo lectura"),
    ("Membresía congelada de María (2025-II)", "RN-4, renovación de nómina (RF-21)"),
    ("Diego como Presidente/a de KOKOA", "RN-1, exclusividad de liderazgo"),
    ("Kevin sin membresías", "RN-2, reaplicación inmediata (Etapa 6)"),
    ("Rol personalizado de Andrés", "RF-07, permisos granulares"),
    ("Documentos 'Estatutos' y 'Brochure'", "RF-16, visibilidad diferenciada"),
    ("Dos PAOs, uno cerrado", "RF-45, histórico por período (RF-49)"),
    ("Ana Rivas como GBP", "RF-54, GBP no edita el interior de los clubes"),
]
