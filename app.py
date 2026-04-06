import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import rasterio
from folium.plugins import HeatMap

st.set_page_config(page_title="Observatoire des feux - Maroc", layout="wide")
st.title("🌍 Détection et suivi des feux de végétation")

# ========== INITIALISATION DE L'ÉTAT ==========
if 'burned_coords' not in st.session_state:
    st.session_state.burned_coords = None
if 'surface_ha' not in st.session_state:
    st.session_state.surface_ha = 0
if 'analyse_faite' not in st.session_state:
    st.session_state.analyse_faite = False

# ========== BARRE LATÉRALE ==========
st.sidebar.header("Paramètres")
zone_options = {
    "Meknès": {"center": [33.8936, -5.5473], "zoom": 11, "bounds": [[33.80, -5.70], [33.98, -5.40]]},
    "Rabat": {"center": [34.0209, -6.8416], "zoom": 11, "bounds": [[33.95, -6.95], [34.10, -6.70]]},
}
zone_choisie = st.sidebar.selectbox("Choisir la zone d'étude", list(zone_options.keys()))
annee = st.sidebar.selectbox("Choisir l'année", [2023, 2024, 2025], index=1)
show_sentinel = st.sidebar.checkbox("Afficher le fond Sentinel-2", value=True)
show_urban = st.sidebar.checkbox("Afficher les zones urbaines", value=True)
show_admin = st.sidebar.checkbox("Afficher la limite administrative", value=True)
analyser = st.sidebar.button("Lancer l'analyse des feux", type="primary")

# ========== CHARGEMENT DES DONNÉES (REAL) ==========
def load_burned_coords_from_tif(tif_path):
    with rasterio.open(tif_path) as src:
        data = src.read(1)
        burned = data == 1
        rows, cols = np.where(burned)
        xs, ys = src.xy(rows, cols)
        return list(zip(ys, xs))   # (lat, lon)

if analyser:
    with st.spinner("Chargement des zones brûlées depuis le GeoTIFF..."):
        try:
            tif_file = "burned_areas (1).tif"   # adaptez le nom
            coords = load_burned_coords_from_tif(tif_file)
            st.session_state.burned_coords = coords
            st.session_state.surface_ha = len(coords) * 100 / 10000
            st.session_state.analyse_faite = True
            st.sidebar.success(f"Analyse terminée : {len(coords)} pixels brûlés.")
        except Exception as e:
            st.sidebar.error(f"Erreur de chargement : {e}")
            st.session_state.burned_coords = None
            st.session_state.analyse_faite = False

# ========== PRÉPARATION DE LA CARTE ==========
center = zone_options[zone_choisie]["center"]
zoom_start = zone_options[zone_choisie]["zoom"]

# Limite administrative (exemple)
admin_polygon = None
if zone_choisie == "Meknès":
    admin_polygon = [
        [33.80, -5.70], [33.85, -5.65], [33.90, -5.60], [33.95, -5.55],
        [33.98, -5.50], [33.95, -5.45], [33.88, -5.48], [33.82, -5.52],
        [33.80, -5.60], [33.80, -5.70]
    ]

urban_points = {
    "Meknès": [[33.8936, -5.5473, "Meknès centre"], [33.880, -5.560, "Hamria"], [33.900, -5.530, "Sidi Baba"]],
    "Rabat": [[34.0209, -6.8416, "Rabat centre"], [34.030, -6.820, "Agdal"]]
}

# Construction de la carte
m = folium.Map(location=center, zoom_start=zoom_start, control_scale=True)
if show_sentinel:
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite',
        name='Sentinel-2 (simulé)',
        overlay=False,
        control=True
    ).add_to(m)
else:
    folium.TileLayer('openstreetmap', name='OSM').add_to(m)

if show_admin and admin_polygon:
    folium.Polygon(locations=admin_polygon, color='blue', weight=3,
                   fill=True, fill_opacity=0.1, popup='Limite administrative').add_to(m)

if show_urban:
    for lat, lon, nom in urban_points.get(zone_choisie, []):
        folium.Marker(location=[lat, lon], popup=nom,
                      icon=folium.Icon(color='red', icon='home', prefix='fa')).add_to(m)

if st.session_state.burned_coords and len(st.session_state.burned_coords) > 0:
    heat_data = [[lat, lon, 1] for lat, lon in st.session_state.burned_coords]
    HeatMap(heat_data, radius=15, blur=10, name='Zones brûlées').add_to(m)
    for lat, lon in st.session_state.burned_coords[:500]:
        folium.CircleMarker(location=[lat, lon], radius=1.5, color='red',
                            fill=True, fill_color='red', fill_opacity=0.8).add_to(m)

folium.LayerControl().add_to(m)

st_folium(m, width=900, height=600)

# ========== STATISTIQUES ==========
st.markdown("---")
st.subheader("📊 Statistiques")
col1, col2, col3 = st.columns(3)
col1.metric("Zone", zone_choisie)
col2.metric("Année", annee)
if st.session_state.analyse_faite:
    col3.metric("Surface brûlée (ha)", f"{st.session_state.surface_ha:.2f}")
else:
    col3.metric("Statut", "Non analysé")

st.caption("Données issues de Google Earth Engine (Sentinel-2). Seuil dNBR > 0.3.")