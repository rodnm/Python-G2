from pathlib import Path
import unicodedata

import folium
import geopandas as gpd
import mapclassify
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="Emergencies and rainfall 2023", page_icon="🌧️", layout="wide")

# Paths relative to this file, so it works on any computer and on Streamlit Cloud
RUTA = Path(__file__).parent / "datos" / "tabla_final.csv"
RUTA_MAPA = Path(__file__).parent / "datos" / "departamentos_peru.geojson"
REPO = "https://github.com/rodnm/Python-G2/blob/main/assignment_3"

FUENTE = "Source: PCM emergency decrees (gob.pe) and Open-Meteo, Jan-May 2023. Own elaboration."

# Kanagawa Wave palette (github.com/rebelot/kanagawa.nvim), the same as the theme in
# .streamlit/config.toml. The same color means the same variable on the whole page:
# blues for rainfall, warm tones for emergency declarations.
FONDO = "#1F1F28"        # sumiInk3
GRIS = "#54546D"         # sumiInk6
TEXTO_SUAVE = "#727169"  # fujiGray
AZUL = "#7E9CD8"         # crystalBlue
NARANJA = "#FFA066"      # surimiOrange
OCRE = "#938056"         # boatYellow1
# Five tones from low to high, for the map classes and the color scales
TONOS_LLUVIA = ["#2D4F67", "#658594", "#7E9CD8", "#7FB4CA", "#A3D4D5"]  # waveBlue2 to lightBlue
TONOS_DECL = ["#938056", "#C0A36E", "#DCA561", "#FFA066", "#FF5D62"]    # boatYellow1 to peachRed


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
    """Conclusion title and source note, as in Part 1. Background and fonts come
    from the Streamlit theme."""
    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b>", font_size=18),
        font=dict(size=13),
        height=alto,
        margin=dict(l=10, r=40, t=70, b=110),
        annotations=list(fig.layout.annotations) + [dict(
            text=FUENTE, showarrow=False, xref="paper", yref="paper",
            x=0, y=0, yshift=-80, yanchor="top", font=dict(size=11, color=TEXTO_SUAVE),
        )],
    )
    return fig


@st.cache_data
def clases(tabla, columna):
    """Five quantile classes of the whole table (as in the Part 2 maps), with legend
    labels that show the lowest and highest value inside each class."""
    quantiles = mapclassify.Quantiles(tabla[columna], k=5)
    clase_por_ubigeo = dict(zip(tabla["ubigeo"], quantiles.yb.tolist()))
    etiquetas = []
    for c in range(quantiles.k):
        grupo = tabla.loc[quantiles.yb == c, columna]
        bajo, alto = f"{grupo.min():,.0f}", f"{grupo.max():,.0f}"
        etiquetas.append(bajo if bajo == alto else f"{bajo}–{alto}")
    return clase_por_ubigeo, etiquetas


tabla = cargar_datos(RUTA)
mapa_datos = cargar_mapa(RUTA_MAPA, tabla)
MIN_DECL, MAX_DECL = int(tabla["declaratorias"].min()), int(tabla["declaratorias"].max())

# Filter state lives in session_state, so "Reset filters" can clear it
st.session_state.setdefault("deptos", [])
st.session_state.setdefault("rango", (MIN_DECL, MAX_DECL))


def reiniciar_filtros():
    st.session_state["deptos"] = []
    st.session_state["rango"] = (MIN_DECL, MAX_DECL)


# --- Sidebar ------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    departamentos = st.multiselect(
        "Departments",
        options=sorted(tabla["departamento"].unique()),
        key="deptos",
        placeholder="All departments",
        help="Leave it empty to include all 25 departments.",
    )
    rango_decl = st.slider(
        "Emergency declarations",
        min_value=MIN_DECL, max_value=MAX_DECL,
        key="rango",
        help="Keep only the departments whose number of declarations is in this range.",
    )
    st.button("Reset filters", on_click=reiniciar_filtros, width="stretch")

    st.divider()
    st.subheader("About")
    st.markdown(
        "**Data.** Emergency decrees of the Presidency of the Council of Ministers "
        "(gob.pe) and rainfall from the Open-Meteo historical API, measured at the "
        "capital of each department.\n\n"
        f"**Notebooks.** [Part 1: charts]({REPO}/visualizacion.ipynb) · "
        f"[Part 2: maps]({REPO}/mapas.ipynb)\n\n"
        "**Group 02** · Fundamentos de Python, Diplomado PUCP"
    )

df_filtrado = tabla[
    tabla["departamento"].isin(departamentos or tabla["departamento"])
    & tabla["declaratorias"].between(*rango_decl)
]
filtrado = len(df_filtrado) < len(tabla)

# --- Header and metrics -------------------------------------------------------
st.title("Does the State declare emergencies where it rains the most?")
st.caption("Peru, rainy season from January to May 2023. Each department is compared by "
           "the rain it recorded and the emergency declarations it received. "
           "Every number, chart and map below follows the filters in the sidebar.")

