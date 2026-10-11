from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Emergencias y lluvia 2023", layout="wide")

RUTA = Path(__file__).parent / "datos" / "tabla_final.csv"

@st.cache_data
def cargar_datos(ruta):
    df = pd.read_csv(ruta, encoding="utf-8-sig", dtype={"ubigeo": str})
    df["ubigeo"] = df["ubigeo"].str.zfill(2)
    return df

tabla = cargar_datos(RUTA)

st.title("¿El Estado declara emergencias donde más llueve?")
st.dataframe(tabla)