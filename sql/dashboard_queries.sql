USE amazon_dw;
GO

/* =========================================================
   KPI 1 — CA total
   Objectif : calculer le chiffre d'affaires total généré
   ========================================================= */
SELECT 
    SUM(ca_net) AS CA_total
FROM Fact_Commandes;
GO

/* =========================================================
   KPI 2 — Nombre de commandes
   Objectif : mesurer le volume total de commandes
   ========================================================= */
SELECT 
    COUNT(order_id) AS Nombre_commandes
FROM Fact_Commandes;
GO

/* =========================================================
   KPI 3 — Panier moyen
   Objectif : calculer la dépense moyenne par commande
   ========================================================= */
SELECT 
    SUM(ca_net) * 1.0 / COUNT(order_id) AS Panier_moyen
FROM Fact_Commandes;
GO

/* =========================================================
   KPI 4 — CA mensuel
   Objectif : analyser l’évolution du CA dans le temps
   ========================================================= */
SELECT 
    d.year,
    d.month,
    d.month_name,
    SUM(f.ca_net) AS CA_mensuel
FROM Fact_Commandes f
JOIN Dim_Date d
    ON f.date_id = d.date_id
GROUP BY 
    d.year, d.month, d.month_name
ORDER BY 
    d.year, d.month;
GO

/* =========================================================
   KPI 5 — CA par catégorie
   Objectif : identifier les catégories les plus rentables
   ========================================================= */
SELECT 
    p.category,
    SUM(f.ca_net) AS CA_par_categorie
FROM Fact_Commandes f
JOIN Dim_Product p
    ON f.product_id = p.product_id
GROUP BY 
    p.category
ORDER BY 
    CA_par_categorie DESC;
GO

/* =========================================================
   KPI 6 — CA par pays
   Objectif : analyser la répartition géographique du CA
   ========================================================= */
SELECT 
    l.country,
    SUM(f.ca_net) AS CA_par_pays
FROM Fact_Commandes f
JOIN Dim_Location l
    ON f.location_id = l.location_id
GROUP BY 
    l.country
ORDER BY 
    CA_par_pays DESC;
GO

/* =========================================================
   KPI 7 — Top 10 clients
   Objectif : identifier les clients les plus rentables
   ========================================================= */
SELECT TOP 10
    c.customer_name,
    SUM(f.ca_net) AS CA_par_client
FROM Fact_Commandes f
JOIN Dim_Customer c
    ON f.customer_id = c.customer_id
GROUP BY 
    c.customer_name
ORDER BY 
    CA_par_client DESC;
GO

/* =========================================================
   KPI 8 — Marge totale
   Objectif : mesurer la rentabilité globale
   ========================================================= */
SELECT 
    SUM(marge) AS Marge_totale
FROM Fact_Commandes;
GO

/* =========================================================
   KPI 9 — Taux de remise moyen
   Objectif : analyser la politique de réduction
   ========================================================= */
SELECT 
    AVG(discount) * 100 AS Taux_remise_moyen_pct
FROM Fact_Commandes;
GO

/* =========================================================
   KPI 10 — Répartition des statuts de commande
   Objectif : analyser la qualité des commandes
   ========================================================= */
SELECT 
    order_status,
    COUNT(order_id) AS Nombre_commandes,
    COUNT(order_id) * 100.0 / SUM(COUNT(order_id)) OVER() AS Pourcentage_commandes
FROM Fact_Commandes
GROUP BY 
    order_status
ORDER BY 
    Nombre_commandes DESC;
GO

/* =========================================================
   KPI 11 — Top 10 produits
   Objectif : identifier les produits les plus performants
   ========================================================= */
SELECT TOP 10
    p.product_name,
    p.category,
    SUM(f.ca_net) AS CA_par_produit
FROM Fact_Commandes f
JOIN Dim_Product p
    ON f.product_id = p.product_id
GROUP BY 
    p.product_name, p.category
ORDER BY 
    CA_par_produit DESC;
GO