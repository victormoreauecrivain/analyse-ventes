# -*- coding: utf-8 -*-
"""
Created on Mon Mar 23 16:13:52 2026

@author: Siegfried
"""

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import unicodedata
from io import StringIO

st.set_page_config(page_title="Analyse de ventes", layout="wide")

mapping_colonnes = {
    "mois": ["mois", "month", "date"],
    "produit": ["produit", "article", "item", "nom"],
    "ventes": ["ventes", "qty", "quantite", "sales"],
    "prix": ["prix", "price", "tarif"]
}

# -----------------------------
# FONCTIONS
# -----------------------------
def normaliser_texte(texte):
    texte = str(texte).strip().lower()
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return texte


def emoji_variation(x):
    if pd.isna(x):
        return "📌 Mois de référence"
    elif x > 0:
        return f"📈 +{x:.2f} %"
    elif x < 0:
        return f"📉 {x:.2f} %"
    else:
        return f"➖ {x:.2f} %"


def analyser_csv(df):
    colonnes_attendues = {"mois", "produit", "ventes", "prix"}
    colonnes_presentes = set(df.columns)

    if not colonnes_attendues.issubset(colonnes_presentes):
        colonnes_manquantes = colonnes_attendues - colonnes_presentes
        raise ValueError(f"Colonnes manquantes dans le CSV : {sorted(colonnes_manquantes)}")

    mapping_mois = {
        "janvier": "Janvier",
        "janv": "Janvier",
        "fevrier": "Février",
        "fev": "Février",
        "mars": "Mars",
        "avril": "Avril",
        "avr": "Avril",
        "mai": "Mai",
        "juin": "Juin",
        "juillet": "Juillet",
        "juil": "Juillet",
        "aout": "Août",
        "septembre": "Septembre",
        "sept": "Septembre",
        "octobre": "Octobre",
        "oct": "Octobre",
        "novembre": "Novembre",
        "nov": "Novembre",
        "decembre": "Décembre",
        "dec": "Décembre",
    }

    ordre_mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    df = df.copy()

    df["mois_normalise"] = df["mois"].apply(normaliser_texte)

    mois_inconnus = sorted(set(df["mois_normalise"]) - set(mapping_mois.keys()))
    if mois_inconnus:
        raise ValueError(
            f"Mois non reconnus dans le CSV : {mois_inconnus}. "
            "Corrige-les ou ajoute-les au mapping."
        )

    df["mois_affiche"] = df["mois_normalise"].map(mapping_mois)

    df["ventes"] = pd.to_numeric(df["ventes"], errors="coerce")
    df["prix"] = pd.to_numeric(df["prix"], errors="coerce")

    df = df.dropna(subset=["ventes", "prix", "mois_affiche", "produit"])

    if df.empty:
        raise ValueError("Aucune ligne exploitable après nettoyage des données.")

    df["mois_affiche"] = pd.Categorical(
        df["mois_affiche"],
        categories=ordre_mois,
        ordered=True
    )

    df["revenu"] = df["ventes"] * df["prix"]

    total_revenu = df["revenu"].sum()
    moyenne_ventes = df["ventes"].mean()

    ca_par_produit = df.groupby("produit")["revenu"].sum().round(2)
    ca_par_mois = (
        df.groupby("mois_affiche", observed=True)["revenu"]
        .sum()
        .sort_index()
        .round(2)
    )

    produit_top = ca_par_produit.idxmax()
    mois_top = ca_par_mois.idxmax()

    variation = (ca_par_mois.pct_change() * 100).round(2)
    variation_affichee = variation.apply(emoji_variation)

    variation_sans_ref = variation.dropna()
    if len(variation_sans_ref) == 0:
        reco = "📌 Pas assez de données pour analyser l'évolution"
    else:
        derniere_variation = variation_sans_ref.iloc[-1]
        if derniere_variation > 10:
            reco = "🔥 Forte croissance récente"
        elif derniere_variation < -10:
            reco = "🚨 Forte baisse à analyser"
        elif derniere_variation < 0:
            reco = "⚠️ Légère baisse"
        else:
            reco = "📊 Stable"

    ca_par_produit_str = ca_par_produit.to_string()
    ca_par_mois_str = ca_par_mois.to_string()
    variation_str = variation_affichee.to_string()

    rapport = f"""
=== RAPPORT DE VENTES ===

--- GLOBAL ---
Chiffre d'affaires total : {total_revenu:.2f} €
Ventes moyennes : {moyenne_ventes:.2f}

--- TOP ---
Produit le plus rentable : {produit_top}
Meilleur mois : {mois_top}

--- CA PAR PRODUIT ---
{ca_par_produit_str}

--- CA PAR MOIS ---
{ca_par_mois_str}

--- VARIATION (%) ---
{variation_str}

--- RECOMMANDATION ---
{reco}
""".strip()

    return {
        "df": df,
        "total_revenu": total_revenu,
        "moyenne_ventes": moyenne_ventes,
        "produit_top": produit_top,
        "mois_top": mois_top,
        "ca_par_produit": ca_par_produit,
        "ca_par_mois": ca_par_mois,
        "variation_affichee": variation_affichee,
        "reco": reco,
        "rapport": rapport,
    }


