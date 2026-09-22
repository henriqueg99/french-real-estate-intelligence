from pathlib import Path

import duckdb


RACINE_PROJET = Path(__file__).resolve().parents[2]

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

CHEMIN_BASE = (
    DOSSIER_TRAITE
    / "immobilier.duckdb"
)


def convertir_chemin_sql(chemin: Path) -> str:
    """
    Convertit un chemin Windows en chemin utilisable dans SQL.
    """

    return (
        chemin.resolve()
        .as_posix()
        .replace("'", "''")
    )


def verifier_fichiers() -> None:
    """Vérifie que les fichiers Parquet existent."""

    fichiers_requis = [
        CHEMIN_TRANSACTIONS,
        CHEMIN_TRANSACTIONS_SIGNALEES,
    ]

    for chemin in fichiers_requis:
        if not chemin.exists():
            raise FileNotFoundError(
                f"Fichier introuvable : {chemin}\n"
                "Lance d'abord nettoyer_dvf.py."
            )


def creer_tables(
    connexion: duckdb.DuckDBPyConnection,
) -> None:
    """Importe les fichiers Parquet dans DuckDB."""

    chemin_transactions_sql = convertir_chemin_sql(
        CHEMIN_TRANSACTIONS
    )

    chemin_signalees_sql = convertir_chemin_sql(
        CHEMIN_TRANSACTIONS_SIGNALEES
    )

    connexion.execute(
        f"""
        CREATE OR REPLACE TABLE
            transactions_appartements
        AS
        SELECT *
        FROM read_parquet(
            '{chemin_transactions_sql}'
        )
        """
    )

    connexion.execute(
        f"""
        CREATE OR REPLACE TABLE
            transactions_signalees
        AS
        SELECT *
        FROM read_parquet(
            '{chemin_signalees_sql}'
        )
        """
    )


def creer_vues(
    connexion: duckdb.DuckDBPyConnection,
) -> None:
    """Crée des vues SQL pour les analyses récurrentes."""

    connexion.execute(
        """
        CREATE OR REPLACE VIEW
            statistiques_annuelles
        AS
        SELECT
            annee,
            COUNT(*) AS nombre_ventes,
            ROUND(
                MEDIAN(prix_m2),
                2
            ) AS prix_m2_median,
            ROUND(
                AVG(prix_m2),
                2
            ) AS prix_m2_moyen,
            ROUND(
                MEDIAN(surface_reelle_bati),
                1
            ) AS surface_mediane
        FROM transactions_appartements
        GROUP BY annee
        """
    )

    connexion.execute(
        """
        CREATE OR REPLACE VIEW
            statistiques_annuelles_zones
        AS
        SELECT
            annee,
            nom_commune,
            COUNT(*) AS nombre_ventes,
            ROUND(
                MEDIAN(prix_m2),
                2
            ) AS prix_m2_median,
            ROUND(
                AVG(prix_m2),
                2
            ) AS prix_m2_moyen
        FROM transactions_appartements
        GROUP BY
            annee,
            nom_commune
        """
    )

    connexion.execute(
        """
        CREATE OR REPLACE VIEW
            statistiques_mensuelles
        AS
        SELECT
            CAST(
                DATE_TRUNC(
                    'month',
                    date_mutation
                )
                AS DATE
            ) AS mois,
            nom_commune,
            COUNT(*) AS nombre_ventes,
            ROUND(
                MEDIAN(prix_m2),
                2
            ) AS prix_m2_median
        FROM transactions_appartements
        GROUP BY
            CAST(
                DATE_TRUNC(
                    'month',
                    date_mutation
                )
                AS DATE
            ),
            nom_commune
        """
    )


def afficher_bilan(
    connexion: duckdb.DuckDBPyConnection,
) -> None:
    """Affiche un contrôle du contenu de la base."""

    nombre_transactions = connexion.execute(
        """
        SELECT COUNT(*)
        FROM transactions_appartements
        """
    ).fetchone()[0]

    nombre_signalees = connexion.execute(
        """
        SELECT COUNT(*)
        FROM transactions_signalees
        """
    ).fetchone()[0]

    statistiques = connexion.execute(
        """
        SELECT *
        FROM statistiques_annuelles
        ORDER BY annee
        """
    ).fetchdf()

    print(
        f"Transactions principales : "
        f"{nombre_transactions:,}"
    )

    print(
        f"Transactions signalées : "
        f"{nombre_signalees:,}"
    )

    print("\nStatistiques annuelles :")
    print(statistiques.to_string(index=False))


def main() -> None:
    """Crée la base DuckDB et ses vues analytiques."""

    verifier_fichiers()

    DOSSIER_TRAITE.mkdir(
        parents=True,
        exist_ok=True,
    )

    with duckdb.connect(
        str(CHEMIN_BASE)
    ) as connexion:
        creer_tables(connexion)
        creer_vues(connexion)
        afficher_bilan(connexion)

    print(f"\nBase DuckDB créée : {CHEMIN_BASE}")


if __name__ == "__main__":
    main()