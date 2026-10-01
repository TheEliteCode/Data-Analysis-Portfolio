-- Nigeria staple food price trends: MySQL 8 setup and analysis queries
-- Run after src/prepare_analyze.py has written data/processed/fact_staple_market_month.csv.
-- This schema stores the six staple series selected for the dashboard.

CREATE DATABASE IF NOT EXISTS nigeria_food_prices
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE nigeria_food_prices;

CREATE TABLE IF NOT EXISTS dim_market (
    market_id VARCHAR(40) NOT NULL,
    country_code CHAR(3) NOT NULL,
    country_name VARCHAR(80) NOT NULL,
    state_name VARCHAR(100),
    source_state_label VARCHAR(100),
    local_government_area VARCHAR(120),
    market_name VARCHAR(120),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    PRIMARY KEY (market_id),
    KEY ix_market_state (state_name)
);

CREATE TABLE IF NOT EXISTS dim_commodity (
    commodity_code VARCHAR(40) NOT NULL,
    commodity_name VARCHAR(80) NOT NULL,
    source_unit VARCHAR(80) NOT NULL,
    PRIMARY KEY (commodity_code)
);

CREATE TABLE IF NOT EXISTS fact_staple_market_month (
    price_date DATE NOT NULL,
    year SMALLINT UNSIGNED NOT NULL,
    month TINYINT UNSIGNED NOT NULL,
    market_id VARCHAR(40) NOT NULL,
    commodity_code VARCHAR(40) NOT NULL,
    commodity_name VARCHAR(80) NOT NULL,
    source_unit VARCHAR(80) NOT NULL,
    estimated_price DECIMAL(18,4),
    currency CHAR(3) NOT NULL,
    trust_score DECIMAL(8,4),
    spatially_interpolated TINYINT UNSIGNED,
    state_name VARCHAR(100),
    local_government_area VARCHAR(120),
    market_name VARCHAR(120),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    PRIMARY KEY (price_date, market_id, commodity_code),
    KEY ix_fact_state_date_product (state_name, price_date, commodity_code),
    KEY ix_fact_product_date (commodity_code, price_date),
    CONSTRAINT fk_fact_market FOREIGN KEY (market_id) REFERENCES dim_market(market_id),
    CONSTRAINT fk_fact_commodity FOREIGN KEY (commodity_code) REFERENCES dim_commodity(commodity_code)
);

-- Load dimension files using MySQL Workbench's Table Data Import Wizard, or use
-- LOAD DATA LOCAL INFILE with the corresponding CSV paths and IGNORE 1 ROWS.
-- Import dim_market.csv and dim_commodity.csv before importing the fact file.
-- For command-line loading, enable LOCAL INFILE in both client and server.
-- Example (replace the path with the absolute CSV path on your machine):
-- LOAD DATA LOCAL INFILE 'C:/path/to/data/processed/fact_staple_market_month.csv'
-- INTO TABLE fact_staple_market_month
-- CHARACTER SET utf8mb4
-- FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '"'
-- LINES TERMINATED BY '\n' IGNORE 1 ROWS;

-- Query 1: equal-weighted national estimate trend and year-over-year movement.
WITH national_month AS (
    SELECT price_date, commodity_code, commodity_name, source_unit, currency,
           COUNT(DISTINCT market_id) AS market_count,
           AVG(estimated_price) AS mean_estimated_price,
           AVG(trust_score) AS mean_trust_score,
           AVG(spatially_interpolated) AS interpolated_market_share
    FROM fact_staple_market_month
    GROUP BY price_date, commodity_code, commodity_name, source_unit, currency
),
national_yoy AS (
    SELECT *,
           100.0 * (mean_estimated_price / NULLIF(LAG(mean_estimated_price, 12)
               OVER (PARTITION BY commodity_code ORDER BY price_date), 0) - 1) AS yoy_change_pct
    FROM national_month
)
SELECT * FROM national_yoy ORDER BY price_date, commodity_code;

-- Query 2: latest available state estimates and within-product ranking.
WITH state_latest AS (
    SELECT state_name, commodity_code, commodity_name, source_unit, currency,
           MAX(price_date) AS price_date
    FROM fact_staple_market_month
    GROUP BY state_name, commodity_code, commodity_name, source_unit, currency
),
state_value AS (
    SELECT f.state_name, f.commodity_code, f.commodity_name, f.source_unit,
           f.currency, f.price_date, COUNT(DISTINCT f.market_id) AS market_count,
           AVG(f.estimated_price) AS mean_estimated_price
    FROM fact_staple_market_month f
    JOIN state_latest s USING (state_name, commodity_code, commodity_name, source_unit, currency, price_date)
    GROUP BY f.state_name, f.commodity_code, f.commodity_name, f.source_unit, f.currency, f.price_date
)
SELECT *,
       DENSE_RANK() OVER (PARTITION BY commodity_code ORDER BY mean_estimated_price DESC) AS price_rank_high_to_low
FROM state_value
ORDER BY commodity_code, price_rank_high_to_low, state_name;

-- Query 3: market-level recent year-over-year changes, for drill-through.
WITH market_yoy AS (
    SELECT current_row.price_date, current_row.state_name, current_row.market_name,
           current_row.market_id, current_row.commodity_code, current_row.commodity_name,
           current_row.source_unit, current_row.estimated_price,
           prior_row.estimated_price AS estimated_price_12m_earlier,
           100.0 * (current_row.estimated_price / NULLIF(prior_row.estimated_price, 0) - 1) AS yoy_change_pct
    FROM fact_staple_market_month current_row
    LEFT JOIN fact_staple_market_month prior_row
      ON prior_row.market_id = current_row.market_id
     AND prior_row.commodity_code = current_row.commodity_code
     AND prior_row.price_date = DATE_SUB(current_row.price_date, INTERVAL 1 YEAR)
)
SELECT * FROM market_yoy
WHERE price_date = (SELECT MAX(price_date) FROM fact_staple_market_month)
ORDER BY commodity_code, yoy_change_pct DESC;

-- Query 4: combined spatial/temporal relative price dispersion by state/product.
SELECT state_name, commodity_code, commodity_name, source_unit,
       COUNT(*) AS market_month_observations,
       AVG(estimated_price) AS mean_estimated_price,
       STDDEV_SAMP(estimated_price) AS stddev_estimated_price,
       100.0 * STDDEV_SAMP(estimated_price) / NULLIF(AVG(estimated_price), 0) AS coefficient_of_variation_pct
FROM fact_staple_market_month
GROUP BY state_name, commodity_code, commodity_name, source_unit
ORDER BY commodity_code, coefficient_of_variation_pct DESC;
