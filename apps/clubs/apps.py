from django.apps import AppConfig


class ClubsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clubs"
    label = "clubs"
    verbose_name = "Clubes"

    def ready(self):
        # Importar el módulo registra sus suscripciones en el bus de eventos.
        from apps.clubs import handlers  # noqa: F401
        from core.services import register_constraint_message

        register_constraint_message(
            "uniq_active_leadership_per_student",
            "Ese estudiante ya lidera otro club. Un líder administra un solo "
            "club a la vez (RN-1).",
            code="leadership_exclusivity",
        )
        register_constraint_message(
            "uniq_membership_per_pao",
            "El estudiante ya tiene una membresía en este club para ese período.",
            code="duplicate_membership",
        )
        register_constraint_message(
            "uniq_role_per_club",
            "Ya existe un rol con ese nombre en el club.",
            code="duplicate_role_name",
        )
        register_constraint_message(
            "chk_club_status_matches_leader",
            "El estado del club no concuerda con su liderazgo: un club activo "
            "debe tener líder y uno sin líder queda en solo lectura.",
            code="club_status_leader_mismatch",
        )
