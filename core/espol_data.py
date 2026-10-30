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

#
# Fechas del calendario oficial de grado
# (https://www.espol.edu.ec/es/vida-politecnica/calendario-grado): el inicio es
# el lunes de la primera semana de "Actividades formativas" y el fin, el último
# día de la semana de "PROCESO FINAL".

PAO_PERIODS = [
    {
        "pao_period": "2025-I",
        "start_date": datetime.date(2025, 5, 12),
        "end_date": datetime.date(2025, 9, 19),
        "activate": False,
    },
    {
        "pao_period": "2025-II",
        "start_date": datetime.date(2025, 9, 29),
        "end_date": datetime.date(2026, 2, 13),
        "activate": False,
    },
    {
        "pao_period": "2026-I",
        "start_date": datetime.date(2026, 5, 11),
        "end_date": datetime.date(2026, 9, 18),
        "activate": False,
    },
    {
        "pao_period": "2026-II",
        "start_date": datetime.date(2026, 9, 28),
        "end_date": datetime.date(2027, 2, 12),
        "activate": True,
    },
    {
        "pao_period": "2027-I",
        "start_date": datetime.date(2027, 5, 10),
        "end_date": datetime.date(2027, 9, 17),
        "activate": False,
    },
]

#: El período del que se renueva la nómina hacia el vigente.
PREVIOUS_PAO = "2026-I"
CURRENT_PAO = "2026-II"

# ---------------------------------------------------------------------------
# Áreas de interés
# ---------------------------------------------------------------------------
#
# ESPOL clasifica sus clubes en: Profesionales, Culturales, Competencias
# transversales y Grupos deportivos. El portal dice que los deportivos "por
# ahora no se incluye[n] en el programa", pero la categoría se acepta para poder
# sembrarlos si aparecen. Esa taxonomía se mapea al catálogo de áreas que ya
# existe en la base, sin tocar el modelo.

CATEGORY_TO_AREAS = {
    "Profesionales": ["Académico", "Tecnología"],
    "Culturales": ["Cultura", "Arte"],
    "Competencias transversales": ["Social", "Académico"],
    "Grupos deportivos": ["Deporte", "Social"],
}

# ---------------------------------------------------------------------------
# Clubes
# ---------------------------------------------------------------------------
#
# Los 18 que publica el portal de la Unidad de Bienestar Politécnico
# (https://oe.espol.edu.ec/clubes-y-organizaciones/), más CIAP, que no está en
# el portal pero sí en la página de grupos estudiantiles de la FIEC. Todos los
# datos se verificaron contra las páginas de ``sources``:
#
# * ``description`` es literal del portal; la de CIAP, de la página de la FIEC.
#   La excepción es ACP: el portal solo publica su nombre, y en su lugar va una
#   frase que lo dice en vez de una descripción inventada.
# * ``faculty`` es la facultad cuya página de grupos estudiantiles lista al
#   club. ``None`` si ninguna lo hace: son clubes abiertos a todas las carreras.
# * ``location`` es la oficina de la página de infraestructura de la FIEC
#   cuando existe. Si no, solo la facultad o el campus, sin inventar una sala.
# * ``image`` es el logo del portal (o de la facultad, si el del portal no
#   carga) y ``social_media``, los enlaces que publican el portal y las
#   facultades. Los sitios ``*.oe.espol.edu.ec`` van en http, como los publica
#   el portal: varios tienen el certificado vencido.
#
# ``areas`` y ``size`` son lo único elegido aquí. ``size`` solo dimensiona la
# nómina de demostración, que es ficticia.
#
# Quedan fuera los clubes de las facultades que no están en el portal y cuya
# descripción no es más que su nombre, o que no se ha revisado todavía.