# -----------------------------
# UI
# -----------------------------
st.title("📊 Analyseur de ventes")
st.write("Charge un fichier CSV contenant les colonnes : `mois`, `produit`, `ventes`, `prix`.")

with st.expander("Voir un exemple de CSV"):
    exemple_csv = """mois,produit,ventes,prix
Janvier,Livre A,120,4.99
février,Livre A,150,4.99
Mars,Livre A,170,4.99
Janvier,Livre B,80,3.99
Fevrier,Livre B,90,3.99
Mars,Livre B,110,3.99
"""
    st.code(exemple_csv, language="csv")

uploaded_file = st.file_uploader("Choisis ton fichier CSV", type=["csv"])

if uploaded_file is not None:
    try:
        # essaie plusieurs encodages
        raw_bytes = uploaded_file.read()
        df = None
        last_error = None

        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                text = raw_bytes.decode(encoding)
                df = pd.read_csv(StringIO(text))
                df = renommer_colonnes(df)
                break
            except Exception as e:
                last_error = e

        if df is None:
            raise ValueError(f"Impossible de lire le CSV. Dernière erreur : {last_error}")

        resultats = analyser_csv(df)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("CA total", f"{resultats['total_revenu']:.2f} €")
        col2.metric("Ventes moyennes", f"{resultats['moyenne_ventes']:.2f}")
        col3.metric("Top produit", str(resultats["produit_top"]))
        col4.metric("Top mois", str(resultats["mois_top"]))

        st.subheader("Recommandation")
        st.info(resultats["reco"])

        gauche, droite = st.columns(2)

        with gauche:
            st.subheader("CA par produit")
            st.dataframe(
                resultats["ca_par_produit"].reset_index().rename(
                    columns={"produit": "Produit", "revenu": "CA"}
                ),
                use_container_width=True,
                hide_index=True,
            )

        with droite:
            st.subheader("CA par mois")
            st.dataframe(
                resultats["ca_par_mois"].reset_index().rename(
                    columns={"mois_affiche": "Mois", "revenu": "CA"}
                ),
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Variation mensuelle")
        st.dataframe(
            resultats["variation_affichee"].reset_index().rename(
                columns={"mois_affiche": "Mois", 0: "Variation"}
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Graphique")
        fig, ax = plt.subplots()
        resultats["ca_par_mois"].plot(kind="bar", ax=ax)
        ax.set_title("Chiffre d'affaires par mois")
        ax.set_xlabel("Mois")
        ax.set_ylabel("CA (€)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

        st.subheader("Rapport complet")
        st.text(resultats["rapport"])

        st.download_button(
            label="Télécharger le rapport (.txt)",
            data=resultats["rapport"],
            file_name="rapport_ventes.txt",
            mime="text/plain",
        )

    except Exception as e:
        st.error(f"Erreur : {e}")
