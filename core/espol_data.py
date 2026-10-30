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
# (https://oe.espol.edu.ec/clubes-y-organizaciones/); después, los que solo
# aparecen en las páginas de grupos estudiantiles de las facultades, y el CDS,
# que publica la Unidad de Sostenibilidad. Todos los datos se verificaron
# contra las páginas de ``sources``:
#
# * ``description`` es literal: del portal cuando el club está ahí, y si no,
#   de la página que lo lista. Se omite la línea "Correo: ..." con la que las
#   facultades cierran algunas descripciones. La excepción es ACP: el portal
#   solo publica su nombre, y en su lugar va una frase que lo dice en vez de
#   una descripción inventada.
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
# Quedan fuera los clubes cuya descripción publicada no es más que su nombre
# (CADIEC, Suitcase, 593 Guides), los que no tienen descripción en ninguna
# fuente legible (CERIT, CARI, IEEE-HKN Nu Zeta, Club Fotográfico, Club de
# Emprendedores, Inecyc, Slow Food, AIROS) y las asociaciones de estudiantes de
# cada facultad, que no son clubes.

_OE = "https://oe.espol.edu.ec/wp-content/uploads"
_PORTAL = "https://oe.espol.edu.ec/clubes-y-organizaciones/"
_FIEC_GROUPS = "https://www.fiec.espol.edu.ec/es/grupos-estudiantiles"
_FIEC_INFRA = "https://www.fiec.espol.edu.ec/es/infraestructura"
_FIMCP_GROUPS = "https://www.fimcp.espol.edu.ec/es/grupos-estudiantiles"
_FICT_GROUPS = "https://www.fict.espol.edu.ec/es/grupos-estudiantiles"
_FCNM_GROUPS = "https://www.fcnm.espol.edu.ec/es/grupos-estudiantiles"
_FCSH_GROUPS = "https://www.fcsh.espol.edu.ec/es/grupos-estudiantiles"
_FADCOM_GROUPS = "https://www.fadcom.espol.edu.ec/es/grupos-estudiantiles"
_FIMCM_GROUPS = "https://www.fimcm.espol.edu.ec/es/grupos-estudiantiles"
_I3LAB = "https://www.i3lab.org/clubes-y-capitulos"
_SOSTENIBILIDAD = "https://sostenibilidad.espol.edu.ec/comunidad"


