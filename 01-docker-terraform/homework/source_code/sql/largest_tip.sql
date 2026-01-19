WITH agg_puzone as(
    SELECT "PULocationID", "DOLocationID", tip_amount
    FROM green_taxi_data
    WHERE 1=1
    AND lpep_pickup_datetime >= '2025-11-01'
    AND lpep_pickup_datetime < '2025-12-01'
),
filtered_zone as(
    SELECT "LocationID", "Zone" as zone_pu
    FROM zones
    WHERE 1=1
    AND "Zone" = 'East Harlem North'
),
filtered_agg_zone as(
    SELECT b.zone_pu, a."DOLocationID", sum(a.tip_amount) as tip_amount
    FROM agg_puzone a
    JOIN filtered_zone b ON a."PULocationID" = b."LocationID"
    GROUP BY 1,2
)
SELECT a."Zone" as zone_do, b.zone_pu, b.tip_amount
FROM zones a
JOIN filtered_agg_zone b 
ON a."LocationID" = b."DOLocationID"
ORDER BY 3 desc;

