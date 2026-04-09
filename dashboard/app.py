import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import pyodbc
import subprocess

# ================= CONFIG =================
st.set_page_config(
    page_title="Amazon Sales Dashboard",
    page_icon="📊",
    layout="wide"
)

# ================= STYLE =================
st.markdown("""
<style>
    .main { background-color: #FDF0F3; }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        border-left: 4px solid #8B2346;
        margin: 5px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #8B2346;
    }
    .metric-label {
        font-size: 13px;
        color: #1B6B7B;
    }
    h1 { color: #3D1A24; }
    h2, h3 { color: #8B2346; }
</style>
""", unsafe_allow_html=True)

COLORS = ["#8B2346", "#1B6B7B", "#2D8A6E", "#C4748A", "#5B4B8A", "#D4956A"]

# ================= CONNEXION AZURE SQL =================
@st.cache_data
def load_data():
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=monamazon--server.database.windows.net;"
            "DATABASE=amazone_dw;"
            "UID=ServerSA456cceb9;"
            "PWD=almy1234@;"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )

        fact = pd.read_sql("SELECT * FROM Fact_Commandes", conn)
        prod = pd.read_sql("SELECT * FROM Dim_Product", conn)
        loc  = pd.read_sql("SELECT * FROM Dim_Location", conn)
        date = pd.read_sql("SELECT * FROM Dim_Date", conn)
        cust = pd.read_sql("SELECT * FROM Dim_Customer", conn)

        conn.close()
        return fact, prod, loc, date, cust

    except Exception as e:
        st.error(f"❌ Erreur de connexion Azure SQL : {e}")
        return None, None, None, None, None

fact, prod, loc, date, cust = load_data()

if fact is None:
    st.stop()

#=========refresh=========
colA, colB, colC = st.columns([5,1,1])

with colB:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

with colC:
    if st.button(" Recalcul IA"):
        with st.spinner("Recalcul des modèles en cours..."):
            try:
                subprocess.run(["python", "ml/regression_forecast.py"], check=True)
                subprocess.run(["python", "ml/clustering_clients.py"], check=True)

                st.success("✅ Modèles IA recalculés avec succès")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"❌ Erreur lors du recalcul IA : {e}")

# ================= PREPARATION DES DONNEES =================
df = (
    fact.merge(prod, on="product_id", how="left")
        .merge(loc, on="location_id", how="left")
        .merge(date, on="date_id", how="left")
        .merge(cust, on="customer_id", how="left")
)

# ================= SIDEBAR FILTRES =================
st.sidebar.title("Filtres")

years = st.sidebar.multiselect(
    "Année",
    sorted(df["year"].dropna().unique()),
    default=sorted(df["year"].dropna().unique())
)

categories = st.sidebar.multiselect(
    "Catégorie",
    sorted(df["category"].dropna().unique()),
    default=sorted(df["category"].dropna().unique())
)

countries = st.sidebar.multiselect(
    "Pays",
    sorted(df["country"].dropna().unique()),
    default=sorted(df["country"].dropna().unique())
)

statuses = st.sidebar.multiselect(
    "Statut commande",
    sorted(df["order_status"].dropna().unique()),
    default=sorted(df["order_status"].dropna().unique())
)

payment_methods = st.sidebar.multiselect(
    "Méthode de paiement",
    sorted(df["payment_method"].dropna().unique()),
    default=sorted(df["payment_method"].dropna().unique())
)

filtered = df[
    (df["year"].isin(years)) &
    (df["category"].isin(categories)) &
    (df["country"].isin(countries)) &
    (df["order_status"].isin(statuses)) &
    (df["payment_method"].isin(payment_methods))
].copy()

# Année précédente pour comparaison
prev_years = [y - 1 for y in years]
prev = df[
    (df["year"].isin(prev_years)) &
    (df["category"].isin(categories)) &
    (df["country"].isin(countries)) &
    (df["order_status"].isin(statuses)) &
    (df["payment_method"].isin(payment_methods))
].copy()

# ================= TITRE =================
st.title("Amazon Sales Dashboard")
st.caption(f"{filtered['order_id'].nunique():,} commandes filtrées")
st.markdown("---")

