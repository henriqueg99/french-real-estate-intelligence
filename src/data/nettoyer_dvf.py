from pathlib import Path

import pandas as pd


# Configuration générale
ANNEES = range(2021, 2026)
DEPARTEMENT = "69"

CODES_LYON = {
    str(code)
    for code in range(69381, 69390)
}
CODE_VILLEURBANNE = "69266"

CODES_COMMUNES_CIBLES = CODES_LYON | {
    CODE_VILLEURBANNE
}

SEUIL_PRIX_M2_MIN = 500
SEUIL_PRIX_M2_MAX = 15_000

RACINE_PROJET = Path(__file__).resolve().parents[2]

DOSSIER_DVF = (
    RACINE_PROJET
    / "data"
    / "raw"
    / "dvf"
)

DOSSIER_TRAITE = (
    RACINE_PROJET
    / "data"
    / "processed"
)

CHEMIN_TRANSACTIONS = (
    DOSSIER_TRAITE
    / "transactions_appartements.parquet"
)

CHEMIN_TRANSACTIONS_SIGNALEES = (
    DOSSIER_TRAITE
    / "transactions_signalees.parquet"
)


COLONNES_CARREZ = [
    "lot1_surface_carrez",
    "lot2_surface_carrez",
    "lot3_surface_carrez",
    "lot4_surface_carrez",
    "lot5_surface_carrez",
]


COLONNES_UTILISEES = [
    "id_mutation",
    "date_mutation",
    "nature_mutation",
    "valeur_fonciere",
    "adresse_numero",
    "adresse_suffixe",
    "adresse_nom_voie",
    "code_postal",
    "code_commune",
    "nom_commune",
    "id_parcelle",
    "nombre_lots",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "lot1_surface_carrez",
    "lot2_surface_carrez",
    "lot3_surface_carrez",
    "lot4_surface_carrez",
    "lot5_surface_carrez",
    "surface_terrain",
    "longitude",
    "latitude",
]


def charger_donnees() -> pd.DataFrame:
    """Charge et concatène les fichiers DVF annuels."""

    tables_annuelles = []

    for annee in ANNEES:
        chemin = (
            DOSSIER_DVF
            / str(annee)
            / f"{DEPARTEMENT}.csv.gz"
        )

        if not chemin.exists():
            raise FileNotFoundError(
                f"Fichier introuvable : {chemin}\n"
                "Lance d'abord telecharger_dvf.py."
            )

        print(f"Chargement de l'année {annee}...")

        table_annuelle = pd.read_csv(
            chemin,
            usecols=COLONNES_UTILISEES,
            dtype={
                "id_mutation": "string",
                "code_postal": "string",
                "code_commune": "string",
            },
            parse_dates=["date_mutation"],
            low_memory=False,
        )

        table_annuelle["annee_source"] = annee

        table_annuelle["id_transaction"] = (
            table_annuelle["annee_source"].astype("string")
            + "_"
            + table_annuelle["id_mutation"]
        )

        tables_annuelles.append(table_annuelle)

    donnees = pd.concat(
        tables_annuelles,
        ignore_index=True,
    )

    return donnees


def filtrer_perimetre(
    donnees: pd.DataFrame,
) -> pd.DataFrame:
    """Conserve les ventes de Lyon et Villeurbanne."""

    masque = (
        donnees["code_commune"].isin(
            CODES_COMMUNES_CIBLES
        )
        & donnees["nature_mutation"].eq("Vente")
    )

    return donnees.loc[masque].copy()


def construire_resume_mutations(
    donnees_zone: pd.DataFrame,
) -> pd.DataFrame:
    """Compte les différents types de locaux par mutation."""

    resume = (
        donnees_zone.groupby("id_transaction")
        .agg(
            nombre_lignes=(
                "id_transaction",
                "size",
            ),
            nombre_appartements=(
                "type_local",
                lambda serie: serie.eq(
                    "Appartement"
                ).sum(),
            ),
            nombre_maisons=(
                "type_local",
                lambda serie: serie.eq(
                    "Maison"
                ).sum(),
            ),
            nombre_dependances=(
                "type_local",
                lambda serie: serie.eq(
                    "Dépendance"
                ).sum(),
            ),
            nombre_locaux_activite=(
                "type_local",
                lambda serie: serie.eq(
                    "Local industriel. commercial ou assimilé"
                ).sum(),
            ),
            nombre_lignes_sans_type=(
                "type_local",
                lambda serie: serie.isna().sum(),
            ),
        )
        .reset_index()
    )

    return resume


