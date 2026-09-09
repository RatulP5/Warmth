const pool = require("../config/db");

async function insertWeatherDataBatch(records) {
    if (records.length === 0) {
        return;
    }

    const values = [];
    const placeholders = [];

    records.forEach((data, index) => {
        const offset = index * 17;

        placeholders.push(`(
            $${offset + 1},
            $${offset + 2},
            ST_SetSRID(
                ST_MakePoint($${offset + 3}, $${offset + 4}),
                4326
            )::geography,
            $${offset + 5},
            $${offset + 6},
            $${offset + 7},
            $${offset + 8},
            $${offset + 9},
            $${offset + 10},
            $${offset + 11},
            $${offset + 12},
            $${offset + 13},
            $${offset + 14},
            $${offset + 15},
            $${offset + 16},
            $${offset + 17},
            'Open-Meteo'
        )`);

        values.push(
            data.grid_id,
            data.recorded_at,
            data.longitude,
            data.latitude,
            data.temperature,
            data.relative_humidity,
            data.wind_speed_kmh,
            data.wind_direction,
            data.solar_radiation,
            data.direct_radiation,
            data.diffuse_radiation,
            data.terrestrial_radiation,
            data.dew_point,
            data.surface_pressure,
            data.wet_bulb_temperature,
            data.surface_temperature,
            data.cloud_cover
        );
    });

    const query = `
        INSERT INTO weather_data (
            grid_id,
            recorded_at,
            location,
            temperature,
            relative_humidity,
            wind_speed_kmh,
            wind_direction,
            solar_radiation,
            direct_radiation,
            diffuse_radiation,
            terrestrial_radiation,
            dew_point,
            surface_pressure,
            wet_bulb_temperature,
            surface_temperature,
            cloud_cover,
            source
        )
        VALUES ${placeholders.join(",")}
        ON CONFLICT (grid_id, recorded_at, source)
        DO NOTHING;
    `;

    await pool.query(query, values);
}

module.exports = { insertWeatherDataBatch };