# scripts/load.py
import pandas as pd
import pyodbc
from extract import write_watermark   # ✅ watermark déplacé ici


def get_conn():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=monamazon--server.database.windows.net;"
        "DATABASE=amazones_dw;"
        "UID=ServerSA456cceb9;"
        "PWD=almy1234@;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

def insert_df(cursor, df, table_name, pk_col):
    """
    MERGE : insère seulement les nouvelles lignes.
    Ne touche pas aux données existantes.
    """
    cols         = ', '.join(df.columns)
    placeholders = ', '.join(['?' for _ in df.columns])

    sql = f"""
        IF NOT EXISTS (SELECT 1 FROM {table_name} WHERE {pk_col} = ?)
        INSERT INTO {table_name} ({cols}) VALUES ({placeholders})
    """
    for row in df.itertuples(index=False, name=None):
        pk_value = row[list(df.columns).index(pk_col)]
        cursor.execute(sql, (pk_value,) + tuple(row))


def load(df):
    conn   = get_conn()
    cursor = conn.cursor()
    print("🔄 Début chargement dans SQL Server...")

    try:
        # --- Dim_Date ---
        dim_date = df[['OrderDate','Year','Month','Quarter',
                       'DayOfWeek','MonthName']].drop_duplicates().copy()
        dim_date.columns = ['date_id','year','month','quarter',
                            'day_of_week','month_name']
        dim_date['date_id'] = dim_date['date_id'].astype(str)
        insert_df(cursor, dim_date, 'Dim_Date', 'date_id')
        conn.commit()
        print(f"  ✅ Dim_Date      : {len(dim_date)} lignes")

        # --- Dim_Product ---
        dim_product = df[['ProductID','ProductName','Category','Brand']].copy()
        dim_product.columns = ['product_id','product_name','category','brand']
        dim_product = dim_product.drop_duplicates(subset=['product_id'], keep='first')
        insert_df(cursor, dim_product, 'Dim_Product', 'product_id')
        conn.commit()
        print(f"  ✅ Dim_Product   : {len(dim_product)} lignes")

        # --- Dim_Customer ---
        dim_customer = df[['CustomerID','CustomerName','PaymentMethod']].copy()
        dim_customer.columns = ['customer_id','customer_name','payment_method']
        dim_customer = dim_customer.drop_duplicates(subset=['customer_id'], keep='first')
        insert_df(cursor, dim_customer, 'Dim_Customer', 'customer_id')
        conn.commit()
        print(f"  ✅ Dim_Customer  : {len(dim_customer)} lignes")

        # --- Dim_Location ---
        dim_location = df[['City','State','Country']].copy()
        dim_location.columns = ['city','state','country']
        dim_location = dim_location.drop_duplicates(subset=['city','state','country'], keep='first')
        insert_df(cursor, dim_location, 'Dim_Location', 'city')
        conn.commit()
        print(f"  ✅ Dim_Location  : {len(dim_location)} lignes")

        # --- Dim_Seller ---
        dim_seller = df[['SellerID']].copy()
        dim_seller.columns = ['seller_id']
        dim_seller = dim_seller.drop_duplicates(subset=['seller_id'], keep='first')
        insert_df(cursor, dim_seller, 'Dim_Seller', 'seller_id')
        conn.commit()
        print(f"  ✅ Dim_Seller    : {len(dim_seller)} lignes")

        # --- Récupérer location_id générés par SQL Server ---
        cursor.execute("SELECT location_id, city, state, country FROM Dim_Location")
        rows = cursor.fetchall()
        dim_loc_db = pd.DataFrame(
            [tuple(r) for r in rows],
            columns=['location_id','city','state','country']
        )

        # --- Normaliser casse avant merge ---
        df['City']    = df['City'].str.strip().str.lower()
        df['State']   = df['State'].str.strip().str.lower()
        df['Country'] = df['Country'].str.strip().str.lower()
        dim_loc_db['city']    = dim_loc_db['city'].str.strip().str.lower()
        dim_loc_db['state']   = dim_loc_db['state'].str.strip().str.lower()
        dim_loc_db['country'] = dim_loc_db['country'].str.strip().str.lower()

        # --- Fact_Commandes ---
        df_merged = df.merge(
            dim_loc_db,
            left_on  = ['City','State','Country'],
            right_on = ['city','state','country'],
            how='left'
        )

        fact = df_merged[[
            'OrderID','OrderDate','ProductID','CustomerID',
            'location_id','SellerID',
            'Quantity','UnitPrice','Discount','Tax',
            'ShippingCost','TotalAmount','Marge','CA_Net',
            'OrderStatus'
        ]].copy()

        fact.columns = [
            'order_id','date_id','product_id','customer_id',
            'location_id','seller_id',
            'quantity','unit_price','discount','tax',
            'shipping_cost','total_amount','marge','ca_net',
            'order_status'
        ]

        fact['date_id'] = fact['date_id'].astype(str)

        insert_df(cursor, fact, 'Fact_Commandes', 'order_id')
        conn.commit()
        print(f"  ✅ Fact_Commandes: {len(fact)} lignes")

        # ✅ Watermark mis à jour SEULEMENT après succès complet du load
        # Si load échoue → watermark pas avancé → relance repart du bon endroit
        new_last_id = int(
            fact['order_id'].str.replace('ORD', '', regex=False).str.strip().astype(int).max()
        )
        write_watermark(new_last_id)
        print(f"  ✅ Watermark mis à jour → ORD{new_last_id:07d}")

        print("✅ Chargement SQL Server terminé !")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur : {e}")
        # ✅ Watermark PAS écrit → relance sécurisée
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    from extract import extract
    df_raw   = extract()
    from transform import transform
    df_clean = transform(df_raw)
    load(df_clean)