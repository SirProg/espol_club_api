"""
Datos reales de ESPOL para poblar la API — declaración pura, sin lógica.

**Procedencia.** Todo lo que hay aquí se tomó del portal oficial de la Unidad de
Bienestar Politécnica (``oe.espol.edu.ec``) y de ``espol.edu.ec``, salvo las
personas, que son ficticias y van marcadas como tales.

Se separa del comando por el mismo motivo que ``seed_data.py``: para poder
contrastar el conjunto contra su fuente sin leer código de orquestación.

Dos cosas que la investigación confirmó y conviene no perder:

* La sigla **GBP** que usa MASTER.md es terminología real de ESPOL. El Programa
  de Apoyo dice literalmente *"el Vicerrectorado Académico y la GBP se unieron"*,
  aunque el portal se titule "Unidad de Bienestar Politécnico".
* **KOKOA existe**, y su descripción oficial coincide con el club que MASTER usa
  como ejemplo.
"""

import datetime

# ---------------------------------------------------------------------------
# Calendario académico
# ---------------------------------------------------------------------------
#
# Nomenclatura confirmada en el calendario oficial de grado: I PAO, II PAO y PAE
# (Período Académico Extraordinario). Se siembran tres para que el histórico por
# período (RF-49) y la renovación de nómina (RF-21) tengan contra qué operar.

PAO_PERIODS = [
    {
        "pao_period": "2025-I",
        "start_date": datetime.date(2025, 5, 5),
        "end_date": datetime.date(2025, 9, 19),
        "activate": False,
    },
    {
        "pao_period": "2025-II",
        "start_date": datetime.date(2025, 10, 13),
        "end_date": datetime.date(2026, 2, 27),
        "activate": False,
    },
    {
        "pao_period": "2026-I",
        "start_date": datetime.date(2026, 5, 4),
        "end_date": datetime.date(2026, 9, 18),
        "activate": True,
    },
]

#: El período del que se renueva la nómina hacia el vigente.
PREVIOUS_PAO = "2025-II"
CURRENT_PAO = "2026-I"

# ---------------------------------------------------------------------------
# Áreas de interés
# ---------------------------------------------------------------------------
#
# ESPOL clasifica sus clubes en: Profesionales, Culturales, Competencias
# transversales y Grupos deportivos (este último "por ahora no se incluye en el
# programa"). Esa taxonomía se mapea al catálogo de áreas que ya existe en la
# base, sin tocar el modelo.

CATEGORY_TO_AREAS = {
    "Profesionales": ["Académico", "Tecnología"],
    "Culturales": ["Cultura", "Arte"],
    "Competencias transversales": ["Social", "Académico"],
}

# ---------------------------------------------------------------------------
# Clubes
# ---------------------------------------------------------------------------
#
# Los 18 que el portal publica **con descripción oficial**. El texto de
# ``description`` es literal de la fuente.
#
# Quedan fuera siete que aparecen solo en un formulario de pedidos, sin
# descripción publicada (ASHRAE, Club de Emprendedores, Club Fotográfico, IAHR,
# Inecyc, Robota, Slow Food): inventarles texto sería mezclar datos verificados
# con ficción sin marcar la diferencia.
#
# ``faculty`` y ``location`` son atribuciones plausibles según el ámbito de cada
# club, no dato oficial: el portal no publica su sede.

