import streamlit as st
import matplotlib.pyplot as plt 
import pandas as pd
import glob
import os

st.title("Suivi du temps - Analyse")

# Load all CSV files in the current directory
csv_files = glob.glob(os.path.join(os.getcwd(), "data/TogglTrack_Report_Detailed_report_*.csv"))
dfs = []
for file in csv_files:
    df = pd.read_csv(file)
    dfs.append(df)
if not dfs:
    st.warning("Aucun fichier CSV trouvé dans le dossier.")
    st.stop()

# Concatenate all data
data = pd.concat(dfs, ignore_index=True)

# Parse date column
data['date'] = pd.to_datetime(data['Start date'], format='%Y-%m-%d', errors='coerce')

def duration_to_hours(duration_str):
    """Convertit une durée 'H:MM:SS' en heures décimales."""
    h, m, s = map(int, duration_str.split(':'))
    return h + m/60 + s/3600

data['time'] = data['Duration'].apply(duration_to_hours)
data['month'] = data['date'].dt.to_period('M').astype(str)
data.to_excel("bilan_global.xlsx", index=False)

# Time per month
time_per_month = data.groupby('month')['time'].sum().reset_index()
st.subheader("Temps total par mois")
st.bar_chart(time_per_month.set_index('month'))


# Time per project ratio
time_per_project = data.groupby('Project')['time'].sum()
st.subheader("Répartition du temps par projet")
fig, ax = plt.subplots()
time_per_project.plot.pie(autopct='%1.1f%%', ylabel='', ax=ax)
st.pyplot(fig)

# Section pour définir les types de projets
st.subheader("Catégorisation des projets")

all_projects = sorted(data['Project'].unique())
ome_projects = st.multiselect("Sélectionnez les projets OME :", all_projects)
cm_projects = st.multiselect("Sélectionnez les projets Climat Médias :", [p for p in all_projects if p not in ome_projects])

# Attribution du type de projet
def get_type(proj):
    if proj in ome_projects:
        return "OME"
    elif proj in cm_projects:
        return "CM"
    else:
        return "Autre"

data['type_projet'] = data['Project'].apply(get_type)

# Heures mensuelles par type de projet
monthly_type = data.groupby([data['month'], 'type_projet'])['time'].sum().unstack(fill_value=0)
st.subheader("Heures mensuelles par type de projet")
st.bar_chart(monthly_type)

# Ratio OME/CM par mois
st.subheader("Ratio OME/CM par mois")
if "OME" in monthly_type.columns and "CM" in monthly_type.columns:
    ratio_monthly = (monthly_type["OME"] / (monthly_type["CM"] + 1e-9)).rename("OME/CM")
    st.line_chart(ratio_monthly)
else:
    st.info("Sélectionnez au moins un projet OME et un projet CM pour voir le ratio.")

# Ratio OME/CM total
total_ome = data.loc[data['type_projet'] == "OME", 'time'].sum()
total_cm = data.loc[data['type_projet'] == "CM", 'time'].sum()
st.subheader("Ratio OME/CM total")
if total_cm > 0:
    st.metric("OME/CM total", f"{total_ome / total_cm:.2f}")
else:
    st.info("Pas d'heures pour les projets CM.")


# Show raw data if needed
if st.checkbox("Afficher les données brutes"):
    st.write(data)