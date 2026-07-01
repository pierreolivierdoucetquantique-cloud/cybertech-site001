"""
Logique de la barre de progression du projet (visible côté client,
contrôlée par un curseur côté admin).

Étapes (cahier des charges) :
  0%   = Projet reçu
  20%  = Analyse
  40%  = Développement
  60%  = Intégration
  80%  = Vérifications
  100% = Projet terminé

Couleurs :
  0-30%   = rouge
  31-70%  = jaune
  71-100% = vert
"""

_STEPS = [
    (0, "Projet reçu"),
    (20, "Analyse"),
    (40, "Développement"),
    (60, "Intégration"),
    (80, "Vérifications"),
    (100, "Projet terminé"),
]


def step_label_for(progress: int) -> str:
    """Retourne le libellé de l'étape la plus proche (par défaut, sans dépasser)."""
    progress = max(0, min(100, progress))
    label = _STEPS[0][1]
    for threshold, name in _STEPS:
        if progress >= threshold:
            label = name
        else:
            break
    return label


def color_for(progress: int) -> str:
    progress = max(0, min(100, progress))
    if progress <= 30:
        return "red"
    if progress <= 70:
        return "yellow"
    return "green"
