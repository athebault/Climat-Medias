import pandas as pd
import folium
import streamlit as st
from folium.features import GeoJsonTooltip
import requests
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import plotly.graph_objects as go

# --- CONFIGURATION STREAMLIT ---
st.set_page_config(page_title="Carte Presse - Diffusion", layout="wide")

# --- CSS PERSONNALISÉ POUR LE SCROLL DU BARPLOT ---
st.markdown("""
    <style>
    .scrollable-plot {
        height: 1000px;
        overflow-y: auto;
        overflow-x: hidden;
    }
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
df_zones = pd.read_csv('data/zones_diffusion.csv', encoding='cp1252', sep=';')
df_dept = pd.read_csv('data/departements_avec_regions.csv', encoding='utf-8-sig', sep=';')
df_diff = pd.read_csv('data/ACPM_list_presse-quotidienne-regionale_20251110.csv', encoding='cp1252', sep=';')

print(df_zones)
print(df_dept)
print(df_diff)

# Formatter les titres 
df_zones['Titre'] = df_zones['Titre'].str.lower().str.strip().str.title()
df_diff['Titre'] = df_diff['Titre'].str.lower().str.strip().str.title()

# Renommer la colonne de diffusion
df_zones = df_zones.rename(columns={'Diffusion quotidienne 2019[52]': 'Diffusion2019'})
df_diff = df_diff.rename(columns={'Diffusion': 'Diffusion2025'})

# Fusionner les données de diffusion
df = pd.merge(df_zones, df_diff[['Titre', 'Diffusion2025']], on='Titre', how='outer')

# Fonction pour extraire les départements
def extraire_departements(zone_str):
    if pd.isna(zone_str):
        return []
    return [d.strip() for d in zone_str.split(',')]

df['departements'] = df['Zone de diffusion'].apply(extraire_departements)

# --- INTERFACE UTILISATEUR ---
st.sidebar.header("📰 Paramètres de la carte")

mode_visualisation = st.sidebar.radio(
    "Mode de visualisation",
    options=["Densité (nombre de titres)", "Zones par titre (couleurs distinctes)"],
    index=0
)

titres = df[["Titre","Diffusion2025"]].dropna().sort_values(by="Diffusion2025", ascending=True)['Titre'].tolist()

if mode_visualisation == "Zones par titre (couleurs distinctes)":
    titres_selectionnes = st.sidebar.multiselect(
        "Choisissez les titres à afficher",
        options=titres,
        default=titres[:5]  # Moins par défaut pour la lisibilité
    )
else:
    titres_selectionnes = st.sidebar.multiselect(
        "Choisissez les titres à inclure",
        options=titres,
        default=titres[:10]
    )

niveau_geo = st.sidebar.radio(
    "Niveau géographique d'affichage",
    options=["Région", "Département"],
    index=0
)

# --- FILTRAGE ---
df_selection = df[df['Titre'].isin(titres_selectionnes)]
print(df_selection)

# --- MAPPING DÉPARTEMENT -> RÉGION ---
dept_nom_vers_region = dict(zip(df_dept['nom'], df_dept['region']))

# --- CHARGEMENT GEOJSON ---
if niveau_geo == "Région":
    geojson_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions.geojson"
elif niveau_geo == "Département":
    geojson_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements.geojson"

geojson_data = requests.get(geojson_url).json()

# --- CRÉATION DE LA CARTE ---
m = folium.Map(location=[46.8, 2.5], zoom_start=6, tiles="CartoDB positron")

if mode_visualisation == "Densité (nombre de titres)":
    # --- MODE DENSITÉ (CHOROPLETH) ---
    zone_to_titles = {}
    
    if not df_selection.empty:
        for _, row in df_selection.iterrows():
            for dept_nom in row['departements']:
                if niveau_geo == "Région":
                    region = dept_nom_vers_region.get(dept_nom)
                    if region:
                        zone_to_titles.setdefault(region, []).append(row['Titre'])
                else:  # Département
                    zone_to_titles.setdefault(dept_nom, []).append(row['Titre'])

    # Construction du DataFrame pour la choropleth
    if zone_to_titles:
        df_map = pd.DataFrame([
            {"nom": zone, "nb_journaux": len(set(titres)), "titres": " • ".join(sorted(set(titres)))}
            for zone, titres in zone_to_titles.items()
        ])
    else:
        # Si aucune sélection, créer un DataFrame vide avec les bonnes colonnes
        df_map = pd.DataFrame(columns=["nom", "nb_journaux", "titres"])

    # Ajout dans GeoJSON
    for feature in geojson_data["features"]:
        nom = feature["properties"]["nom"]
        if not df_map.empty:
            match = df_map[df_map["nom"] == nom]
            if not match.empty:
                feature["properties"]["nb_journaux"] = int(match["nb_journaux"].iloc[0])
                feature["properties"]["titres"] = str(match["titres"].iloc[0])
            else:
                feature["properties"]["nb_journaux"] = 0
                feature["properties"]["titres"] = "Aucun titre sélectionné"
        else:
            # Aucune sélection du tout
            feature["properties"]["nb_journaux"] = 0
            feature["properties"]["titres"] = "Aucun titre sélectionné"

    if not df_map.empty:
        folium.Choropleth(
            geo_data=geojson_data,
            data=df_map,
            columns=["nom", "nb_journaux"],
            key_on="feature.properties.nom",
            fill_color="YlOrRd",
            fill_opacity=0.7,
            line_opacity=0.8,
            legend_name=f"Nombre de journaux ({len(titres_selectionnes)} titres sélectionnés)",
            nan_fill_color="#f0f0f0"
        ).add_to(m)
    else:
        # Carte vide : juste les contours gris
        folium.Choropleth(
            geo_data=geojson_data,
            data=pd.DataFrame({"nom": [], "nb_journaux": []}),
            columns=["nom", "nb_journaux"],
            key_on="feature.properties.nom",
            fill_color="Greys",
            fill_opacity=0.3,
            line_opacity=0.5,
            legend_name="Aucun titre sélectionné",
            nan_fill_color="#f0f0f0"
        ).add_to(m)

    folium.GeoJson(
        geojson_data,
        name="Infos",
        style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
        tooltip=GeoJsonTooltip(
            fields=["nom", "nb_journaux", "titres"],
            aliases=[f"{niveau_geo} :", "Nombre de journaux :", "Titres :"],
            localize=True,
            sticky=True,
            labels=True
        ),
    ).add_to(m)

else:
    # --- MODE ZONES PAR TITRE (COULEURS DISTINCTES) ---
    if not df_selection.empty:
        # Générer une palette de couleurs distinctes
        couleurs_base = list(mcolors.TABLEAU_COLORS.values()) + list(mcolors.CSS4_COLORS.values())
        couleurs_titres = {titre: couleurs_base[i % len(couleurs_base)] 
                           for i, titre in enumerate(titres_selectionnes)}
        
        # Pour chaque titre, créer une couche
        for titre in titres_selectionnes:
            titre_data = df_selection[df_selection['Titre'] == titre].iloc[0]
            titre_dept = titre_data['departements']
            couleur = couleurs_titres[titre]
            groupe = titre_data.get('Groupe', 'Non spécifié')
            
            # Créer un GeoJSON filtré pour ce titre
            geojson_titre = {
                "type": "FeatureCollection",
                "features": []
            }
            
            for feature in geojson_data["features"]:
                nom = feature["properties"]["nom"]
                
                # Vérifier si cette zone est concernée par le titre
                est_concernee = False
                if niveau_geo == "Région":
                    # Vérifier si au moins un département de cette région est dans la liste
                    for dept in titre_dept:
                        if dept_nom_vers_region.get(dept) == nom:
                            est_concernee = True
                            break
                else:  # Département
                    if nom in titre_dept:
                        est_concernee = True
                
                if est_concernee:
                    feature_copy = feature.copy()
                    feature_copy["properties"]["titre"] = titre
                    feature_copy["properties"]["diffusion"] = int(titre_data['Diffusion2025'])
                    feature_copy["properties"]["groupe"] = groupe
                    geojson_titre["features"].append(feature_copy)
            
            # Ajouter la couche pour ce titre
            if geojson_titre["features"]:
                folium.GeoJson(
                    geojson_titre,
                    name=f"{titre} ({groupe})",
                    style_function=lambda x, couleur=couleur: {
                        "fillColor": couleur,
                        "color": "black",
                        "weight": 1,
                        "fillOpacity": 0.6
                    },
                    tooltip=GeoJsonTooltip(
                        fields=["nom", "titre", "groupe", "diffusion"],
                        aliases=[f"{niveau_geo} :", "Titre :", "Groupe :", "Diffusion2025 :"],
                        localize=True,
                        sticky=True,
                        labels=True
                    ),
                ).add_to(m)
        
        # Ajouter un contrôle des couches
        folium.LayerControl().add_to(m)
    else:
        # Aucune sélection : afficher juste les contours en gris
        folium.GeoJson(
            geojson_data,
            name="Contours",
            style_function=lambda x: {
                "fillColor": "#f0f0f0",
                "color": "#999999",
                "weight": 1,
                "fillOpacity": 0.3
            }
        ).add_to(m)

# --- LAYOUT : carte + barplot côte à côte ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📈 Diffusion par titre (tous)")
    
    # Toujours afficher TOUTES les données, pas la sélection
    df_bar = df.dropna(subset=["Diffusion2025"]).sort_values("Diffusion2025", ascending=True)
    
    # Conteneur scrollable avec hauteur fixe
    with st.container(height=800):
        # Hauteur proportionnelle au nombre de titres pour permettre le scroll
        hauteur_plot = len(df_bar) * 25 / 100  # 25 pixels par titre
        fig, ax = plt.subplots(figsize=(5, hauteur_plot))
        
        # Colorer différemment les titres sélectionnés vs non-sélectionnés
        couleurs = ['#4CAF50' if titre in titres_selectionnes else '#E0E0E0' 
                    for titre in df_bar["Titre"]]
        
        ax.barh(df_bar["Titre"], df_bar["Diffusion2025"], color=couleurs)
        ax.set_xlabel("Diffusion quotidienne", fontsize=11)
        ax.set_ylabel("")
        ax.set_title("Diffusion de tous les titres (2025)", fontsize=13, pad=15)
        ax.tick_params(axis='y', labelsize=9)
        ax.tick_params(axis='x', labelsize=6)
        plt.tight_layout()
        
        st.pyplot(fig, use_container_width=True)
        
        st.caption(f"🟢 Vert : titres sélectionnés ({len(titres_selectionnes)}) | ⚪ Gris : non sélectionnés")
    
    # Afficher les groupes si disponibles (en dehors du conteneur scrollable)
    if 'Groupe' in df_zones.columns and not df_selection.empty:
        st.markdown("---")
        st.subheader("📊 Groupes représentés")
        groupes_count = df_selection.groupby('Groupe').agg({
            'Titre': 'count',
            'Diffusion2025': 'sum'
        }).rename(columns={'Titre': 'Nb titres'})
        st.dataframe(groupes_count, use_container_width=True)

with col2:
    st.subheader(f"🗺️ Carte de la presse - niveau {niveau_geo.lower()}")
    if mode_visualisation == "Zones par titre (couleurs distinctes)":
        st.caption("💡 Utilisez le contrôle des couches (coin supérieur droit) pour activer/désactiver les titres")
    st.components.v1.html(m._repr_html_(), height=1000)

# --- JAUGE DE POURCENTAGE ---
total_diffusion = df["Diffusion2025"].sum()
selected_diffusion = df_selection["Diffusion2025"].sum() if not df_selection.empty else 0
pourcentage = (selected_diffusion / total_diffusion) * 100 if total_diffusion > 0 else 0

st.markdown("### 🎯 Diffusion cumulée des titres sélectionnés")

# Créer la jauge avec Plotly
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=pourcentage,
    domain={'x': [0, 1], 'y': [0, 1]},
    title={'text': "% de la diffusion totale", 'font': {'size': 18}},
    number={'suffix': "%", 'font': {'size': 40}},
    delta={'reference': 100, 'increasing': {'color': "green"}},
    gauge={
        'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkgray"},
        'bar': {'color': "#4CAF50"},
        'bgcolor': "white",
        'borderwidth': 2,
        'bordercolor': "gray",
        'steps': [
            {'range': [0, 25], 'color': '#FFE5E5'},
            {'range': [25, 50], 'color': '#FFF4E5'},
            {'range': [50, 75], 'color': '#E8F5E9'},
            {'range': [75, 100], 'color': '#C8E6C9'}
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 90
        }
    }
))

fig_gauge.update_layout(
    height=300,
    margin=dict(l=20, r=20, t=60, b=20),
    paper_bgcolor="white",
    font={'color': "darkgray", 'family': "Arial"}
)

st.plotly_chart(fig_gauge, use_container_width=True)

if not df_selection.empty:
    st.write(f"**{selected_diffusion:,}** exemplaires sur **{total_diffusion:,}** au total")
else:
    st.info("Aucun titre sélectionné - Sélectionnez des titres dans la barre latérale pour commencer")

# --- TABLEAU COMPACT ---
st.write("### 🗞️ Titres sélectionnés")
if not df_selection.empty:
    colonnes_affichage = ["Titre", "Diffusion2025", "Zone de diffusion"]
    if 'Groupe' in df_selection.columns:
        colonnes_affichage.insert(1, "Groupe")

    st.dataframe(
        df_selection[colonnes_affichage]
        .reset_index(drop=True)
        .style.format({"Diffusion2025": "{:,}"})
    )
else:
    st.info("Aucun titre sélectionné. Utilisez la barre latérale pour choisir des titres à afficher.")