_OE = "https://oe.espol.edu.ec/wp-content/uploads"
_PORTAL = "https://oe.espol.edu.ec/clubes-y-organizaciones/"
_FIEC_GROUPS = "https://www.fiec.espol.edu.ec/es/grupos-estudiantiles"
_FIEC_INFRA = "https://www.fiec.espol.edu.ec/es/infraestructura"
_FIMCP_GROUPS = "https://www.fimcp.espol.edu.ec/es/grupos-estudiantiles"
_FICT_GROUPS = "https://www.fict.espol.edu.ec/es/grupos-estudiantiles"
_FCNM_GROUPS = "https://www.fcnm.espol.edu.ec/es/grupos-estudiantiles"
_FCSH_GROUPS = "https://www.fcsh.espol.edu.ec/es/grupos-estudiantiles"
_FADCOM_GROUPS = "https://www.fadcom.espol.edu.ec/es/grupos-estudiantiles"

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
        "location": "FIEC, Bloque 11D, oficina 11D-O003",
        "areas": ["Tecnología", "Académico", "Ciencia"],
        "size": "grande",
        "image": f"{_OE}/2014/11/kokoa.png",
        "social_media": [
            {"network": "Sitio web", "link": "https://www.kokoa.club/"},
            {"network": "Sitio ESPOL", "link": "http://kokoa.oe.espol.edu.ec/"},
            {"network": "Instagram", "link": "https://www.instagram.com/kokoa_espol/"},
            {"network": "Facebook", "link": "https://www.facebook.com/kokoaespol/"},
            {"network": "X", "link": "https://twitter.com/kokoaespol"},
            {"network": "GitHub", "link": "https://github.com/kokoaespol"},
            {"network": "YouTube", "link": "https://www.youtube.com/@kokoaespol1"},
            {"network": "Linktree", "link": "https://linktr.ee/kokoaespol"},
        ],
        "sources": [_PORTAL, _FIEC_GROUPS, _FIEC_INFRA, "https://www.kokoa.club/events"],
    },
    {
        "acronym": "CIAP",
        "name": "Club de Inteligencia Artificial Politécnico",
        "description": (
            "Promovemos el aprendizaje e investigación, en inteligencia "
            "artificial y análisis de datos, ofreciendo talleres, conferencias "
            "y proyectos colaborativos para desarrollar habilidades aplicables "
            "en el entorno empresarial."
        ),
        "category": "Profesionales",
        "faculty": "FIEC",
        "location": "FIEC, Bloque 11D",
        "areas": ["Tecnología", "Ciencia", "Académico"],
        "size": "mediano",
        "image": (
            "https://www.fiec.espol.edu.ec/sites/default/files/styles/"
            "teacher_photo/public/2025-06/logo_ciap_1.png?itok=fnPcneE9"
        ),
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://ciap.oe.espol.edu.ec/"},
            {"network": "Instagram", "link": "https://www.instagram.com/ciap_espol"},
            {"network": "GitHub", "link": "https://github.com/CiapEspol"},
        ],
        "sources": [_FIEC_GROUPS, _FIEC_INFRA],
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
        "location": "FIEC, Campus Gustavo Galindo",
        "areas": ["Tecnología", "Académico"],
        "size": "grande",
        "image": f"{_OE}/2015/01/taws.png",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://taws.oe.espol.edu.ec/"},
            {"network": "Facebook", "link": "https://www.facebook.com/tawsespol/"},
            {"network": "X", "link": "https://twitter.com/TawsEspol"},
        ],
        "sources": [_PORTAL, _FIEC_GROUPS],
    },
    {
        "acronym": "MECATRÓNICA",
        "name": "Club de Mecatrónica",
        "description": (
            "El Club de Mecatrónica tiene por objeto impulsar el desarrollo de "
            "competencias en el ámbito tecnológico, particularmente en el "
            "desarrollo de sistemas mecatrónicas, IOT, manufactura aditiva, "
            "software y aplicaciones para el control y automatización de "
            "procesos."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Tecnología", "Ciencia"],
        "size": "mediano",
        # El logo del portal devuelve 404; este es el de la FIMCP.
        "image": (
            "https://www.fimcp.espol.edu.ec/sites/default/files/styles/"
            "teacher_photo/public/2023-09/logo%20Club-de-mecatr%C3%B3nica.jpg"
            "?itok=TdEAfezL"
        ),
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://clubmecatronica.oe.espol.edu.ec/"},
            {
                "network": "Facebook",
                "link": "https://www.facebook.com/Club-Mecatr%C3%B3nica-ESPOL-584070041803082/",
            },
            {"network": "Instagram", "link": "https://www.instagram.com/club_mecatronica_espol/"},
            {"network": "X", "link": "https://x.com/club_espol"},
        ],
        "sources": [_PORTAL, _FIMCP_GROUPS],
    },
    {
        "acronym": "NIOT",
        "name": "Grupo estudiantil NIoT",
        "description": (
            "Cooperamos con la sociedad del conocimiento en el desarrollo de "
            "Aplicaciones web y móviles integrados con servicios telemáticos, "
            "internet de las Cosas, tecnologías de la Información y la "
            "Comunicación, para la formación académica de estudiantes e "
            "investigadores."
        ),
        "category": "Profesionales",
        "faculty": "FIEC",
        "location": "FIEC, Bloque 11D, oficina 11D-O104",
        "areas": ["Tecnología", "Académico"],
        "size": "mediano",
        "image": f"{_OE}/2020/08/NIoT_logo-e1598887865900.png",
        # Ni el portal ni la FIEC publican enlaces: la FIEC muestra
        # "@ClubNiotEspol", pero el enlace apunta a su propia portada.
        "social_media": [],
        "sources": [_PORTAL, _FIEC_GROUPS, _FIEC_INFRA],
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
        "location": "FIEC, Bloque 11F, oficina 11F-O109",
        "areas": ["Tecnología", "Emprendimiento"],
        "size": "mediano",
        "image": f"{_OE}/2020/09/CELULA-ESTUDIANTIL.png",
        # La FIEC enlaza también https://celula.espol.edu.ec/, que no responde.
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://celula.oe.espol.edu.ec/"},
        ],
        "sources": [_PORTAL, _FIEC_GROUPS, _FIEC_INFRA],
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
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Académico", "Tecnología"],
        "size": "mediano",
        "image": f"{_OE}/2014/09/asme.png",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://asme.oe.espol.edu.ec/"},
            {"network": "Facebook", "link": "https://www.facebook.com/ASMEESPOL/"},
            {"network": "Instagram", "link": "https://www.instagram.com/asme_espol/"},
            {"network": "X", "link": "https://x.com/ASME_ESPOL"},
        ],
        "sources": [_PORTAL, _FIMCP_GROUPS],
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
        "location": "FICT, Campus Gustavo Galindo",
        "areas": ["Académico", "Ciencia"],
        "size": "mediano",
        "image": f"{_OE}/2020/12/ASCE.png",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://asce.oe.espol.edu.ec/"},
            {"network": "Instagram", "link": "https://www.instagram.com/asce.espol/"},
            {"network": "Facebook", "link": "https://www.facebook.com/asce.espol/"},
            {"network": "X", "link": "https://x.com/asce_espol"},
            {"network": "LinkedIn", "link": "https://www.linkedin.com/in/asce-espol/"},
        ],
        "sources": [_PORTAL, _FICT_GROUPS],
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
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Académico", "Emprendimiento"],
        "size": "pequeño",
        "image": f"{_OE}/2014/09/iie.png",
        # La FIMCP lo lista con su nombre actual, IISE.
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://iie.oe.espol.edu.ec/"},
            {"network": "Facebook", "link": "https://www.facebook.com/IieEspol/"},
            {"network": "Instagram", "link": "https://www.instagram.com/iise_espol/"},
            {"network": "X", "link": "https://x.com/iise_espol"},
            {
                "network": "YouTube",
                "link": "https://www.youtube.com/channel/UCadEFapRPARcNfOBfdcDcLg",
            },
        ],
        "sources": [_PORTAL, _FIMCP_GROUPS],
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
        "faculty": "FIMCP",
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
        "image": f"{_OE}/2020/10/IFT-e1602768041326.png",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://ift.oe.espol.edu.ec/"},
            {
                "network": "Facebook",
                "link": "https://www.facebook.com/profile.php?id=100010197914639",
            },
            {"network": "Instagram", "link": "https://www.instagram.com/ift_espol/"},
            {"network": "X", "link": "https://x.com/IFT_ESPOL"},
        ],
        "sources": [_PORTAL, _FIMCP_GROUPS],
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
        "faculty": "FCNM",
        "location": "FCNM, Campus Gustavo Galindo",
        "areas": ["Académico", "Emprendimiento"],
        "size": "mediano",
        "image": f"{_OE}/2020/10/CLIP-LOGO-FIN--e1603724968841.png",
        "social_media": [
            {"network": "Sitio web", "link": "https://clublogistico.wixsite.com/clipespol"},
            {"network": "Instagram", "link": "https://www.instagram.com/clip_espol/"},
        ],
        "sources": [_PORTAL, _FCNM_GROUPS],
    },
    {
        "acronym": "AAPG",
        "name": "American Association of Petroleum Geologists — Capítulo ESPOL",
        "description": (
            "Proporcionar a las miembros habilidades que serán valiosas "
            "herramientas para su vida profesional, mediante conferencias, "
            "cursos y diferentes actividades con información actualizada acerca "
            "de la ciencia de la geología del petróleo."
        ),
        "category": "Profesionales",
        "faculty": "FICT",
        "location": "FICT, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
        "image": f"{_OE}/2020/10/AAPGN-e1602715475382.jpg",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://aapg.oe.espol.edu.ec/"},
            {"network": "Instagram", "link": "https://www.instagram.com/aapgespol/"},
            {"network": "Facebook", "link": "https://www.facebook.com/AAPGESPOL"},
            {"network": "X", "link": "https://x.com/AAPGESPOL"},
            {"network": "LinkedIn", "link": "https://www.linkedin.com/company/aapgespol/"},
        ],
        "sources": [_PORTAL, _FICT_GROUPS],
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
        "location": "FICT, Campus Gustavo Galindo",
        "areas": ["Tecnología", "Ciencia"],
        "size": "pequeño",
        "image": f"{_OE}/2021/06/Logo-GISSC-v01-1.png",
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/gissc_espol/"},
            {"network": "Facebook", "link": "https://www.facebook.com/GISSC1.ESPOL"},
            {"network": "X", "link": "https://x.com/gissc_espol"},
            {
                "network": "LinkedIn",
                "link": "https://www.linkedin.com/in/gissc-espol-025652244/",
            },
        ],
        "sources": [_PORTAL, _FICT_GROUPS],
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
        "faculty": None,
        "location": "Campus Gustavo Galindo",
        "areas": ["Social", "Académico"],
        "size": "mediano",
        "image": f"{_OE}/2020/09/ARGUMENTUM.png",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://argumentum.oe.espol.edu.ec/"},
        ],
        "sources": [_PORTAL],
    },
    {
        "acronym": "FANPOL",
        "name": "FANPOL — Club de Cultura Asiática",
        "description": (
            "Es un club cultural fundado por estudiantes de la ESPOL al decidir "
            "convertir sus intereses en la cultura y las tendencias de la "
            "sociedad asiática en actividades las cuales pueden compartir "
            "experiencias tanto didácticas como recreativas. El club se divide "
            "en áreas de especialización en las cuales los miembros pueden "
            "participar libremente: Manualidades Gastronomía Cultura, y; "
            "Expresión artística"
        ),
        "category": "Culturales",
        "faculty": None,
        "location": "Campus Gustavo Galindo",
        "areas": ["Cultura", "Arte"],
        "size": "grande",
        "image": f"{_OE}/2020/09/FANPOL-e1598968477425.png",
        "social_media": [
            {"network": "Sitio web", "link": "https://clubfanpol.wixsite.com/fanpol"},
        ],
        "sources": [_PORTAL],
    },
    {
        "acronym": "TWEENING",
        "name": "Tweening — Club de Ilustración y Animación",
        "description": (
            "Club de ilustración, animación y guion. Dentro del club se "
            "desarrolla actividades que le permite a cada uno de los miembros "
            "mejorar sus habilidades estéticas y gramaticales. Cada uno de los "
            "proyectos realizados promueve la creatividad y la imaginación, de "
            "modo que creamos piezas originales con estilos diferentes."
        ),
        "category": "Culturales",
        "faculty": "FADCOM",
        "location": "FADCOM, Campus Gustavo Galindo",
        "areas": ["Arte", "Cultura"],
        "size": "mediano",
        "image": f"{_OE}/2021/06/LOGO-TWEENING-2-1.png",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://tweening.oe.espol.edu.ec/"},
            {"network": "Instagram", "link": "https://www.instagram.com/tweening_club/"},
        ],
        "sources": [_PORTAL, _FADCOM_GROUPS],
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
        "location": "FCSH, Campus Gustavo Galindo",
        "areas": ["Cultura", "Ciencia"],
        "size": "pequeño",
        "image": f"{_OE}/2021/06/logo_club_arqueolog%C3%ADa2.jpg",
        "social_media": [
            {"network": "Facebook", "link": "https://www.facebook.com/ClubArqueologia.ESPOL"},
            {"network": "Instagram", "link": "https://www.instagram.com/clubarqueologia.espol/"},
        ],
        "sources": [_PORTAL, _FCSH_GROUPS],
    },
    {
        "acronym": "ACUP",
        "name": "Acción Universitaria",
        "description": (
            "Promovemos Líderes Jóvenes comprometidos con el cambio del mundo "
            "desde una perspectiva católica."
        ),
        "category": "Competencias transversales",
        "faculty": None,
        "location": "Campus Gustavo Galindo",
        "areas": ["Social", "Cultura"],
        "size": "mediano",
        "image": f"{_OE}/2014/09/accion.png",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://accionuniversitaria.oe.espol.edu.ec/"},
        ],
        "sources": [_PORTAL],
    },
    {
        # Único club que se siembra SIN líder resuelto: el catálogo tiene que
        # mostrar el estado 'Pending Leader' y el cliente debe poder pintarlo.
        "acronym": "ACP",
        "name": "Acción Cultural Politécnica",
        "description": (
            "Club estudiantil de la ESPOL. La Unidad de Bienestar Politécnico "
            "todavía no publica su descripción."
        ),
        "category": "Culturales",
        "faculty": None,
        "location": "Campus Gustavo Galindo",
        "areas": ["Cultura", "Arte"],
        "size": "sin_lider",
        "image": f"{_OE}/2021/10/Logo_ACP_negro-e1633622108994.png",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://acp.oe.espol.edu.ec/"},
        ],
        "sources": [_PORTAL],
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
    "Grupos deportivos": [
        ("Entrenamiento abierto de {tema}", "Cancha {aula}", "In-person"),
        ("Torneo interno de {tema}", "Instalaciones deportivas de ESPOL", "In-person"),
        ("Clínica de {tema}", "Cancha {aula}", "In-person"),
    ],
}

