import os
import warnings


import psycopg2
import numpy as np


from dotenv import load_dotenv
from pvlib.solarposition import get_solarposition

from pythermalcomfort.models import (
    solar_gain,
    utci,
    wbgt,
    heat_index_lu
)

from pythermalcomfort.utilities import mean_radiant_tmp

#from scipy.optimize import brentq


load_dotenv()


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

cur = conn.cursor()


# ---------------------------------------------------------
# GLOBE TEMPERATURE ESTIMATION
# ---------------------------------------------------------

def estimate_globe_temperature(
    target_mrt,
    air_temperature,
    wind_speed,
    diameter=0.15,
    emissivity=0.95
):

    def error(tg):

        try:

            if tg <= 0:
                return np.nan

            calculated_mrt = float(
                mean_radiant_tmp(
                    tg=float(tg),
                    tdb=float(air_temperature),
                    v=max(float(wind_speed), 0.5),
                    d=float(diameter),
                    emissivity=float(emissivity),
                    standard="Mixed Convection"
                )
            )

            if not np.isfinite(calculated_mrt):
                return np.nan

            return calculated_mrt - target_mrt

        except (ValueError, RuntimeError):
            return np.nan


    # Reasonable search interval
    lower = max(
        0.1,
        air_temperature - 5
    )

    upper = air_temperature + 20


    lower_error = error(lower)
    upper_error = error(upper)


    if not np.isfinite(lower_error) or not np.isfinite(upper_error):
        raise ValueError(
            "Invalid MRT values at globe-temperature bounds."
        )


    # The solution must be bracketed.
    if lower_error * upper_error > 0:
        raise ValueError(
            "Could not bracket globe temperature solution."
        )


    # -----------------------------------------------------
    # BISECTION
    # -----------------------------------------------------

    for _ in range(12):

        middle = (lower + upper) / 2

        middle_error = error(middle)


        if not np.isfinite(middle_error):
            raise ValueError(
                "Invalid MRT during globe-temperature search."
            )


        if abs(middle_error) < 0.01:
            return float(middle)


        if lower_error * middle_error <= 0:

            upper = middle
            upper_error = middle_error

        else:

            lower = middle
            lower_error = middle_error


    return float(
        (lower + upper) / 2
    )


# ---------------------------------------------------------
# GET ONLY UNPROCESSED WEATHER RECORDS
# ---------------------------------------------------------

cur.execute("""
    SELECT
    wd.weather_id,
    wd.recorded_at,
    ST_Y(wd.location::geometry) AS latitude,
    ST_X(wd.location::geometry) AS longitude,
    wd.temperature,
    wd.relative_humidity,
    wd.wind_speed_kmh,
    wd.direct_radiation,
    wd.diffuse_radiation,
    wd.wet_bulb_temperature,
    wd.surface_temperature,
    wd.cloud_cover,
    wd.surface_pressure
FROM weather_data wd
WHERE wd.wet_bulb_temperature IS NOT NULL
  AND wd.surface_temperature IS NOT NULL
  AND wd.cloud_cover IS NOT NULL
  AND wd.recorded_at = (
      SELECT MAX(recorded_at)
      FROM weather_data
  )
  AND NOT EXISTS (
      SELECT 1
      FROM thermal_indices ti
      WHERE ti.weather_id = wd.weather_id
  )
ORDER BY wd.weather_id;


""")


rows = cur.fetchall()


print(
    f"Found {len(rows)} unprocessed weather records."
)


# ---------------------------------------------------------
# PROCESS WEATHER RECORDS
# ---------------------------------------------------------

processed = 0
skipped = 0


