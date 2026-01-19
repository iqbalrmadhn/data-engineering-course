SELECT count(*) as total_trips
FROM green_taxi_data
WHERE 1=1
AND lpep_pickup_datetime >= '2025-11-01'
AND lpep_pickup_datetime <  '2025-12-01'
AND trip_distance <= 1;