if df_filtrado.empty:
    st.warning("No department matches the filters. Try a wider range of declarations "
               "or press **Reset filters**.")
    st.stop()

lluvia_media = df_filtrado["lluvia_total_mm"].mean()
dias_media = df_filtrado["dias_lluvia_fuerte"].mean()
total_decl = int(df_filtrado["declaratorias"].sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Departments", f"{len(df_filtrado)} of {len(tabla)}", border=True)
col2.metric(
    "Emergency declarations", total_decl,
    delta=f"{total_decl / tabla['declaratorias'].sum():.0%} of the national total" if filtrado else None,
    delta_color="off", delta_arrow="off", border=True,
    help="Department-level declarations. One decree usually covers several departments.",
)
col3.metric(
    "Average rainfall", f"{lluvia_media:,.1f} mm",
    delta=f"{lluvia_media - tabla['lluvia_total_mm'].mean():+,.1f} mm vs. all departments" if filtrado else None,
    delta_color="off", border=True,
    help="Total rainfall from January to May 2023, measured at the department capital.",
)
col4.metric(
    "Avg. days of heavy rain", f"{dias_media:.1f}",
    delta=f"{dias_media - tabla['dias_lluvia_fuerte'].mean():+.1f} vs. all departments" if filtrado else None,
    delta_color="off", border=True,
    help="Days with 20 mm of rain or more.",
)

# --- Charts -------------------------------------------------------------------
with st.container(border=True):
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

        # The bars the title talks about are highlighted
        barras = df_filtrado.sort_values("declaratorias").assign(
            grupo=lambda d: d["declaratorias"].eq(maximo).map({True: "Most", False: "Rest"}))
        fig = px.bar(barras, x="declaratorias", y="departamento", orientation="h",
                     color="grupo", text="declaratorias",
                     color_discrete_map={"Most": NARANJA, "Rest": OCRE},
                     labels={"declaratorias": "Emergency declarations", "departamento": "Department"})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(showlegend=False, bargap=0.25, xaxis=dict(showgrid=False),
                          yaxis=dict(ticksuffix="  ", categoryorder="array",
                                     categoryarray=barras["departamento"].tolist()))
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

            mediana_lluvia = tabla["lluvia_total_mm"].median()
            mediana_decl = tabla["declaratorias"].median()

            fig = px.scatter(df_filtrado, x="lluvia_total_mm", y="declaratorias",
                             hover_name="departamento",
                             text="departamento" if len(df_filtrado) <= 12 else None,
                             color="dias_lluvia_fuerte", color_continuous_scale=TONOS_LLUVIA,
                             range_color=(0, int(tabla["dias_lluvia_fuerte"].max())),
                             labels={"lluvia_total_mm": "Total rainfall (mm)",
                                     "declaratorias": "Emergency declarations",
                                     "dias_lluvia_fuerte": "Days with<br>20+ mm"})
            fig.update_traces(textposition="top center", textfont_size=10,
                              marker=dict(size=12, line=dict(width=1, color=TEXTO_SUAVE)))
            # Medians of the whole table: the quadrant analysis of Part 1
            fig.add_vline(x=mediana_lluvia, line_dash="dot", line_width=1, line_color=TEXTO_SUAVE)
            fig.add_hline(y=mediana_decl, line_dash="dot", line_width=1, line_color=TEXTO_SUAVE)
            st.plotly_chart(estilo(fig, titulo, 560), width="stretch")
            st.caption(f"Dotted lines: medians of all 25 departments ({mediana_lluvia:,.0f} mm "
                       f"and {mediana_decl:.0f} declarations). Points at the bottom right got "
                       "more rain but fewer declarations.")

    with tab_hist:
        n = len(df_filtrado)
        pocos = int((df_filtrado["lluvia_total_mm"] < 200).sum())
        muchos = int((df_filtrado["lluvia_total_mm"] > 1000).sum())
        sufijo = "department" if n == 1 else "departments"
        titulo = (f"{pocos} of {n} selected {sufijo} got less than 200 mm of rain, "
                  f"while {muchos} got more than 1,000 mm")

        # Count by 200 mm ranges, so empty ranges show no "0" label
        rangos = pd.cut(df_filtrado["lluvia_total_mm"], bins=range(0, 2000, 200), right=False)
        conteo = rangos.value_counts(sort=False)
        hist = pd.DataFrame({
            "rango": [f"{int(i.left):,}-{int(i.right):,}" for i in conteo.index],
            "departamentos": conteo.to_numpy(),
        })
        fig = px.bar(hist, x="rango", y="departamentos",
                     text=hist["departamentos"].where(hist["departamentos"] > 0, ""),
                     color_discrete_sequence=[AZUL],
                     labels={"rango": "Total rainfall (mm)", "departamentos": "Number of departments"})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(bargap=0.08, yaxis=dict(showgrid=False, dtick=1))
        st.plotly_chart(estilo(fig, titulo, 480), width="stretch")

# --- Map ----------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Map")
    variable = st.segmented_control("Color the map by", ["Total rainfall", "Emergency declarations"],
                                    default="Total rainfall", required=True)
    columna, tonos, leyenda = {
        "Total rainfall": ("lluvia_total_mm", TONOS_LLUVIA, "Total rainfall (mm)"),
        "Emergency declarations": ("declaratorias", TONOS_DECL, "Emergency declarations"),
    }[variable]

    # Classes of the whole table, so the colors keep their meaning when filtering
    clase_por_ubigeo, etiquetas = clases(tabla, columna)
    tonos = tonos[len(tonos) - len(etiquetas):]
    seleccion = mapa_datos[mapa_datos["ubigeo"].isin(df_filtrado["ubigeo"])][
        ["ubigeo", "departamento", "declaratorias", "lluvia_total_mm", "geometry"]]

    # No basemap: the departments sit on the Kanagawa background. Wheel zoom is off so
    # scrolling the page does not zoom the map; the +/- buttons still work.
    mapa = folium.Map(location=[-9.2, -75], zoom_start=5, tiles=None, scrollWheelZoom=False)
    mapa.get_root().header.add_child(folium.Element(
        f"<style>.leaflet-container {{ background: {FONDO}; }}</style>"))
    # Frame the selected departments, so the map zooms in when the filters narrow the view
    minx, miny, maxx, maxy = seleccion.total_bounds
    mapa.fit_bounds([[miny, minx], [maxy, maxx]], max_zoom=8)
    # Departments left out by the filters stay as a faint outline
    folium.GeoJson(
        mapa_datos[["geometry"]],
        style_function=lambda _: {"fillColor": GRIS, "fillOpacity": 0.2, "color": GRIS,
                                  "weight": 0.8},
    ).add_to(mapa)
    folium.GeoJson(
        seleccion,
        style_function=lambda f: {"fillColor": tonos[clase_por_ubigeo[f["properties"]["ubigeo"]]],
                                  "fillOpacity": 0.9, "color": FONDO, "weight": 1},
        highlight_function=lambda _: {"weight": 2.5, "color": "#DCD7BA"},  # fujiWhite
        tooltip=folium.GeoJsonTooltip(
            fields=["departamento", "declaratorias", "lluvia_total_mm"],
            aliases=["Department:", "Emergency declarations:", "Total rainfall (mm):"],
            localize=True,
            style=("background-color: #2A2A37; color: #DCD7BA; border: 1px solid #54546D; "
                   "font-family: sans-serif;"),
        ),
    ).add_to(mapa)

    # returned_objects=[] so moving or zooming the map does not rerun the whole app
    st_folium(mapa, height=520, use_container_width=True, returned_objects=[])

    # Legend drawn by Streamlit, so it follows the theme
    muestras = "".join(
        f"<span style='display:inline-block; width:0.8rem; height:0.8rem; background:{tono}; "
        f"border-radius:2px; margin:0 0.3rem 0 1rem; vertical-align:middle'></span>{etiqueta}"
        for tono, etiqueta in zip(tonos, etiquetas))
    st.markdown(f"<div style='font-size:0.9rem'><b>{leyenda}</b> (quantile classes of all "
                f"departments){muestras}</div>", unsafe_allow_html=True)

    sin_mapa = tabla.loc[~tabla["ubigeo"].isin(mapa_datos["ubigeo"]), "departamento"].tolist()
    if sin_mapa:
        st.warning(f"Departments without a boundary on the map: {', '.join(sin_mapa)}")
    else:
        st.caption(f"Join by ubigeo: all {len(mapa_datos)} departments matched "
                   "their boundary. Hover over a department to see its values; the faint "
                   "outlines are departments left out by the filters.")

# --- Data table ---------------------------------------------------------------
with st.container(border=True):
    st.subheader("Data")
    st.dataframe(
        df_filtrado,
        width="stretch",
        hide_index=True,
        column_order=["ubigeo", "departamento", "declaratorias", "prorrogas",
                      "lluvia_total_mm", "dias_lluvia_fuerte", "capital"],
        column_config={
            "ubigeo": st.column_config.TextColumn("Ubigeo"),
            "departamento": st.column_config.TextColumn("Department"),
            "declaratorias": st.column_config.NumberColumn("Declarations", format="%d"),
            "prorrogas": st.column_config.NumberColumn("Extensions", format="%d",
                                                       help="Extensions of an emergency already declared."),
            "lluvia_total_mm": st.column_config.ProgressColumn(
                "Total rainfall (mm)", format="%.1f", min_value=0,
                max_value=float(tabla["lluvia_total_mm"].max())),
            "dias_lluvia_fuerte": st.column_config.NumberColumn("Days with 20+ mm", format="%d"),
            "capital": st.column_config.TextColumn("Capital (where rain was measured)"),
        },
    )
    st.download_button(
        label="Download filtered data (CSV)",
        data=df_filtrado.to_csv(index=False).encode("utf-8-sig"),
        file_name="filtered_data.csv",
        mime="text/csv",
    )

st.divider()
st.caption(f"{FUENTE} · Group 02, Fundamentos de Python (Diplomado PUCP) · "
           f"[Code and notebooks on GitHub]({REPO})")