#: Temas por club, para que los eventos no sean intercambiables entre clubes.
EVENT_TOPICS = {
    "KOKOA": ["Git y control de versiones", "Linux desde cero", "Python aplicado"],
    "CIAP": ["Machine Learning", "visión por computador", "análisis de datos"],
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

#: Eventos reales, publicados por el club o por ESPOL. Sustituyen a los eventos
#: pasados generados con plantilla; los presentes y futuros se siguen generando,
#: porque sin ellos no habría a qué inscribirse ni qué escanear.
#:
#: Las fuentes no publican la hora: la elige el comando, igual que en los
#: eventos de plantilla. Nombre, fecha, modalidad, lugar y descripción son
#: literales.
REAL_EVENTS = {
    # https://www.kokoa.club/events
    "KOKOA": [
        {
            "event_name": "FliSol 2025",
            "date": datetime.date(2025, 5, 31),
            "mode": "In-person",
            "planned_place": "Universidad Católica de Santiago de Guayaquil (UCSG)",
            "description": (
                "FLISoL es el evento más grande de difusión de Software Libre "
                "en América Latina. Su objetivo es promover las 4 libertades "
                "del Software Libre."
            ),
        },
        {
            "event_name": "Feria Vive ESPOL",
            "date": datetime.date(2025, 8, 29),
            "mode": "In-person",
            "planned_place": "FIEC, ESPOL",
            "description": (
                "Evento para mostrar proyectos y compartir con la comunidad de "
                "FIEC en la feria Vive ESPOL."
            ),
        },
        {
            "event_name": "Taller KiCAD",
            "date": datetime.date(2025, 9, 19),
            "mode": "Virtual",
            "planned_place": "Virtual",
            "description": (
                "Diseño de circuitos electrónicos impresos (PCB) con software "
                "libre KiCAD."
            ),
        },
        {
            "event_name": "Taller Open Hardware",
            "date": datetime.date(2025, 9, 27),
            "mode": "Virtual",
            "planned_place": "Virtual",
            "description": "Introducción al hardware libre y sus aplicaciones.",
        },
        {
            "event_name": "Análisis de Datos",
            "date": datetime.date(2025, 9, 28),
            "mode": "Virtual",
            "planned_place": "Virtual",
            "description": "Fundamentos de análisis y ciencia de datos.",
        },
    ],
    # https://www.i3lab.org/noticias/2025/12/10/expoclubes-2025-creatividad-tecnologa-e-innovacin-brillan-en-la-semana-de-la-innovacin-de-espol
    "CIAP": [
        {
            "event_name": "ExpoClubes 2025",
            "date": datetime.date(2025, 11, 25),
            "mode": "In-person",
            "planned_place": "Lobby del Auditorio STEM",
            "description": (
                "Entre los clubes destacados, el Club de Inteligencia "
                "Artificial Politécnico (CIAP) presentó “Entre Galaxias y "
                "Robots”, una experiencia donde los asistentes exploraron "
                "modelos de Inteligencia Artificial aplicados al análisis de "
                "patrones."
            ),
        },
    ],
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
#:
#: Nombres literales de la oferta de grado
#: (https://www.espol.edu.ec/es/admision/oferta-academica).
CAREERS_BY_FACULTY = {
    "FIEC": [
        "Ciencia de Datos e Inteligencia Artificial (Hibrido)", "Computación",
        "Electricidad", "Electrónica y Automatización", "Telecomunicaciones",
        "Telemática",
    ],
    "FIMCP": [
        "Alimentos", "Ingeniería Industrial", "Materiales", "Mecánica",
        "Mecatrónica",
    ],
    "FICT": [
        "Geología", "Ingeniería Civil", "Minas", "Petróleos",
    ],
    "FCNM": [
        "Estadística", "Ingeniería Química", "Logistica y Transporte",
        "Matemática",
    ],
    "FCSH": [
        "Administración de Empresas", "Arqueología",
        "Auditoría y Control de Gestión", "Economía", "Turismo",
    ],
    "FCV": [
        "Biología", "Ingeniería Agrícola y Biológica",
    ],
    "FADCOM": [
        "Animación Digital y Videojuegos", "Diseño de Productos",
        "Diseño Gráfico", "Producción para Medios de Comunicación",
    ],
    "FIMCM": [
        "Acuicultura", "Ingeniería Naval", "Oceanografía",
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
