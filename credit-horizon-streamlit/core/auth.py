"""Authentification (bcrypt) et matrice des permissions par rôle (séparation des tâches, contrôle C03)."""
import bcrypt

ROLES = {
    "admin": "Administrateur",
    "directeur": "Directeur",
    "analyste": "Analyste risques",
    "commercial": "Commercial",
    "controleur": "Contrôleur interne",
}

PERMISSIONS = {
    "risks.write": ["admin", "analyste"],
    "controls.write": ["admin", "controleur"],
    "coso.write": ["admin", "controleur"],
    "actions.write": ["admin", "directeur", "analyste", "controleur"],
    "recommendations.write": ["admin", "analyste", "controleur"],
    "anomalies.create": ["admin", "directeur", "analyste", "commercial", "controleur"],
    "anomalies.write": ["admin", "directeur", "analyste", "controleur"],
    "dossiers.write": ["admin", "analyste", "commercial"],
    "users.manage": ["admin"],
    "audit.view": ["admin", "directeur", "controleur"],
    "demo.reset": ["admin"],
}

PERMISSION_LABELS = {
    "risks.write": "Modifier le registre des risques",
    "controls.write": "Gérer les fiches de contrôle",
    "coso.write": "Mettre à jour le diagnostic COSO",
    "actions.write": "Piloter le plan d'action",
    "recommendations.write": "Gérer les recommandations",
    "anomalies.create": "Déclarer une anomalie",
    "anomalies.write": "Traiter / clôturer une anomalie",
    "dossiers.write": "Saisir les dossiers TPE",
    "users.manage": "Gérer les utilisateurs",
    "audit.view": "Consulter le journal d'audit",
    "demo.reset": "Réinitialiser les données",
}


def hash_password(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt(rounds=10)).decode()


def check_password(pwd: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pwd.encode(), hashed.encode())
    except ValueError:
        return False


def can(role: str | None, perm: str) -> bool:
    return bool(role) and role in PERMISSIONS.get(perm, [])