def _logo(faculty, path):
    """Logo publicado en la página de grupos estudiantiles de una facultad."""
    return (
        f"https://www.{faculty}.espol.edu.ec/sites/default/files/styles/"
        f"teacher_photo/public/{path}"
    )


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
            {"network": "Instagram", "link": "https://www.instagram.com/taws_espol"},
        ],
        "sources": [_PORTAL, _FIEC_GROUPS, _I3LAB],
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
            {"network": "Facebook", "link": "https://www.facebook.com/accionistaespol"},
        ],
        "sources": [_PORTAL, _I3LAB],
    },
    # -- Solo en las páginas de las facultades -----------------------------
    {
        "acronym": "PHYCOM",
        "name": "PHYCOM",
        "description": (
            "Impulsa el aprendizaje de electrónica, programación y robótica con "
            "proyectos creativos, inclusivos e interdisciplinarios; "
            "experimentando la tecnología de forma tangible, combinando "
            "ciencia, arte y resolución de problemas."
        ),
        "category": "Profesionales",
        "faculty": "FIEC",
        "location": "FIEC, Campus Gustavo Galindo",
        "areas": ["Tecnología", "Arte"],
        "size": "pequeño",
        "image": _logo("fiec", "2025-06/logo_phycom_0.png?itok=8vgIKYLL"),
        "social_media": [
            {"network": "Linktree", "link": "https://linktr.ee/phycom"},
            {"network": "Instagram", "link": "https://www.instagram.com/phycom_espol"},
        ],
        "sources": [_FIEC_GROUPS, _I3LAB],
    },
    {
        "acronym": "IEEE",
        "name": "Rama Estudiantil IEEE – ESPOL",
        "description": (
            "Organización sin fines de lucro, que fomenta y promueve la "
            "investigación, desarrollando así el interés de los futuros "
            "ingenieros en la consecución de avances tecnológicos."
        ),
        "category": "Profesionales",
        "faculty": "FIEC",
        "location": "FIEC, Bloque 11D, oficina 11D-O002",
        "areas": ["Tecnología", "Académico"],
        "size": "grande",
        "image": _logo("fiec", "2023-08/logo%20Ieee.png?itok=lV7Fql4h"),
        "social_media": [
            {"network": "Sitio web", "link": "https://site.ieee.org/sb-espol/"},
            {"network": "Instagram", "link": "https://www.instagram.com/ieee.espol/"},
            {"network": "LinkedIn", "link": "https://www.linkedin.com/company/ieee-espol/"},
        ],
        "sources": [_FIEC_GROUPS, _FIEC_INFRA],
    },
    {
        "acronym": "SPE",
        "name": "SPE ESPOL — Society of Petroleum Engineers",
        "description": (
            "El Capítulo Estudiantil de la Sociedad de Ingenieros de Petróleo, "
            "fundado en Ecuador el 1 de junio de 1994, enriquece el campo "
            "profesional con talleres y prácticas académicas."
        ),
        "category": "Profesionales",
        "faculty": "FICT",
        "location": "FICT, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "mediano",
        "image": _logo("fict", "2023-07/FICT-logoSPE.png?itok=MjcCjZJY"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/espolspe/"},
            {"network": "Facebook", "link": "https://www.facebook.com/ESPOLSPE"},
            {"network": "X", "link": "https://x.com/ESPOLSPE"},
            {"network": "LinkedIn", "link": "https://www.linkedin.com/in/spe-espol-71953b204/"},
        ],
        "sources": [_FICT_GROUPS],
    },
    {
        "acronym": "ACI",
        "name": "ACI ESPOL — American Concrete Institute",
        "description": (
            "La misión del capítulo estudiantil es capacitar a sus miembros en "
            "competencias técnicas del cemento y hormigón aprovechando los "
            "programas que ofrece el American Concrete Institute (ACI)."
        ),
        "category": "Profesionales",
        "faculty": "FICT",
        "location": "FICT, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
        "image": _logo("fict", "2023-07/ACI%20%281%29.png?itok=h9s7Bq56"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/aci_espol/"},
            {"network": "Facebook", "link": "https://www.facebook.com/aciespol"},
            {"network": "X", "link": "https://x.com/ACI_ESPOL"},
            {
                "network": "LinkedIn",
                "link": "https://www.linkedin.com/in/aci-espol-student-chapter-093872174/",
            },
        ],
        "sources": [_FICT_GROUPS],
    },
    {
        "acronym": "SME",
        "name": "SME ESPOL — Society for Mining, Metallurgy & Exploration",
        "description": (
            "La misión de este capítulo es que sus miembros se encuentren entre "
            "los profesionales más formados, titulares y exitosos de la "
            "industria de los minerales."
        ),
        "category": "Profesionales",
        "faculty": "FICT",
        "location": "FICT, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
        "image": _logo("fict", "2023-07/FICT-logoSME.png?itok=IJRdeDf7"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/smeespol/"},
            {"network": "Facebook", "link": "https://www.facebook.com/espolsme"},
            {"network": "X", "link": "https://x.com/SME_ESPOL"},
        ],
        "sources": [_FICT_GROUPS],
    },
    {
        "acronym": "IAHR",
        "name": "IAHR ESPOL — International Association for Hydro-Environment Engineering and Research",
        "description": (
            "El Capítulo Estudiantil IAHR-ESPOL tiene el compromiso de fomentar "
            "el interés en la trascendencia de los temas hidroambientales, a "
            "través de la conexión intelectual en las distintas disciplinas "
            "académicas que oferta la ESPOL."
        ),
        "category": "Profesionales",
        "faculty": "FICT",
        "location": "FICT, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
        "image": _logo("fict", "2024-02/logo_iahr-espol_oficial.png?itok=nCIjnEGt"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/iahrespol/"},
            {"network": "Facebook", "link": "https://www.facebook.com/IAHRESPOL"},
            {"network": "X", "link": "https://twitter.com/IAHRESPOL"},
            {"network": "YouTube", "link": "https://www.youtube.com/@iahrespol1521"},
        ],
        "sources": [_FICT_GROUPS],
    },
    {
        "acronym": "ASHRAE",
        "name": (
            "ASHRAE — Sociedad Americana de Ingenieros en Calefacción, "
            "Refrigeración y Aire Acondicionado"
        ),
        "description": (
            "Es una organización diversa dedicada a promover las artes y las "
            "ciencias de calefacción, ventilación, aire acondicionado y "
            "refrigeración para servir a la humanidad y promover un mundo "
            "sostenible."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Tecnología"],
        "size": "pequeño",
        "image": _logo("fimcp", "2023-09/logo%20ASHRAE.jpg?itok=-oQAKhqx"),
        "social_media": [
            {"network": "Facebook", "link": "https://www.facebook.com/ashrae.espol"},
            {"network": "Instagram", "link": "https://www.instagram.com/ashrae_espol/"},
            {"network": "X", "link": "https://x.com/ashrae_espol"},
        ],
        "sources": [_FIMCP_GROUPS],
    },
    {
        "acronym": "AWS",
        "name": "AWS — Sociedad Americana de Soldadura",
        "description": (
            "Dirigido a estudiantes de carreras pertenecientes a la FIMCP. La "
            "Sociedad Americana de Soldadura (AWS) reconoce la importancia de "
            "adquirir vasto conocimiento en el tema de fusionar materiales."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Tecnología"],
        "size": "pequeño",
        "image": _logo("fimcp", "2023-09/logo%20AWS.jpg?itok=dOO0QMpw"),
        "social_media": [
            {"network": "Facebook", "link": "https://www.facebook.com/awsespol/"},
            {"network": "Instagram", "link": "https://www.instagram.com/awsespol"},
        ],
        "sources": [_FIMCP_GROUPS, _I3LAB],
    },
    {
        "acronym": "CIMAT",
        "name": "CIMAT — Club de Ingeniería en Materiales",
        "description": (
            "Es un capítulo estudiantil dedicado a acercar a los estudiantes "
            "interesados en la ingeniería de los materiales y a conocer todo lo "
            "relacionado a estos."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
        "image": _logo("fimcp", "2023-09/logo%20CIMAT.jpg?itok=pyK98X6T"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/club_cimat/"},
            {
                "network": "Facebook",
                "link": (
                    "https://www.facebook.com/people/"
                    "CIMATClub-de-Ciencia-e-Ingenier%C3%ADa-en-Materiales/100041334229219/"
                ),
            },
            {"network": "X", "link": "https://x.com/CCimat"},
            {"network": "LinkedIn", "link": "https://www.linkedin.com/in/club-cimat-9528ba216/"},
        ],
        "sources": [_FIMCP_GROUPS],
    },
    {
        "acronym": "MAEC",
        "name": "MAEC — Mecánica Automotriz ESPOL Club",
        "description": (
            "Integrado por estudiantes quienes motivan y propagan el "
            "conocimiento de la mecánica automotriz con la práctica en base a "
            "los conocimientos académicos recibidos, con el fin de desarrollar "
            "profesionales capaces de gestionar, dirigir e innovar proyectos "
            "asociados a la rama."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Tecnología", "Académico"],
        "size": "pequeño",
        "image": _logo("fimcp", "2023-09/logo%20maec.jpg?itok=oOO5hc3d"),
        # La FIMCP solo publica su correo.
        "social_media": [],
        "sources": [_FIMCP_GROUPS],
    },
    {
        "acronym": "RAS",
        "name": "RAS / IEEE — Sociedad de Robótica & Automatización",
        "description": (
            "Nuestro capítulo lucha por el avance de la teoría y práctica de la "
            "ingeniería, ciencia de la robótica y la automatización, las artes "
            "y ciencias afines, y por el mantenimiento de altos estándares "
            "profesionales entre sus miembros."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Tecnología", "Ciencia"],
        "size": "pequeño",
        "image": _logo("fimcp", "2023-09/logo%20IEEEE.jpg?itok=TeP-druQ"),
        "social_media": [
            {"network": "Facebook", "link": "https://www.facebook.com/RASESPOL/"},
            {"network": "Instagram", "link": "https://www.instagram.com/ras_espol/"},
        ],
        "sources": [_FIMCP_GROUPS],
    },
    {
        "acronym": "ROBOTA",
        "name": "ROBOTA — Club de Robótica",
        "description": (
            "El club se dedica a la construcción de prototipos de robótica de "
            "competición, así como a proyectos de investigación y desarrollo "
            "en diversos campos (social, médico, industrial, etc.)."
        ),
        "category": "Profesionales",
        "faculty": "FIMCP",
        "location": "FIMCP, Campus Gustavo Galindo",
        "areas": ["Tecnología", "Ciencia"],
        "size": "mediano",
        "image": _logo("fimcp", "2023-09/logo%20Robota.jpg?itok=0PpljKKs"),
        "social_media": [
            {"network": "Facebook", "link": "https://www.facebook.com/robotaespol"},
            {"network": "Instagram", "link": "https://www.instagram.com/club_robotica_robota/"},
            {"network": "X", "link": "https://x.com/CLUB_ROBOTA"},
        ],
        "sources": [_FIMCP_GROUPS],
    },
    {
        "acronym": "AICHE",
        "name": "AIChE – ESPOL",
        "description": (
            "Un capítulo de AIChE Global (American Institute of Chemical "
            "Engineers) que se enfoca en el desarrollo académico complementario "
            "a estudiantes de Ing. Química y carreras afines. Se realizan foros "
            "de industria, charlas con profesionales del área industrial y "
            "profesores, ayudantías para los alumnos sobre materias de la "
            "carrera, además de actividades sociales."
        ),
        "category": "Profesionales",
        "faculty": "FCNM",
        "location": "FCNM, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "mediano",
        "image": _logo("fcnm", "2023-08/FCNM%20logo%20AIChE.webp?itok=wbqJk7Z-"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/aiche.espol/"},
            {"network": "Facebook", "link": "https://www.facebook.com/AIChE.ESPOL1"},
        ],
        "sources": [_FCNM_GROUPS, _I3LAB],
    },
    {
        "acronym": "D.A.T.A",
        "name": "D.A.T.A Club — Data Analysis Technology Algorithms Club",
        "description": (
            "Un club estudiantil que busca impulsar y promover el desarrollo de "
            "conocimientos estadísticos para la comunidad politécnica y la "
            "sociedad en general, brindando oportunidades para aprender y "
            "discutir la transversalidad de la estadística en distintas áreas, "
            "desarrollando habilidades profesionales."
        ),
        "category": "Profesionales",
        "faculty": "FCNM",
        "location": "FCNM, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Tecnología"],
        "size": "pequeño",
        "image": _logo("fcnm", "2023-08/FCNM%20logo%20DATA.webp?itok=SjMS4yPn"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/dataclubec/"},
        ],
        "sources": [_FCNM_GROUPS],
    },
    {
        "acronym": "MATES",
        "name": "MatEs",
        "description": (
            "Un club estudiantil que invita a conocer el mundo de las "
            "matemáticas por medio de actividades divulgativas y académicas, "
            "como conversatorios, sesiones de estudio y clases; entrenamientos "
            "y participación en olimpiadas de matemática, nacionales e "
            "internacionales; escuelas de matemáticas."
        ),
        "category": "Profesionales",
        "faculty": "FCNM",
        "location": "FCNM, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
        "image": _logo("fcnm", "2025-08/clubmates.png?itok=SPxT5M83"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/mates_espol/"},
        ],
        "sources": [_FCNM_GROUPS],
    },
    {
        "acronym": "ALUCINE",
        "name": "ALUCINE — Club de Cine de ESPOL",
        "description": (
            "Alucine es una familia de amigos unida por la experiencia "
            "colectiva de ver, vivir y compartir la pasión por el séptimo arte. "
            "Se realizan diferentes actividades dentro del club, como "
            "proyecciones, cine coloquios y cine ciclos de diferentes películas."
        ),
        "category": "Culturales",
        "faculty": "FADCOM",
        "location": "FADCOM, Campus Gustavo Galindo",
        "areas": ["Arte", "Cultura"],
        "size": "mediano",
        "image": _logo(
            "fadcom", "2023-08/logo%20club%20alucine%20218x160.webp?itok=v6Z3BOrR"
        ),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/alucineclub/"},
        ],
        "sources": [_FADCOM_GROUPS],
    },
    {
        "acronym": "D-PRO",
        "name": "D-PRO — Club de Diseño de Productos",
        "description": (
            "Nuestro propósito es fomentar la creatividad, el pensamiento "
            "crítico y la innovación a través de actividades que integran "
            "teoría, práctica y trabajo colaborativo."
        ),
        "category": "Profesionales",
        "faculty": "FADCOM",
        "location": "FADCOM, Campus Gustavo Galindo",
        "areas": ["Arte", "Emprendimiento"],
        "size": "pequeño",
        "image": _logo("fadcom", "2025-05/logo_dpro_218x160_wepg.webp?itok=VKhuOhJ6"),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/clubdpro/"},
        ],
        "sources": [_FADCOM_GROUPS],
    },
    {
        "acronym": "BREIK",
        "name": "BREIK — Club de Cobertura y Comunicación Audiovisual",
        "description": (
            "La principal función del club es la cobertura de eventos, donde "
            "todo se plasma en fotografías y cápsulas audiovisuales. Asimismo, "
            "se imparten talleres de fotografía, edición y se realizan "
            "concursos de fotografía."
        ),
        "category": "Culturales",
        "faculty": "FADCOM",
        "location": "FADCOM, Campus Gustavo Galindo",
        "areas": ["Arte", "Cultura"],
        "size": "pequeño",
        "image": _logo(
            "fadcom", "2023-08/logo%20club%20breik%20218x160.webp?itok=35ckW1KM"
        ),
        "social_media": [
            {"network": "Instagram", "link": "https://www.instagram.com/breikgye/"},
        ],
        "sources": [_FADCOM_GROUPS],
    },
    {
        "acronym": "SNAME",
        "name": "SNAME",
        "description": (
            "Su misión es avanzar en el arte, la ciencia y la práctica de la "
            "Arquitectura Naval, Ingeniería Naval, Ingeniería Oceánica y otras "
            "profesiones relacionadas con el mar."
        ),
        "category": "Profesionales",
        "faculty": "FIMCM",
        "location": "FIMCM, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Tecnología"],
        "size": "pequeño",
        "image": _logo("fimcm", "2023-08/logo%20FIMCM%20-%20SNAME.webp?itok=YAwySz24"),
        # La FIMCM no publica enlaces propios del club.
        "social_media": [],
        "sources": [_FIMCM_GROUPS],
    },
    {
        "acronym": "OKEANOS",
        "name": "Okeanos",
        "description": (
            "Club de desarrollo investigativo y planteamiento de proyectos "
            "oceanográficos/ambientales de la ESPOL"
        ),
        "category": "Profesionales",
        "faculty": "FIMCM",
        "location": "FIMCM, Campus Gustavo Galindo",
        "areas": ["Ciencia", "Académico"],
        "size": "pequeño",
        "image": _logo(
            "fimcm", "2023-08/logo%20FIMCM%20-%20Okeanos_400x400.webp?itok=vrabr_pI"
        ),
        "social_media": [],
        "sources": [_FIMCM_GROUPS],
    },
    # -- Publicado por la Unidad de Sostenibilidad -------------------------
    {
        "acronym": "CDS",
        "name": "Club de Desarrollo Sostenible",
        "description": (
            "El Club de Desarrollo Sostenible se constituye formalmente en 2020 "
            "con la visión de ser un referente en la promoción de los ODS en la "
            "comunidad ESPOL. A través de proyectos, visitas técnicas, "
            "capacitaciones, acciones de voluntariado en centros y áreas de "
            "conservación, entre otras actividades, el club fomenta una cultura "
            "de sostenibilidad activa y participativa."
        ),
        "category": "Competencias transversales",
        "faculty": None,
        "location": "Campus Gustavo Galindo",
        "areas": ["Social", "Ciencia"],
        "size": "mediano",
        # Sin logo: la página de Sostenibilidad no publica uno identificable.
        "image": "",
        "social_media": [
            {"network": "Sitio ESPOL", "link": "http://cds.oe.espol.edu.ec/"},
            {"network": "Instagram", "link": "https://www.instagram.com/cds_espol/"},
        ],
        "sources": [_SOSTENIBILIDAD, _I3LAB],
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
            {"network": "Instagram", "link": "https://www.instagram.com/acp_club"},
        ],
        "sources": [_PORTAL, _I3LAB],
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
    "PHYCOM": ["Arduino creativo", "electrónica interactiva", "robótica educativa"],
    "IEEE": ["redacción de artículos científicos", "IoT aplicado", "liderazgo IEEE"],
    "SPE": ["ingeniería de yacimientos", "perforación de pozos", "producción petrolera"],
    "ACI": ["diseño de mezclas de hormigón", "ensayos de materiales", "cemento"],
    "SME": ["operaciones mineras", "exploración geológica", "seguridad minera"],
    "IAHR": ["modelación hidráulica", "gestión de recursos hídricos", "hidrología"],
    "ASHRAE": ["climatización eficiente", "refrigeración industrial", "ventilación"],
    "AWS": ["soldadura por arco", "inspección de soldaduras", "metalurgia"],
    "CIMAT": ["caracterización de materiales", "polímeros", "corrosión"],
    "MAEC": ["motores de combustión", "diagnóstico automotriz", "vehículos eléctricos"],
    "RAS": ["ROS para principiantes", "control de robots", "visión artificial"],
    "ROBOTA": ["robots de competición", "seguidores de línea", "sumo robótico"],
    "AICHE": ["simulación de procesos", "termodinámica química", "seguridad industrial"],
    "D.A.T.A": ["R para análisis de datos", "estadística aplicada", "visualización"],
    "MATES": ["olimpiadas de matemática", "cálculo avanzado", "teoría de números"],
    "ALUCINE": ["cine latinoamericano", "crítica cinematográfica", "cortometrajes"],
    "D-PRO": ["prototipado rápido", "diseño industrial", "modelado 3D"],
    "BREIK": ["fotografía de eventos", "edición de video", "cobertura audiovisual"],
    "SNAME": ["diseño de embarcaciones", "hidrodinámica naval", "estructuras navales"],
    "OKEANOS": ["oceanografía", "monitoreo costero", "conservación marina"],
    "CDS": ["Objetivos de Desarrollo Sostenible", "compostaje", "voluntariado ambiental"],
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
    # https://www.fict.espol.edu.ec/es/noticias/ecuamining-2026-reunio-en-salinas-mas-de-120-participantes-del-sector-minero-y-geologico-y
    # Lo organiza SME-ESPOL con la Carrera de Minas; IAHR y AAPG figuran como
    # coorganizadores. La página escribe "CUAMINEING"; el nombre va como el
    # del titular de la noticia.
    "SME": [
        {
            "event_name": "ECUAMINING 2026 — Congreso Universitario de Minería y Geología",
            "date": datetime.date(2026, 10, 17),
            "end_date": datetime.date(2026, 10, 18),
            "mode": "In-person",
            "planned_place": "Hotel Colón Salinas, Santa Elena",
            "description": (
                "La 8.ª edición del congreso, organizada por el Capítulo "
                "Estudiantil SME-ESPOL y la Carrera de Minas de ESPOL."
            ),
        },
    ],
    "IAHR": [
        {
            "event_name": "ECUAMINING 2026 — Congreso Universitario de Minería y Geología",
            "date": datetime.date(2026, 10, 17),
            "end_date": datetime.date(2026, 10, 18),
            "mode": "In-person",
            "planned_place": "Hotel Colón Salinas, Santa Elena",
            "description": "IAHR-ESPOL figura entre los coorganizadores del congreso.",
        },
    ],
    "AAPG": [
        {
            "event_name": "ECUAMINING 2026 — Congreso Universitario de Minería y Geología",
            "date": datetime.date(2026, 10, 17),
            "end_date": datetime.date(2026, 10, 18),
            "mode": "In-person",
            "planned_place": "Hotel Colón Salinas, Santa Elena",
            "description": (
                "AAPG ESPOL Student Chapter figura entre los coorganizadores del "
                "congreso."
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
