SELECT lpep_pickup_datetime
FROM green_taxi_data
WHERE 1=1
AND trip_distance = (
    SELECT max(trip_distance)
    FROM green_taxi_data
    WHERE 1=1
    AND trip_distance <= 100
    );