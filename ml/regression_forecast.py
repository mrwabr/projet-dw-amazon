import pandas as pd
import pyodbc
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from pathlib import Path


def get_connection():
    """
    Crée une connexion à Azure SQL.
    """
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
    return conn


def load_monthly_revenue() -> pd.DataFrame:
    """
    Charge le CA mensuel depuis Azure SQL.
    On utilise ca_net pour rester cohérent avec les KPI métier.
    """
    query = """
    SELECT
        d.year,
        d.month,
        d.month_name,
        SUM(f.ca_net) AS ca_mensuel
    FROM Fact_Commandes f
    JOIN Dim_Date d
        ON f.date_id = d.date_id
    GROUP BY
        d.year, d.month, d.month_name
    ORDER BY
        d.year, d.month;
    """

    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()

    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prépare les variables pour la régression.
    On transforme le temps en index numérique :
    0, 1, 2, 3, ...
    """
    df = df.copy()
    df["time_index"] = range(len(df))
    return df


def train_regression_model(df: pd.DataFrame):
    """
    Entraîne un modèle de régression linéaire.
    """
    X = df[["time_index"]]
    y = df["ca_mensuel"]

    model = LinearRegression()
    model.fit(X, y)

    df["prediction_train"] = model.predict(X)

    mae = mean_absolute_error(y, df["prediction_train"])
    r2 = r2_score(y, df["prediction_train"])

    return model, df, mae, r2


def forecast_future_months(model, df: pd.DataFrame, n_months: int = 6) -> pd.DataFrame:
    """
    Prédit le CA des prochains mois.
    """
    last_index = df["time_index"].max()

    future_df = pd.DataFrame({
        "time_index": range(last_index + 1, last_index + 1 + n_months)
    })

    future_df["prediction_future"] = model.predict(future_df[["time_index"]])

    # Reconstitution des dates futures
    last_year = int(df.iloc[-1]["year"])
    last_month = int(df.iloc[-1]["month"])

    future_years = []
    future_months = []

    current_year = last_year
    current_month = last_month

    for _ in range(n_months):
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1

        future_years.append(current_year)
        future_months.append(current_month)

    future_df["year"] = future_years
    future_df["month"] = future_months
    future_df["type"] = "forecast"

    return future_df


def save_outputs(train_df: pd.DataFrame, future_df: pd.DataFrame):
    """
    Sauvegarde les résultats en CSV pour réutilisation dans le dashboard.
    """
    output_dir = Path("ml/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    train_export = train_df[["year", "month", "month_name", "ca_mensuel", "prediction_train"]].copy()
    train_export["type"] = "historical"

    future_export = future_df[["year", "month", "prediction_future", "type"]].copy()
    future_export = future_export.rename(columns={"prediction_future": "ca_mensuel_prevu"})

    train_export.to_csv(output_dir / "historical_revenue_with_predictions.csv", index=False)
    future_export.to_csv(output_dir / "future_revenue_forecast.csv", index=False)

    print("Fichiers générés :")
    print("- ml/output/historical_revenue_with_predictions.csv")
    print("- ml/output/future_revenue_forecast.csv")


def main():
    print("Chargement des données mensuelles...")
    df = load_monthly_revenue()

    print("Préparation des features...")
    df = prepare_features(df)

    print("Entraînement du modèle...")
    model, train_df, mae, r2 = train_regression_model(df)

    print("Prédiction des prochains mois...")
    future_df = forecast_future_months(model, train_df, n_months=6)

    print("\n=== Évaluation du modèle ===")
    print(f"MAE : {mae:,.2f}")
    print(f"R²  : {r2:.4f}")

    print("\n=== Prévisions futures ===")
    print(future_df[["year", "month", "prediction_future"]])

    save_outputs(train_df, future_df)


if __name__ == "__main__":
    main()