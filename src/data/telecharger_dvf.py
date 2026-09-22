from pathlib import Path

import requests


# Paramètres du téléchargement
ANNEE = 2025
DEPARTEMENT = "69"

URL_BASE = "https://files.data.gouv.fr/geo-dvf/latest/csv"
URL_TELECHARGEMENT = (
    f"{URL_BASE}/{ANNEE}/departements/{DEPARTEMENT}.csv.gz"
)

# Construction du chemin de destination
RACINE_PROJET = Path(__file__).resolve().parents[2]
CHEMIN_SORTIE = (
    RACINE_PROJET
    / "data"
    / "raw"
    / "dvf"
    / str(ANNEE)
    / f"{DEPARTEMENT}.csv.gz"
)


def telecharger_fichier(url: str, chemin_sortie: Path) -> None:
    """
    Télécharge un fichier depuis une URL et l'enregistre localement.

    Si le fichier existe déjà, le téléchargement n'est pas relancé.
    """

    chemin_sortie.parent.mkdir(parents=True, exist_ok=True)

    if chemin_sortie.exists():
        print(f"Le fichier existe déjà : {chemin_sortie}")
        return

    taille_telechargee = 0

    print(f"Téléchargement depuis : {url}")

    with requests.get(url, stream=True, timeout=60) as reponse:
        reponse.raise_for_status()

        with chemin_sortie.open("wb") as fichier:
            for bloc in reponse.iter_content(chunk_size=1024 * 1024):
                if bloc:
                    fichier.write(bloc)
                    taille_telechargee += len(bloc)

    taille_mo = taille_telechargee / (1024**2)

    print(f"Téléchargement terminé : {chemin_sortie}")
    print(f"Taille du fichier : {taille_mo:.2f} Mo")


if __name__ == "__main__":
    telecharger_fichier(URL_TELECHARGEMENT, CHEMIN_SORTIE)