CLUBS = [
    {
        "acronym": "KOKOA",
        "name": "Club de Software Libre KOKOA",
        "description": (
            "KOKOA es una comunidad código abierto, software y hardware libre "
            "que se preocupa por la distribución, desarrollo, implementación y "
            "aprendizaje de software, hardware y tecnologías libres."
        ),
        "category": "Profesionales",
        "faculty": "FIEC",
        "location": "FIEC, Edificio 11D",
        "areas": ["Tecnología", "Académico"],
        "size": "grande",
    },
    {
        "acronym": "TAWS",
        "name": "Tecnologías Web, Móviles y Data Science",
        "description": (
            "El Grupo de Investigación de Tecnologías Web, Móviles y Data "
            "Science (TAWS) busca contribuir de forma integral en la formación "
            "de estudiantes de ESPOL, fomentando la investigación aplicada, el "
            "aprendizaje de nuevas tecnologías y el desarrollo de proyectos "
            "multidisciplinarios. #BeTAWS"
        ),
        "category": "Profesionales",
        "faculty": "FIEC",
        "location": "FIEC, Laboratorio de Investigación",
        "areas": ["Tecnología", "Académico"],
        "size": "grande",
    },
    {
        "acronym": "MECATRÓNICA",
        "name": "Club de Mecatrónica",
        "description": (
            "El Club de Mecatrónica tiene por objeto impulsar el desarrollo de "
            "competencias en el ámbito tecnológico, particularmente en el "
            "desarrollo de sistemas mecatrónicos, IOT, manufactura aditiva, "
            "software y aplicaciones para el control y automatización de "
            "procesos."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Taller de Prototipado",
        "areas": ["Tecnología", "Ciencia"],
        "size": "mediano",
    },
    {
        "acronym": "NIOT",
        "name": "Networking e Internet de las Cosas",
        "description": (
            "Cooperamos con la sociedad del conocimiento en el desarrollo de "
            "aplicaciones web y móviles integrados con servicios telemáticos, "
            "internet de las Cosas, tecnologías de la Información y la "
            "Comunicación, para la formación académica de estudiantes e "
            "investigadores."
        ),
        "category": "Profesionales",
        "faculty": "FIEC",
        "location": "FIEC, Laboratorio de Telemática",
        "areas": ["Tecnología", "Académico"],
        "size": "mediano",
    },
    {
        "acronym": "MSP",
        "name": "Célula Estudiantil Microsoft ESPOL",
        "description": (
            "Lideramos, investigamos y emprendemos, compartiendo nuestros "
            "conocimientos. Aquí ¡Impulsamos tu Potencial!"
        ),
        "category": "Profesionales",
        "faculty": "FIEC",
        "location": "FIEC, Sala de Estudiantes",
        "areas": ["Tecnología", "Emprendimiento"],
        "size": "mediano",
    },
    {
        "acronym": "ASME",
        "name": "American Society of Mechanical Engineers — Capítulo ESPOL",
        "description": (
            "Es una sociedad sin fines de lucro que busca servir a los futuros "
            "ingenieros en su formación académica, mediante la organización de "
            "cursos, charlas, capacitaciones, y demás actividades que permitan "
            "obtener un crecimiento profesional."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Aula 22A",
        "areas": ["Académico", "Tecnología"],
        "size": "mediano",
    },
    {
        "acronym": "ASCE",
        "name": "American Society of Civil Engineers — Capítulo ESPOL",
        "description": (
            "La American Society of Civil Engineers en ESPOL fomenta la "
            "interacción entre el ámbito académico y profesional de la "
            "Ingeniería Civil a través de investigaciones, ponencias, "
            "capacitaciones, visitas técnicas y más, en todas las ramas de la "
            "carrera, formando líderes y proactivos miembros en el campo "
            "laboral."
        ),
        "category": "Profesionales",
        "faculty": "FICT",
        "location": "FICT, Edificio de Ingeniería Civil",
        "areas": ["Académico", "Ciencia"],
        "size": "mediano",
    },
    {
        "acronym": "IIE",
        "name": "Capítulo Estudiantil Institute of Industrial Engineers",
        "description": (
            "Capítulo Estudiantil del Institute of Industrial Engineers "
            "dedicado a la difusión de los conocimientos y aplicaciones de "
            "Ing. Industrial."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Aula 18B",
        "areas": ["Académico", "Emprendimiento"],
        "size": "pequeño",
    },
    {
        "acronym": "IFT",
        "name": "Institute of Food Technologists — Capítulo ESPOL",
        "description": (
            "Somos un capítulo estudiantil que representa a la institución "
            "internacional más importante de ingeniería en alimentos. Nuestro "
            "fin es contribuir con el perfil profesional desde los inicios, "
            "formando líderes y fomentando lazos internacionales."
        ),
        "category": "Profesionales",
        "faculty": "FCV",
        "location": "FCV, Laboratorio de Alimentos",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
    },
    {
        "acronym": "CLIP",
        "name": "Club Logístico Integral Politécnico",
        "description": (
            "Impulsa la carrera de Ingeniería en Logística y Transporte "
            "mediante la investigación y desarrollo de proyectos "
            "multidisciplinarios que beneficien a la sociedad y a la comunidad "
            "politécnica, contribuyendo a la formación académica y profesional "
            "de los estudiantes."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Aula 20C",
        "areas": ["Académico", "Emprendimiento"],
        "size": "mediano",
    },
    {
        "acronym": "AAPG",
        "name": "American Association of Petroleum Geologists — Capítulo ESPOL",
        "description": (
            "Proporcionar a los miembros habilidades que serán valiosas "
            "herramientas para su vida profesional, mediante conferencias, "
            "cursos y diferentes actividades con información actualizada acerca "
            "de la ciencia de la geología del petróleo."
        ),
        "category": "Profesionales",
        "faculty": "FICT",
        "location": "FICT, Laboratorio de Geología",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
    },
    {
        "acronym": "GISSC",
        "name": "Club Estudiantil de Sistemas de Información Geográfica",
        "description": (
            "El objetivo del Club Estudiantil GISSC es proporcionar nexos entre "
            "los miembros del Club e investigadores, para involucrarse en "
            "actividades multidisciplinares con el uso de los Sistemas de "
            "Información Geográfica (GIS) y teledetección a nivel regional."
        ),
        "category": "Profesionales",
        "faculty": "FICT",
        "location": "FICT, Laboratorio de Geomática",
        "areas": ["Tecnología", "Ciencia"],
        "size": "pequeño",
    },
    {
        "acronym": "ARGUMENTUM",
        "name": "Argumentum — Club de Debate y Oratoria",
        "description": (
            "Nuestro objetivo es crear líderes de opinión y pensamiento crítico "
            "que sean capaces de expandir la cultura del debate y la oratoria; "
            "mediante la creación de actividades formativas y evaluativas para "
            "sus miembros. Además de fomentar la participación en ambientes "
            "competitivos y de socialización a nivel nacional e internacional."
        ),
        "category": "Competencias transversales",
        "faculty": "FCSH",
        "location": "FCSH, Auditorio",
        "areas": ["Social", "Académico"],
        "size": "mediano",
    },
    {
        "acronym": "FANPOL",
        "name": "FANPOL — Club de Cultura Asiática",
        "description": (
            "Es un club cultural fundado por estudiantes de la ESPOL al decidir "
            "convertir sus intereses en la cultura y las tendencias de la "
            "sociedad asiática en actividades las cuales pueden compartir "
            "experiencias tanto didácticas como recreativas. El club se divide "
            "en áreas de especialización: manualidades, gastronomía, cultura y "
            "expresión artística."
        ),
        "category": "Culturales",
        "faculty": "FADCOM",
        "location": "FADCOM, Sala de Usos Múltiples",
        "areas": ["Cultura", "Arte"],
        "size": "grande",
    },
    {
        "acronym": "TWEENING",
        "name": "Tweening — Club de Ilustración y Animación",
        "description": (
            "Club de ilustración, animación y guion. Dentro del club se "
            "desarrollan actividades que le permiten a cada uno de los miembros "
            "mejorar sus habilidades estéticas y gramaticales. Cada uno de los "
            "proyectos realizados promueve la creatividad y la imaginación, de "
            "modo que creamos piezas originales con estilos diferentes."
        ),
        "category": "Culturales",
        "faculty": "FADCOM",
        "location": "FADCOM, Laboratorio de Animación",
        "areas": ["Arte", "Cultura"],
        "size": "mediano",
    },
    {
        "acronym": "ARQUEOLOGÍA",
        "name": "Club de Arqueología Politécnico",
        "description": (
            "El Club de Arqueología Politécnico fomenta, promueve e incentiva "
            "el conocimiento de la arqueología y la antropología desde una "
            "nueva relación entre el ser humano y la historia; contribuyendo al "
            "redescubrimiento del pasado y la identidad cultural en la región."
        ),
        "category": "Culturales",
        "faculty": "FCSH",
        "location": "FCSH, Museo Arqueológico",
        "areas": ["Cultura", "Ciencia"],
        "size": "pequeño",
    },
    {
        "acronym": "ACUP",
        "name": "Acción Universitaria",
        "description": (
            "Promovemos Líderes Jóvenes comprometidos con el cambio del mundo "
            "desde una perspectiva católica."
        ),
        "category": "Competencias transversales",
        "faculty": "FCSH",
        "location": "Campus Gustavo Galindo, Capilla",
        "areas": ["Social", "Cultura"],
        "size": "mediano",
    },
    {
        # Único club que se siembra SIN líder resuelto: el catálogo tiene que
        # mostrar el estado 'Pending Leader' y el cliente debe poder pintarlo.
        "acronym": "ACP",
        "name": "Acción Cultural Politécnica",
        "description": (
            "Agrupación dedicada a la difusión de las artes y la cultura dentro "
            "de la comunidad politécnica, en articulación con los grupos "
            "artísticos de ESPOL Cultural."
        ),
        "category": "Culturales",
        "faculty": "FADCOM",
        "location": "Teatro ESPOL",
        "areas": ["Cultura", "Arte"],
        "size": "sin_lider",
    },
]

#: Cuántos miembros tiene la nómina según el tamaño declarado.
ROSTER_SIZES = {"grande": (18, 25), "mediano": (10, 17), "pequeño": (6, 9)}

# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------
#
# Plantillas por categoría de club. Los nombres se inspiran en actividades que
# el portal describe como propias del programa: cursos, charlas, capacitaciones,
# visitas técnicas, simposios y festivales.

EVENT_TEMPLATES = {
    "Profesionales": [
        ("Taller de {tema}", "Aula {aula}", "In-person"),
        ("Charla técnica: {tema}", "Auditorio {aula}", "Online"),
        ("Capacitación intensiva de {tema}", "Laboratorio {aula}", "In-person"),
        ("Visita técnica — {tema}", "Salida de campo", "In-person"),
        ("Simposio anual de {tema}", "Teatro ESPOL", "In-person"),
    ],
    "Culturales": [
        ("Festival de {tema}", "Teatro ESPOL", "In-person"),
        ("Taller creativo de {tema}", "Sala {aula}", "In-person"),
        ("Muestra abierta: {tema}", "Lobby del Teatro ESPOL", "In-person"),
        ("Conversatorio sobre {tema}", "Aula {aula}", "Online"),
    ],
    "Competencias transversales": [
        ("Torneo interno de {tema}", "Auditorio {aula}", "In-person"),
        ("Entrenamiento de {tema}", "Aula {aula}", "In-person"),
        ("Jornada de {tema}", "Campus Gustavo Galindo", "In-person"),
    ],
}

#: Temas por club, para que los eventos no sean intercambiables entre clubes.
EVENT_TOPICS = {
    "KOKOA": ["Git y control de versiones", "Linux desde cero", "Python aplicado"],
    "TAWS": ["React Native", "Ciencia de datos con Pandas", "APIs REST con Django"],
    "MECATRÓNICA": ["Impresión 3D", "Arduino e IoT", "Automatización industrial"],
    "NIOT": ["Redes definidas por software", "Sensores IoT", "Protocolos MQTT"],
    "MSP": ["Azure para estudiantes", "Power Platform", "Copilot y productividad"],
    "ASME": ["Diseño mecánico asistido", "Termodinámica aplicada", "Manufactura"],
    "ASCE": ["Diseño estructural", "Hormigón armado", "Obras hidráulicas"],
    "IIE": ["Lean manufacturing", "Gestión de calidad", "Simulación de procesos"],
    "IFT": ["Inocuidad alimentaria", "Desarrollo de nuevos productos", "Análisis sensorial"],
    "CLIP": ["Cadena de suministro", "Comercio exterior", "Gestión de inventarios"],
    "AAPG": ["Geología del petróleo", "Interpretación sísmica", "Cuencas sedimentarias"],
    "GISSC": ["QGIS aplicado", "Teledetección satelital", "Cartografía temática"],
    "ARGUMENTUM": ["debate parlamentario", "oratoria", "pensamiento crítico"],
    "FANPOL": ["gastronomía asiática", "caligrafía japonesa", "cultura coreana"],
    "TWEENING": ["ilustración digital", "animación 2D", "guion gráfico"],
    "ARQUEOLOGÍA": ["arqueología del Litoral", "cerámica precolombina", "patrimonio"],
    "ACUP": ["liderazgo y servicio", "voluntariado universitario", "ética"],
    "ACP": ["difusión cultural", "gestión de eventos artísticos"],
}

# ---------------------------------------------------------------------------
# Trámites ante GBP
# ---------------------------------------------------------------------------
#
# Tipos reales, tomados del Programa de Apoyo. Son mucho más concretos que un
# genérico "Nómina de Miembros": el portal pide un RollUp de 1,80 × 0,80 m en
# .ai o .psd, el logo actualizado y el diseño de camiseta (20 unidades, tallas
# por género), todos con fecha límite.

GBP_DOCUMENT_TYPES = [
    "Nómina de Miembros Activos",
    "Diseño de RollUp institucional",
    "Logo actualizado del club",
    "Diseño de camisetas del club",
    "Plan de actividades del período",
    "Informe de rendición de cuentas",
]

#: Observaciones que GBP escribe al rechazar. Reflejan los requisitos reales.
GBP_REJECTION_FEEDBACK = [
    "El RollUp no cumple las dimensiones requeridas (1,80 m de alto por 0,80 m "
    "de ancho). Vuelve a enviarlo con el formato correcto.",
    "El logo debe entregarse en formato vectorial (.ai o .psd). El archivo "
    "adjunto es una imagen rasterizada.",
    "La suma de tallas no llega a las 20 camisetas indicadas en el formulario.",
    "Falta la firma del presidente del club en la última página del documento.",
    "La nómina no coincide con los miembros registrados en el sistema para este "
    "período. Verifica y vuelve a enviarla.",
]

# ---------------------------------------------------------------------------
# Formularios dinámicos
# ---------------------------------------------------------------------------

MEMBERSHIP_FORM_FIELDS = [
    {
        "field_id": "motivacion",
        "label": "¿Por qué quieres unirte al club?",
        "type": "textarea",
        "required": True,
        "order": 1,
        "validation": {"max_length": 500},
    },
    {
        "field_id": "experiencia",
        "label": "Nivel de experiencia en el área del club",
        "type": "select",
        "required": True,
        "order": 2,
        "options": ["Ninguna", "Principiante", "Intermedio", "Avanzado"],
    },
    {
        "field_id": "disponibilidad",
        "label": "Horas semanales que puedes dedicar",
        "type": "number",
        "required": True,
        "order": 3,
        "validation": {"min_value": 1, "max_value": 20},
    },
    {
        "field_id": "intereses",
        "label": "Áreas de interés dentro del club",
        "type": "checkbox",
        "required": False,
        "order": 4,
        "options": ["Proyectos", "Capacitación", "Competencias", "Difusión"],
    },
]

EVENT_FORM_FIELDS = [
    {
        "field_id": "nivel",
        "label": "Nivel de conocimiento previo",
        "type": "radio",
        "required": True,
        "order": 1,
        "options": ["Principiante", "Intermedio", "Avanzado"],
    },
    {
        "field_id": "expectativa",
        "label": "¿Qué esperas del evento?",
        "type": "text",
        "required": False,
        "order": 2,
        "validation": {"max_length": 200},
    },
]

#: Roles personalizados. RF-07: el panel de roles debe mostrar algo más que los
#: cuatro por defecto.
CUSTOM_ROLES = [
    ("Encargado de Documentos", {"access_web_panel": True, "manage_documents": True}),
    ("Coordinador de Eventos", {"access_web_panel": True, "manage_events": True}),
    ("Staff de Eventos", {"scan_event_qr": True}),
    ("Encargado de Comunicación", {"access_web_panel": True}),
]

# ---------------------------------------------------------------------------
# Personas — ÚNICO bloque ficticio
# ---------------------------------------------------------------------------
#
# Nombres y apellidos frecuentes en Ecuador, combinados por el comando. No
# corresponden a personas reales, y las cuentas quedan marcadas como de
# demostración en su descripción de perfil.

FIRST_NAMES = [
    "Kevin", "María", "Diego", "Ana", "Lucía", "Andrés", "Josué", "Camila",
    "Mateo", "Valeria", "Sebastián", "Doménica", "Ricardo", "Emilia", "Bryan",
    "Nicole", "Alejandro", "Gabriela", "Christian", "Paola", "Jorge", "Isabella",
    "Luis", "Daniela", "Carlos", "Melissa", "Fernando", "Anahí", "Steven",
    "Génesis", "Óscar", "Karla", "Miguel", "Denisse", "Julio", "Mishell",
]

LAST_NAMES = [
    "Maldonado", "Cevallos", "Ponce", "Rivas", "Torres", "Vera", "Zambrano",
    "Mendoza", "Salazar", "Villacís", "Andrade", "Bermúdez", "Cedeño", "Espinoza",
    "Franco", "Guerrero", "Holguín", "Intriago", "Jaramillo", "León", "Macías",
    "Navarrete", "Ochoa", "Peñafiel", "Quinteros", "Rodríguez", "Solórzano",
    "Tomalá", "Ubilla", "Valdez", "Yagual", "Álvarez", "Bustamante", "Carrera",
]

#: Carrera por facultad, para que el perfil sea coherente con lo que declara.
CAREERS_BY_FACULTY = {
    "FIEC": [
        "Computación", "Telemática", "Electrónica y Automatización",
        "Telecomunicaciones", "Electricidad",
    ],
    "FIMCP": [
        "Ingeniería Mecánica", "Ingeniería Industrial",
        "Ingeniería en Materiales", "Ingeniería Química",
    ],
    "FICT": [
        "Ingeniería Civil", "Geología", "Minas", "Petróleos",
    ],
    "FCNM": [
        "Matemática", "Estadística", "Logística y Transporte",
    ],
    "FCSH": [
        "Economía", "Administración de Empresas", "Auditoría y Control de Gestión",
        "Turismo",
    ],
    "FCV": [
        "Ingeniería en Alimentos", "Biología", "Acuicultura", "Nutrición",
    ],
    "FADCOM": [
        "Diseño Gráfico", "Producción para Medios de Comunicación",
        "Diseño de Productos",
    ],
}

#: Rango de matrículas reservado para las cuentas de demostración. Empieza en
#: 2024 para que convivan estudiantes de distintas cohortes sin chocar con las
#: seis cuentas de MASTER §17, que usan matrículas de 2018 a 2023.
DEMO_ENROLLMENT_PREFIX = "2024"
DEMO_ENROLLMENT_START = 90000

#: Contraseña única de todas las cuentas generadas. Se reporta al terminar.
DEMO_PASSWORD = "espolclub2026"

DEMO_PROFILE_NOTE = (
    "Cuenta de demostración generada para poblar la API. No corresponde a una "
    "persona real."
)

SKILLS_POOL = [
    "Python", "JavaScript", "React", "SQL", "Git", "Figma", "AutoCAD", "MATLAB",
    "Excel avanzado", "Trabajo en equipo", "Oratoria", "Gestión de proyectos",
    "Illustrator", "Arduino", "QGIS", "Power BI",
]

# ---------------------------------------------------------------------------
# Documentos de club
# ---------------------------------------------------------------------------

CLUB_DOCUMENTS = [
    ("Estatutos del Club", False),
    ("Plan de Trabajo del Período", False),
    ("Brochure de Presentación", True),
    ("Convocatoria de Membresía", True),
]

#: Justificaciones de rechazo de solicitudes de membresía (RN-5).
APPLICATION_REJECTION_FEEDBACK = [
    "El cupo de este período ya está completo. Vuelve a postular el próximo "
    "PAO, tu perfil encaja bien con el club.",
    "La disponibilidad semanal que indicas no alcanza para las actividades del "
    "club este período. Te esperamos cuando tengas más tiempo.",
    "Necesitamos que completes la motivación con más detalle. Puedes volver a "
    "postular de inmediato.",
]
