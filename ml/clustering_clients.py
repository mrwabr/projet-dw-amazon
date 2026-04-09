import pandas as pd
import pyodbc
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ================= CONFIG CONNEXION =================
SQL_CONFIG = {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": "monamazon--server.database.windows.net;",   
    "database": "amazone_dw",                          # à vérifier demain
    "uid": "ServerSA456cceb9;",                          # à changer demain
    "pwd": "almy1234@;"                       # à changer demain
}


def get_connection():
    conn_str = (
        f"DRIVER={{{SQL_CONFIG['driver']}}};"
        f"SERVER={SQL_CONFIG['server']};"
        f"DATABASE={SQL_CONFIG['database']};"
        f"UID={SQL_CONFIG['uid']};"
        f"PWD={SQL_CONFIG['pwd']};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


def load_customer_data() -> pd.DataFrame:
    """
    Charge les données clients agrégées pour le clustering.
    """
    query = """
    SELECT
        c.customer_id,
        c.customer_name,
        COUNT(f.order_id) AS frequence_commandes,
        SUM(f.ca_net) AS ca_total,
        AVG(f.ca_net) AS panier_moyen
    FROM Fact_Commandes f
    JOIN Dim_Customer c
        ON f.customer_id = c.customer_id
    GROUP BY
        c.customer_id, c.customer_name
    ORDER BY
        ca_total DESC;
    """

    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()

    return df


def prepare_features(df: pd.DataFrame):
    """
    Prépare les variables utilisées pour K-means.
    """
    features = df[["frequence_commandes", "ca_total", "panier_moyen"]].copy()

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    return scaled_features


def train_kmeans(df: pd.DataFrame, scaled_features, n_clusters: int = 3):
    """
    Entraîne le modèle KMeans et affecte un cluster à chaque client.
    """
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df = df.copy()
    df["cluster"] = model.fit_predict(scaled_features)

    return model, df


def build_cluster_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Produit un résumé métier par cluster.
    """
    summary = (
        df.groupby("cluster", as_index=False)
        .agg(
            nb_clients=("customer_id", "count"),
            frequence_moyenne=("frequence_commandes", "mean"),
            ca_moyen=("ca_total", "mean"),
            panier_moyen=("panier_moyen", "mean")
        )
        .sort_values("ca_moyen", ascending=False)
    )

    return summary


def assign_cluster_labels(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute des labels métiers simples.
    """
    summary = summary.copy()
    labels = {}

    sorted_clusters = summary.sort_values("ca_moyen", ascending=False)["cluster"].tolist()

    if len(sorted_clusters) >= 3:
        labels[sorted_clusters[0]] = "Clients VIP"
        labels[sorted_clusters[1]] = "Clients réguliers"
        labels[sorted_clusters[2]] = "Petits clients"
    else:
        for i, cluster_id in enumerate(sorted_clusters):
            labels[cluster_id] = f"Segment {i+1}"

    summary["segment_label"] = summary["cluster"].map(labels)
    return summary


def apply_labels_to_clients(df: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    """
    Propage les labels métiers à la table client.
    """
    label_map = dict(zip(summary["cluster"], summary["segment_label"]))
    df = df.copy()
    df["segment_label"] = df["cluster"].map(label_map)
    return df


def save_outputs(clients_df: pd.DataFrame, summary_df: pd.DataFrame):
    output_dir = Path("ml/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    clients_df.to_csv(output_dir / "customer_clusters.csv", index=False)
    summary_df.to_csv(output_dir / "cluster_summary.csv", index=False)

    print("Fichiers générés :")
    print("- ml/output/customer_clusters.csv")
    print("- ml/output/cluster_summary.csv")


def main():
    print("Chargement des données clients...")
    df = load_customer_data()

    print("Préparation des variables...")
    scaled_features = prepare_features(df)

    print("Entraînement du modèle KMeans...")
    model, clustered_df = train_kmeans(df, scaled_features, n_clusters=3)

    print("Construction du résumé des clusters...")
    summary_df = build_cluster_summary(clustered_df)
    summary_df = assign_cluster_labels(summary_df)

    print("Application des labels métiers...")
    clustered_df = apply_labels_to_clients(clustered_df, summary_df)

    print("\n=== Résumé des clusters ===")
    print(summary_df)

    save_outputs(clustered_df, summary_df)


if __name__ == "__main__":
    main()