# ================= KPI CARDS =================
ca_total = filtered["ca_net"].sum()
nb_commandes = filtered["order_id"].nunique()
marge_totale = filtered["marge"].sum()
remise_moyenne = filtered["discount"].mean() * 100 if len(filtered) > 0 else 0
panier_moyen = ca_total / nb_commandes if nb_commandes > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">CA Total</div>
        <div class="metric-value">${ca_total/1e6:.1f}M</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Commandes</div>
        <div class="metric-value">{nb_commandes:,}</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Marge totale</div>
        <div class="metric-value">${marge_totale/1e6:.1f}M</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Remise moyenne</div>
        <div class="metric-value">{remise_moyenne:.1f}%</div>
    </div>""", unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Panier moyen</div>
        <div class="metric-value">${panier_moyen:.0f}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ================= ROW 1 : COURBE + TREEMAP =================
col_left, col_right = st.columns([2, 1])

with col_left:
    ca_mois = (
        filtered.groupby(["year", "month", "month_name"], as_index=False)["ca_net"]
        .sum()
        .rename(columns={"ca_net": "CA_mensuel"})
        .sort_values(["year", "month"])
    )

    ca_mois["periode"] = (
        ca_mois["year"].astype(int).astype(str) + "-" +
        ca_mois["month"].astype(int).astype(str).str.zfill(2)
    )

    fig_line = px.line(
        ca_mois,
        x="periode",
        y="CA_mensuel",
        title="Évolution du CA par mois",
        markers=True,
        color_discrete_sequence=["#1B6B7B"]
    )
    fig_line.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="#FDF0F3",
        title_font_color="#3D1A24",
        xaxis_title="Période",
        yaxis_title="CA net ($)"
    )
    st.plotly_chart(fig_line, use_container_width=True)

with col_right:
    ca_cat = (
        filtered.groupby("category", as_index=False)["ca_net"]
        .sum()
        .rename(columns={"ca_net": "CA_par_categorie"})
        .sort_values("CA_par_categorie", ascending=False)
    )

    fig_tree = px.treemap(
        ca_cat,
        path=["category"],
        values="CA_par_categorie",
        title="CA par catégorie",
        color="CA_par_categorie",
        color_continuous_scale=["#FDF0F3", "#C4748A", "#8B2346"]
    )
    fig_tree.update_layout(paper_bgcolor="#FDF0F3")
    st.plotly_chart(fig_tree, use_container_width=True)

# ================= ROW 2 : CARTE + DONUT STATUT =================
col3a, col3b = st.columns([2, 1])

with col3a:
    ca_pays = (
        filtered.groupby("country", as_index=False)["ca_net"]
        .sum()
        .rename(columns={"ca_net": "CA_par_pays"})
        .sort_values("CA_par_pays", ascending=False)
    )

    fig_map = px.choropleth(
        ca_pays,
        locations="country",
        locationmode="country names",
        color="CA_par_pays",
        title="Répartition géographique du CA",
        color_continuous_scale=["#FDF0F3", "#C4748A", "#8B2346"]
    )
    fig_map.update_layout(
        paper_bgcolor="#FDF0F3",
        coloraxis_colorbar_title="CA net ($)"
    )
    st.plotly_chart(fig_map, use_container_width=True)

with col3b:
    status = (
        filtered.groupby("order_status", as_index=False)["order_id"]
        .nunique()
        .rename(columns={"order_id": "Nombre_commandes"})
        .sort_values("Nombre_commandes", ascending=False)
    )

    fig_donut = px.pie(
        status,
        names="order_status",
        values="Nombre_commandes",
        title="Statut des commandes",
        hole=0.5,
        color_discrete_sequence=COLORS
    )
    fig_donut.update_layout(paper_bgcolor="#FDF0F3")
    st.plotly_chart(fig_donut, use_container_width=True)

# ================= ROW 3 : TOP PRODUITS + PAIEMENT =================
col4a, col4b = st.columns([1, 1])

with col4a:
    top10 = (
        filtered.groupby(["product_name", "category"], as_index=False)
        .agg(
            CA_par_produit=("ca_net", "sum"),
            Commandes=("order_id", "nunique")
        )
        .sort_values("CA_par_produit", ascending=False)
        .head(10)
        .sort_values("CA_par_produit", ascending=True)
    )

    fig_top = px.bar(
        top10,
        x="CA_par_produit",
        y="product_name",
        orientation="h",
        title="Top 10 produits par CA",
        color="CA_par_produit",
        color_continuous_scale=["#F0C4D0", "#8B2346"]
    )
    fig_top.update_layout(
        paper_bgcolor="#FDF0F3",
        plot_bgcolor="white",
        xaxis_title="CA net ($)",
        yaxis_title="Produit",
        coloraxis_showscale=False
    )
    st.plotly_chart(fig_top, use_container_width=True)

with col4b:
    pay = (
        filtered.groupby("payment_method", as_index=False)["ca_net"]
        .sum()
        .rename(columns={"ca_net": "CA_par_paiement"})
        .sort_values("CA_par_paiement", ascending=False)
    )

    fig_pay = px.pie(
        pay,
        names="payment_method",
        values="CA_par_paiement",
        title="CA par méthode de paiement",
        hole=0.45,
        color_discrete_sequence=COLORS
    )
    fig_pay.update_layout(paper_bgcolor="#FDF0F3")
    st.plotly_chart(fig_pay, use_container_width=True)

# ================= ROW 4 : COMPARAISON N vs N-1 =================
st.subheader("Comparaison CA — Année sélectionnée vs Année précédente")

ca_curr_mois = (
    filtered.groupby("month", as_index=False)["ca_net"]
    .sum()
    .rename(columns={"ca_net": "CA_selectionne"})
)

ca_prev_mois = (
    prev.groupby("month", as_index=False)["ca_net"]
    .sum()
    .rename(columns={"ca_net": "CA_precedent"})
)

comp = pd.merge(ca_curr_mois, ca_prev_mois, on="month", how="outer").fillna(0).sort_values("month")

fig_comp = go.Figure()
fig_comp.add_trace(go.Bar(
    x=comp["month"],
    y=comp["CA_selectionne"],
    name="Année sélectionnée",
    marker_color="#8B2346"
))
fig_comp.add_trace(go.Bar(
    x=comp["month"],
    y=comp["CA_precedent"],
    name="Année précédente",
    marker_color="#C4748A"
))
fig_comp.update_layout(
    barmode="group",
    paper_bgcolor="#FDF0F3",
    plot_bgcolor="white",
    xaxis_title="Mois",
    yaxis_title="CA net ($)",
    legend=dict(orientation="h", y=1.1)
)
st.plotly_chart(fig_comp, use_container_width=True)

# ================= TABLEAU DETAIL =================
st.subheader("Top 20 produits — Détail")

top20 = (
    filtered.groupby(["product_name", "category"], as_index=False)
    .agg(
        CA=("ca_net", "sum"),
        Commandes=("order_id", "nunique"),
        Marge_moy=("marge", "mean"),
        Remise_moy=("discount", "mean")
    )
    .sort_values("CA", ascending=False)
    .head(20)
)

top20["CA"] = top20["CA"].round(0)
top20["Marge_moy"] = top20["Marge_moy"].round(1)
top20["Remise_moy"] = (top20["Remise_moy"] * 100).round(1).astype(str) + "%"

st.dataframe(
    top20,
    use_container_width=True,
    height=400
)

st.markdown("---")
st.caption("Amazon Sales Dashboard • Projet BI 2026")
# ================= IA : PREDICTION CA =================
st.markdown("##  Prévision du chiffre d'affaires")

try:
    hist = pd.read_csv("ml/output/historical_revenue_with_predictions.csv")
    future = pd.read_csv("ml/output/future_revenue_forecast.csv")

    hist["date"] = hist["year"].astype(str) + "-" + hist["month"].astype(str).str.zfill(2)
    future["date"] = future["year"].astype(str) + "-" + future["month"].astype(str).str.zfill(2)

    fig_pred = px.line(
        hist,
        x="date",
        y="ca_mensuel",
        title="Historique + prédiction",
        labels={"ca_mensuel": "CA réel"},
        color_discrete_sequence=["#1B6B7B"]
    )

    fig_pred.add_scatter(
        x=hist["date"],
        y=hist["prediction_train"],
        mode="lines",
        name="Prédiction (train)",
        line=dict(dash="dot", color="#8B2346")
    )

    fig_pred.add_scatter(
        x=future["date"],
        y=future["ca_mensuel_prevu"],
        mode="lines+markers",
        name="Prévision future",
        line=dict(color="#C4748A")
    )

    fig_pred.update_layout(
        paper_bgcolor="#FDF0F3",
        plot_bgcolor="white",
        xaxis_title="Temps",
        yaxis_title="CA net ($)"
    )

    st.plotly_chart(fig_pred, use_container_width=True)

except:
    st.warning("⚠️ Fichiers de prédiction non trouvés")

# ================= IA : CLUSTERING CLIENTS =================
st.markdown("##  Segmentation des clients (K-means)")

try:
    clusters = pd.read_csv("ml/output/customer_clusters.csv")
    summary = pd.read_csv("ml/output/cluster_summary.csv")

    col1, col2 = st.columns(2)

    with col1:
        fig_cluster = px.scatter(
            clusters,
            x="frequence_commandes",
            y="ca_total",
            color="segment_label",
            title="Segmentation clients",
            hover_data=["customer_name"],
            color_discrete_sequence=["#8B2346","#1B6B7B","#2D8A6E"]
        )
        fig_cluster.update_layout(
            paper_bgcolor="#FDF0F3",
            plot_bgcolor="white"
        )
        st.plotly_chart(fig_cluster, use_container_width=True)

    with col2:
        st.markdown("### 📊 Résumé des segments")
        st.dataframe(summary, use_container_width=True)

except:
    st.warning("⚠️ Fichiers de clustering non trouvés")