for row in rows:

    (
        weather_id,
        recorded_at,

        latitude,
        longitude,

        temperature,
        humidity,
        wind_kmh,

        direct_radiation,
        diffuse_radiation,

        wet_bulb_temperature,
        surface_temperature,
        cloud_cover,
        pressure

    ) = row


    try:

        # -------------------------------------------------
        # CONVERT VALUES TO FLOAT
        # -------------------------------------------------

        temperature = float(temperature)
        humidity = float(humidity)
        wind_kmh = float(wind_kmh)

        direct_radiation = float(
            direct_radiation
        )

        diffuse_radiation = float(
            diffuse_radiation
        )

        wet_bulb_temperature = float(
            wet_bulb_temperature
        )

        surface_temperature = float(
            surface_temperature
        )

        cloud_cover = float(
            cloud_cover
        )

        pressure = float(
            pressure
        )


        wind_ms = wind_kmh / 3.6


        # -------------------------------------------------
        # SOLAR POSITION
        # -------------------------------------------------

        solar_position = get_solarposition(
            time=recorded_at,
            latitude=latitude,
            longitude=longitude,
            altitude=0,
            pressure=pressure,
            temperature=temperature
        )


        solar_elevation = float(
            solar_position[
                "apparent_elevation"
            ].iloc[0]
        )


        # -------------------------------------------------
        # BASELINE MRT
        # -------------------------------------------------

        # Prototype assumption:
        # surface temperature is used
        # as baseline MRT.

        baseline_mrt = surface_temperature


        # -------------------------------------------------
        # SOLAR ΔMRT
        # -------------------------------------------------

        if (
            solar_elevation > 0
            and direct_radiation >= 200
        ):

            solar_result = solar_gain(
                sol_altitude=solar_elevation,
                sharp=0,
                sol_radiation_dir=direct_radiation,
                sol_transmittance=1.0,
                f_svv=0.5,
                f_bes=0.5,
                asw=0.7,
                posture="standing",
                round_output=True
            )


            solar_delta_mrt = float(
                solar_result.delta_mrt
            )

        else:

            solar_delta_mrt = 0.0


        # -------------------------------------------------
        # ESTIMATED MRT
        # -------------------------------------------------

        estimated_mrt = (
            baseline_mrt
            + solar_delta_mrt
        )


        # -------------------------------------------------
        # UTCI
        # -------------------------------------------------

        utci_result = utci(
            tdb=temperature,
            tr=estimated_mrt,
            v=max(wind_ms, 0.5),
            rh=humidity,
            units="SI",
            limit_inputs=True,
            round_output=True
        )


        utci_value = float(
            utci_result.utci
        )


        # -------------------------------------------------
        # EQUIVALENT GLOBE TEMPERATURE
        # -------------------------------------------------

        equivalent_globe_temperature = (
            estimate_globe_temperature(
                target_mrt=estimated_mrt,
                air_temperature=temperature,
                wind_speed=wind_ms
            )
        )


        # -------------------------------------------------
        # WBGT
        # -------------------------------------------------

        wbgt_result = wbgt(
            twb=wet_bulb_temperature,
            tg=equivalent_globe_temperature,
            tdb=temperature,
            with_solar_load=(
                direct_radiation >= 200
            ),
            round_output=True
        )


        wbgt_value = float(
            wbgt_result.wbgt
        )


        # -------------------------------------------------
        # HEAT INDEX
        # -------------------------------------------------

        heat_index_result = heat_index_lu(
            tdb=temperature,
            rh=humidity
        )


        heat_index_value = float(
            heat_index_result.hi
        )


        # -------------------------------------------------
        # INSERT THERMAL RESULTS
        # -------------------------------------------------

        cur.execute("""
            INSERT INTO thermal_indices (
                weather_id,
                mrt,
                globe_temperature,
                utci,
                wbgt,
                heat_index
            )

            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )

            ON CONFLICT (weather_id)
            DO NOTHING;
        """, (

            weather_id,

            estimated_mrt,

            equivalent_globe_temperature,

            utci_value,

            wbgt_value,

            heat_index_value
        ))


        processed += 1


        if processed % 100 == 0:
            print(f"Processed {processed} records...")


    except Exception as error:

        skipped += 1

        print(
            f"Weather ID {weather_id} → "
            f"SKIPPED: {error}"
        )


# ---------------------------------------------------------
# SAVE ALL INSERTS
# ---------------------------------------------------------

conn.commit()


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

print()

print(
    "=============================================="
)

print(
    "       THERMAL CALCULATION COMPLETE"
)

print(
    "=============================================="
)

print(
    f"Unprocessed weather records : {len(rows)}"
)

print(
    f"Processed                  : {processed}"
)

print(
    f"Skipped                    : {skipped}"
)

print(
    "=============================================="
)


# ---------------------------------------------------------
# CLOSE DATABASE
# ---------------------------------------------------------

cur.close()
conn.close()

