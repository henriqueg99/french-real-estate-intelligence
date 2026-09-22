from pathlib import Path

import requests


# Paramètres généraux
ANNEES = range(2021, 2026)
DEPARTEMENT = "69"

URL_BASE = "https://files.data.gouv.fr/geo-dvf/latest/csv"

RACINE_PROJET = Path(__file__).resolve().parents[2]
DOSSIER_DVF = RACINE_PROJET / "data" / "raw" / "dvf"


def construire_url(annee: int, departement: str) -> str:
    """Construit l'URL d'un fichier DVF départemental."""

    return (
        f"{URL_BASE}/{annee}/departements/"
        f"{departement}.csv.gz"
    )


def construire_chemin_sortie(
    annee: int,
    departement: str,
) -> Path:
    """Construit le chemin local du fichier à télécharger."""

    return (
        DOSSIER_DVF
        / str(annee)
        / f"{departement}.csv.gz"
    )


def telecharger_fichier(
    url: str,
    chemin_sortie: Path,
) -> None:
    """
    Télécharge un fichier depuis une URL.

    Le téléchargement est ignoré si le fichier existe déjà.
    Un fichier temporaire est utilisé pour éviter de conserver
    un fichier final incomplet en cas d'interruption.
    """

    chemin_sortie.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        chemin_sortie.exists()
        and chemin_sortie.stat().st_size > 0
    ):
        print(f"Fichier déjà présent : {chemin_sortie}")
        return

    chemin_temporaire = chemin_sortie.with_suffix(
        chemin_sortie.suffix + ".part"
    )

    taille_telechargee = 0

    print(f"Téléchargement depuis : {url}")

    with requests.get(
        url,
        stream=True,
        timeout=120,
    ) as reponse:
        reponse.raise_for_status()

        with chemin_temporaire.open("wb") as fichier:
            for bloc in reponse.iter_content(
                chunk_size=1024 * 1024
            ):
                if bloc:
                    fichier.write(bloc)
                    taille_telechargee += len(bloc)

    chemin_temporaire.replace(chemin_sortie)

    taille_mo = taille_telechargee / (1024**2)

    print(f"Fichier enregistré : {chemin_sortie}")
    print(f"Taille : {taille_mo:.2f} Mo")


def telecharger_toutes_les_annees() -> None:
    """Télécharge les fichiers DVF pour toutes les années."""

    for annee in ANNEES:
        print(f"\n--- Année {annee} ---")

        url = construire_url(
            annee,
            DEPARTEMENT,
        )

        chemin_sortie = construire_chemin_sortie(
            annee,
            DEPARTEMENT,
        )

        telecharger_fichier(
            url,
            chemin_sortie,
        )


if __name__ == "__main__":
    telecharger_toutes_les_annees()