create or replace function get_ward_weather (p_ward_number integer) RETURNS table (
  ward_number integer,
  grid_id bigint,
  recorded_at timestamptz,
  temperature numeric,
  relative_humidity numeric,
  wind_speed_kmh numeric,
  solar_radiation numeric,
  wet_bulb_temperature numeric,
  surface_temperature numeric
) LANGUAGE sql as $$
    SELECT
        TRIM(w.ward_name)::integer AS ward_number,
        wg.grid_id,
        wd.recorded_at,
        wd.temperature,
        wd.relative_humidity,
        wd.wind_speed_kmh,
        wd.solar_radiation,
        wd.wet_bulb_temperature,
        wd.surface_temperature
    FROM wards w
    JOIN weather_grid wg
        ON ST_Contains(
            w.geometry::geometry,
            wg.location::geometry
        )
    JOIN weather_data wd
        ON wd.grid_id = wg.grid_id
    WHERE TRIM(w.ward_name)::integer = p_ward_number
      AND wd.recorded_at = (
          SELECT MAX(wd2.recorded_at)
          FROM weather_data wd2
          WHERE wd2.grid_id = wg.grid_id
      )
    ORDER BY wg.grid_id;
$$;

select
  *
from
  get_ward_weather (93);