def nettoyer_appartements(
    donnees_zone: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Construit la table des appartements exploitables.

    Retourne :
    - les transactions utilisées pour la modélisation ;
    - les transactions signalées par les règles ;
    - un bilan du nettoyage.
    """

    resume_mutations = construire_resume_mutations(
        donnees_zone
    )

    appartements = (
        donnees_zone.loc[
            donnees_zone["type_local"].eq(
                "Appartement"
            )
        ]
        .merge(
            resume_mutations,
            on="id_transaction",
            how="left",
            validate="many_to_one",
        )
    )

    appartements_simples = appartements.loc[
        appartements["nombre_appartements"].eq(1)
        & appartements["nombre_maisons"].eq(0)
        & appartements[
            "nombre_locaux_activite"
        ].eq(0)
    ].copy()

    masque_validite = (
        appartements_simples[
            "valeur_fonciere"
        ].notna()
        & appartements_simples[
            "valeur_fonciere"
        ].gt(0)
        & appartements_simples[
            "surface_reelle_bati"
        ].gt(0)
        & appartements_simples[
            "date_mutation"
        ].notna()
        & appartements_simples[
            "longitude"
        ].notna()
        & appartements_simples[
            "latitude"
        ].notna()
    )

    appartements_valides = appartements_simples.loc[
        masque_validite
    ].copy()

    appartements_valides["surface_carrez_totale"] = (
        appartements_valides[COLONNES_CARREZ].sum(
            axis=1,
            min_count=1,
        )
    )

    appartements_valides["prix_m2"] = (
        appartements_valides["valeur_fonciere"]
        / appartements_valides[
            "surface_reelle_bati"
        ]
    )

    appartements_valides["annee"] = (
        appartements_valides[
            "date_mutation"
        ].dt.year
    )

    appartements_valides["mois"] = (
        appartements_valides[
            "date_mutation"
        ].dt.month
    )

    appartements_valides["trimestre"] = (
        appartements_valides[
            "date_mutation"
        ].dt.quarter
    )

    appartements_valides["a_dependance"] = (
        appartements_valides[
            "nombre_dependances"
        ].gt(0)
    )

    appartements_valides["prix_m2_hors_plage"] = ~(
        appartements_valides["prix_m2"].between(
            SEUIL_PRIX_M2_MIN,
            SEUIL_PRIX_M2_MAX,
        )
    )

    appartements_valides["nombre_pieces_invalide"] = (
        appartements_valides[
            "nombre_pieces_principales"
        ].lt(1)
        | appartements_valides[
            "nombre_pieces_principales"
        ].isna()
    )

    masque_exclusion = (
        appartements_valides[
            "prix_m2_hors_plage"
        ]
        | appartements_valides[
            "nombre_pieces_invalide"
        ]
    )

    transactions_signalees = (
        appartements_valides.loc[
            masque_exclusion
        ]
        .sort_values(
            ["date_mutation", "id_transaction"]
        )
        .reset_index(drop=True)
    )

    transactions_modele = (
        appartements_valides.loc[
            ~masque_exclusion
        ]
        .sort_values(
            ["date_mutation", "id_transaction"]
        )
        .reset_index(drop=True)
    )

    assert transactions_modele[
        "id_transaction"
    ].is_unique

    bilan = {
        "lignes_dans_la_zone": len(donnees_zone),
        "lignes_appartements": len(appartements),
        "appartements_simples": len(
            appartements_simples
        ),
        "appartements_valides": len(
            appartements_valides
        ),
        "transactions_signalees": len(
            transactions_signalees
        ),
        "transactions_conservees": len(
            transactions_modele
        ),
    }

    return (
        transactions_modele,
        transactions_signalees,
        bilan,
    )


def sauvegarder_donnees(
    transactions: pd.DataFrame,
    transactions_signalees: pd.DataFrame,
) -> None:
    """Enregistre les tables finales au format Parquet."""

    DOSSIER_TRAITE.mkdir(
        parents=True,
        exist_ok=True,
    )

    transactions.to_parquet(
        CHEMIN_TRANSACTIONS,
        index=False,
    )

    transactions_signalees.to_parquet(
        CHEMIN_TRANSACTIONS_SIGNALEES,
        index=False,
    )

    print(f"\nFichier créé : {CHEMIN_TRANSACTIONS}")
    print(
        "Fichier créé :",
        CHEMIN_TRANSACTIONS_SIGNALEES,
    )


def main() -> None:
    """Exécute l'ensemble du pipeline de nettoyage."""

    donnees = charger_donnees()

    print(
        f"\nNombre total de lignes chargées : "
        f"{len(donnees):,}"
    )

    donnees_zone = filtrer_perimetre(donnees)

    (
        transactions,
        transactions_signalees,
        bilan,
    ) = nettoyer_appartements(donnees_zone)

    sauvegarder_donnees(
        transactions,
        transactions_signalees,
    )

    print("\n--- Bilan du nettoyage ---")

    for indicateur, valeur in bilan.items():
        print(f"{indicateur} : {valeur:,}")

    print("\n--- Transactions par année ---")

    print(
        transactions["annee"]
        .value_counts()
        .sort_index()
    )


if __name__ == "__main__":
    main()