WITH agg_puzone as(
    SELECT "PULocationID", sum(total_amount) as total_amount
    FROM green_taxi_data
    WHERE 1=1
    AND lpep_pickup_datetime >= '2025-11-18'
    AND lpep_pickup_datetime < '2025-11-19'
    GROUP BY 1
)
SELECT a."Zone", b.total_amount
FROM zones a
JOIN agg_puzone b 
ON a."LocationID" = b."PULocationID"
ORDER BY 2 desc
LIMIT 1;

