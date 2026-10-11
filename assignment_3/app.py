from pathlib import Path
import unicodedata

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="Emergencies and rainfall 2023", layout="wide")

# Paths relative to this file, so it works on any computer and on Streamlit Cloud
RUTA = Path(__file__).parent / "datos" / "tabla_final.csv"
RUTA_MAPA = Path(__file__).parent / "datos" / "departamentos_peru.geojson"

FUENTE = "Source: PCM emergency decrees (gob.pe) and Open-Meteo, Jan-May 2023. Own elaboration."


@st.cache_data
def cargar_datos(ruta):
    df = pd.read_csv(ruta, encoding="utf-8-sig", dtype={"ubigeo": str})
    df["ubigeo"] = df["ubigeo"].str.zfill(2)
    return df


def normalizar(nombre):
    """Capital letters and no accent marks: the GeoJSON writes 'ANCASH', the table 'Áncash'."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", str(nombre))
                         if unicodedata.category(c) != "Mn")
    return sin_tildes.upper()


@st.cache_data
def cargar_mapa(ruta, tabla):
    """Department boundaries joined with the table by ubigeo, as in Part 2.

    The GeoJSON has no ubigeo, so the names are normalized only to assign it. From
    there on the join uses the ubigeo, read as text.
    """
    mapa = gpd.read_file(ruta).rename(columns={"departamento": "nombre_geojson"})
    ubigeo_por_nombre = dict(zip(tabla["departamento"].map(normalizar), tabla["ubigeo"]))
    mapa["ubigeo"] = mapa["nombre_geojson"].map(normalizar).map(ubigeo_por_nombre)
    # Lighter shapes (about 1 km of tolerance) so the map loads fast in the cloud
    mapa["geometry"] = mapa.geometry.simplify(0.01, preserve_topology=True)
    return (mapa[["ubigeo", "geometry"]]
            .dropna(subset=["ubigeo"])
            .merge(tabla, on="ubigeo", how="inner", validate="one_to_one"))


def lista(nombres):
    """'Lima', 'Lima and Loreto', 'Lima, Loreto and Piura'."""
    nombres = list(nombres)
    if len(nombres) == 1:
        return nombres[0]
    return ", ".join(nombres[:-1]) + " and " + nombres[-1]


def estilo(fig, titulo, alto):
    """Same look as the charts of Part 1: conclusion title and source note."""
    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b>", font_size=18),
        template="plotly_white",
        font=dict(family="Arial", size=13),
        height=alto,
        margin=dict(l=10, r=40, t=70, b=110),
        annotations=[dict(
            text=FUENTE, showarrow=False, xref="paper", yref="paper",
            x=0, y=0, yshift=-80, yanchor="top", font=dict(size=11, color="gray"),
        )],
    )
    return fig


tabla = cargar_datos(RUTA)
mapa_datos = cargar_mapa(RUTA_MAPA, tabla)

st.title("Does the State declare emergencies where it rains the most?")
st.caption("Departments of Peru, January to May 2023. Use the filters in the sidebar: "
           "the metrics, charts, map and table all follow them.")

st.sidebar.header("Filters")

departamentos = st.sidebar.multiselect(
    "Department",
    options=sorted(tabla["departamento"].unique()),
    default=sorted(tabla["departamento"].unique()),
)

rango_decl = st.sidebar.slider(
    "Emergency declarations",
    int(tabla["declaratorias"].min()), int(tabla["declaratorias"].max()),
    (int(tabla["declaratorias"].min()), int(tabla["declaratorias"].max())),
)

df_filtrado = tabla[
    tabla["departamento"].isin(departamentos)
    & tabla["declaratorias"].between(*rango_decl)
]

if df_filtrado.empty:
    st.warning("No department matches the filters.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Departments", len(df_filtrado))
col2.metric("Total declarations", int(df_filtrado["declaratorias"].sum()))
col3.metric("Average rainfall (mm)", f"{df_filtrado['lluvia_total_mm'].mean():,.1f}")
col4.metric("Avg. days of heavy rain", f"{df_filtrado['dias_lluvia_fuerte'].mean():.1f}")

st.subheader("Charts")
tab_barras, tab_dispersion, tab_hist = st.tabs(
    ["Declarations by department", "Rainfall vs declarations", "Rainfall distribution"]
)

with tab_barras:
    maximo = int(df_filtrado["declaratorias"].max())
    lideres = df_filtrado.loc[df_filtrado["declaratorias"] == maximo, "departamento"].tolist()
    if maximo == 0:
        titulo = "None of the selected departments received an emergency declaration"
    elif len(lideres) > 3:
        titulo = f"{len(lideres)} departments tied for the most emergency declarations ({maximo} each)"
    else:
        titulo = f"{lista(lideres)} had the most emergency declarations ({maximo})"

    fig = px.bar(df_filtrado.sort_values("declaratorias"),
                 x="declaratorias", y="departamento", orientation="h",
                 color="declaratorias", color_continuous_scale="Blues",
                 range_color=(0, int(tabla["declaratorias"].max())),
                 text="declaratorias",
                 labels={"declaratorias": "Emergency declarations", "departamento": "Department"})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(coloraxis_showscale=False, bargap=0.25, xaxis=dict(showgrid=False),
                      yaxis=dict(ticksuffix="  "))
    st.plotly_chart(estilo(fig, titulo, max(420, 24 * len(df_filtrado) + 190)), width="stretch")

with tab_dispersion:
    columnas = ["lluvia_total_mm", "declaratorias"]
    if len(df_filtrado) < 3 or df_filtrado[columnas].nunique().min() < 2:
        st.info("Select at least 3 departments with different values to compare "
                "rainfall and declarations.")
    else:
        r = df_filtrado["lluvia_total_mm"].corr(df_filtrado["declaratorias"])
        if r >= 0.5:
            titulo = f"Departments with more rain received more declarations (r = {r:.2f})"
        elif r >= 0.3:
            titulo = f"Rainfall and declarations moved together only weakly (r = {r:.2f})"
        elif r > -0.3:
            titulo = f"More rain did not mean more emergency declarations (r = {r:.2f})"
        else:
            titulo = f"Departments with more rain received fewer declarations (r = {r:.2f})"

        fig = px.scatter(df_filtrado, x="lluvia_total_mm", y="declaratorias",
                         hover_name="departamento",
                         text="departamento" if len(df_filtrado) <= 12 else None,
                         color="dias_lluvia_fuerte", color_continuous_scale="Blues",
                         range_color=(0, int(tabla["dias_lluvia_fuerte"].max())),
                         labels={"lluvia_total_mm": "Total rainfall (mm)",
                                 "declaratorias": "Emergency declarations",
                                 "dias_lluvia_fuerte": "Days with<br>20+ mm"})
        fig.update_traces(textposition="top center", textfont_size=10,
                          marker=dict(size=12, line=dict(width=1, color="gray")))
        st.plotly_chart(estilo(fig, titulo, 560), width="stretch")

with tab_hist:
    n = len(df_filtrado)
    pocos = int((df_filtrado["lluvia_total_mm"] < 200).sum())
    muchos = int((df_filtrado["lluvia_total_mm"] > 1000).sum())
    sufijo = "department" if n == 1 else "departments"
    titulo = (f"{pocos} of {n} selected {sufijo} got less than 200 mm of rain, "
              f"while {muchos} got more than 1,000 mm")

    fig = px.histogram(df_filtrado, x="lluvia_total_mm", text_auto=True,
                       color_discrete_sequence=["#2171b5"],
                       labels={"lluvia_total_mm": "Total rainfall (mm)"})
    fig.update_traces(xbins=dict(start=0, end=1800, size=200),
                      marker_line=dict(width=1, color="white"),
                      textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis_title="Number of departments", bargap=0.05,
                      xaxis=dict(dtick=200), yaxis=dict(showgrid=False))
    st.plotly_chart(estilo(fig, titulo, 480), width="stretch")

st.subheader("Map")
variable = st.radio("Color the map by", ["Total rainfall", "Emergency declarations"],
                    horizontal=True)
columna, paleta, leyenda = {
    "Total rainfall": ("lluvia_total_mm", "Blues", "Total rainfall, January to May 2023 (mm)"),
    "Emergency declarations": ("declaratorias", "Oranges", "Emergency declarations, January to May 2023"),
}[variable]

# Quantile classes of the whole table, so the colors keep their meaning when filtering
cortes = sorted(set(tabla[columna].quantile([0, 0.2, 0.4, 0.6, 0.8, 1]).tolist()))
seleccion = mapa_datos[mapa_datos["ubigeo"].isin(df_filtrado["ubigeo"])][
    ["ubigeo", "departamento", "declaratorias", "lluvia_total_mm", "geometry"]]

mapa = folium.Map(location=[-9.2, -75], zoom_start=5, tiles="Esri.WorldGrayCanvas")
# Frame the selected departments, so the map zooms in when the filters narrow the view
minx, miny, maxx, maxy = seleccion.total_bounds
mapa.fit_bounds([[miny, minx], [maxy, maxx]], max_zoom=8)
# Departments left out by the filters stay on the map in gray
folium.GeoJson(
    mapa_datos[["geometry"]],
    style_function=lambda _: {"fillColor": "#e6e6e6", "color": "white", "weight": 1,
                              "fillOpacity": 0.7},
).add_to(mapa)
coropleta = folium.Choropleth(
    geo_data=seleccion,
    data=df_filtrado,
    columns=["ubigeo", columna],
    key_on="feature.properties.ubigeo",
    bins=cortes,
    fill_color=paleta,
    fill_opacity=0.85,
    line_color="white",
    line_weight=1,
    highlight=True,
    legend_name=leyenda,
).add_to(mapa)
folium.GeoJsonTooltip(
    fields=["departamento", "declaratorias", "lluvia_total_mm"],
    aliases=["Department:", "Emergency declarations:", "Total rainfall (mm):"],
    localize=True,
).add_to(coropleta.geojson)

# returned_objects=[] so moving or zooming the map does not rerun the whole app
st_folium(mapa, height=520, use_container_width=True, returned_objects=[])

sin_mapa = tabla.loc[~tabla["ubigeo"].isin(mapa_datos["ubigeo"]), "departamento"].tolist()
if sin_mapa:
    st.warning(f"Departments without a boundary on the map: {', '.join(sin_mapa)}")
else:
    st.caption(f"Join by ubigeo (read as text): all {len(mapa_datos)} departments matched "
               "their boundary. Gray departments are left out by the filters.")

st.subheader("Filtered data")
st.dataframe(df_filtrado, width="stretch", hide_index=True)

st.download_button(
    label="Download filtered data (CSV)",
    data=df_filtrado.to_csv(index=False).encode("utf-8-sig"),
    file_name="filtered_data.csv",
    mime="text/csv",
)

st.caption(FUENTE)
