
require("dotenv").config();

const pool = require("./config/db");
const { insertWeatherDataBatch } = require("./services/weatherService");


// --------------------------------------------------
// Helper: wait
// --------------------------------------------------

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// --------------------------------------------------
// Helper: fetch with retry for rate limiting
// --------------------------------------------------

async function fetchWeatherWithRetry(url, maxRetries = 5) {

    for (let attempt = 0; attempt <= maxRetries; attempt++) {

        try {

            // Abort request if it takes too long
            const controller = new AbortController();

            const timeout = setTimeout(() => {
                controller.abort();
            }, 30000); // 30 seconds


            const response = await fetch(url, {
                signal: controller.signal
            });


            clearTimeout(timeout);


            // ------------------------------------------
            // Successful request
            // ------------------------------------------

            if (response.ok) {
                return await response.json();
            }


            // ------------------------------------------
            // Rate limited
            // ------------------------------------------

            if (response.status === 429) {

                if (attempt === maxRetries) {
                    throw new Error(
                        "Open-Meteo rate limit persisted after maximum retries."
                    );
                }

                const waitTime =
                    10000 * Math.pow(2, attempt);

                console.log(
                    `429 rate limit. Waiting ${waitTime / 1000}s before retry...`
                );

                await sleep(waitTime);

                continue;
            }


            // ------------------------------------------
            // Server-side error
            // ------------------------------------------

            if (response.status >= 500) {

                if (attempt === maxRetries) {
                    throw new Error(
                        `Open-Meteo server error: ${response.status}`
                    );
                }

                const waitTime =
                    5000 * Math.pow(2, attempt);

                console.log(
                    `Server error ${response.status}. ` +
                    `Retrying in ${waitTime / 1000}s...`
                );

                await sleep(waitTime);

                continue;
            }


            // ------------------------------------------
            // Other HTTP error
            // ------------------------------------------

            throw new Error(
                `Weather API returned ${response.status}`
            );

        } catch (error) {

            // ------------------------------------------
            // Network failure / timeout
            // ------------------------------------------

            if (
                error.name === "TypeError" ||
                error.name === "AbortError"
            ) {

                if (attempt === maxRetries) {
                    throw new Error(
                        `Network request failed after ${maxRetries + 1} attempts: ${error.message}`
                    );
                }

                const waitTime =
                    5000 * Math.pow(2, attempt);

                console.log(
                    `Network request failed. ` +
                    `Retrying in ${waitTime / 1000}s...`
                );

                await sleep(waitTime);

                continue;
            }


            // Don't retry our deliberate final errors
            throw error;
        }
    }
}




// --------------------------------------------------
// Main function
// --------------------------------------------------

async function fetchGridWeather() {

    try {

        // --------------------------------------------------
        // Get all grid points
        // --------------------------------------------------

        const result = await pool.query(`
            SELECT
                grid_id,
                ST_Y(location::geometry) AS latitude,
                ST_X(location::geometry) AS longitude
            FROM weather_grid
            ORDER BY grid_id;
        `);

        const grids = result.rows;

        console.log(`Found ${grids.length} grid points.`);


        // --------------------------------------------------
        // One hourly timestep
        // --------------------------------------------------

        const batchSize = 50;

        // Delay between API requests
        const requestDelay = 5000;


        console.log(
            "Fetching only the current hourly weather data..."
        );


        // --------------------------------------------------
        // Process grids in batches
        // --------------------------------------------------

        for (
            let start = 0;
            start < grids.length;
            start += batchSize
        ) {

            const batch = grids.slice(
                start,
                start + batchSize
            );


            console.log(
                `\nProcessing grid points ${start + 1} to ${start + batch.length}...`
            );


            // --------------------------------------------------
            // Prepare coordinates
            // --------------------------------------------------

            const latitudes = batch
                .map(g => g.latitude)
                .join(",");

            const longitudes = batch
                .map(g => g.longitude)
                .join(",");


            // --------------------------------------------------
            // Open-Meteo request
            //
            // IMPORTANT:
            // forecast_hours=1 means ONLY ONE hourly timestep
            // is requested.
            // --------------------------------------------------

            const url =
                `https://api.open-meteo.com/v1/forecast` +
                `?latitude=${latitudes}` +
                `&longitude=${longitudes}` +
                `&hourly=` +
                `temperature_2m,` +
                `relative_humidity_2m,` +
                `dew_point_2m,` +
                `wind_speed_10m,` +
                `wind_direction_10m,` +
                `shortwave_radiation,` +
                `direct_radiation,` +
                `diffuse_radiation,` +
                `terrestrial_radiation,` +
                `surface_pressure,` +
                `wet_bulb_temperature_2m,` +
                `surface_temperature,` +
                `cloud_cover` +
                `&forecast_hours=1` +
                `&timezone=UTC`;


            // --------------------------------------------------
            // Call Open-Meteo
            // --------------------------------------------------

            const data =
                await fetchWeatherWithRetry(url);


            // --------------------------------------------------
            // Convert API response into DB records
            // --------------------------------------------------

            const weatherRecords = [];


            for (let i = 0; i < batch.length; i++) {

                const grid = batch[i];
                const weather = data[i];


                if (!weather || !weather.hourly) {

                    console.log(
                        `Warning: No weather data for grid ${grid.grid_id}`
                    );

                    continue;
                }


                // Because forecast_hours=1,
                // there should be exactly one timestep.

                if (
                    !weather.hourly.time ||
                    weather.hourly.time.length === 0
                ) {

                    console.log(
                        `Warning: Empty hourly data for grid ${grid.grid_id}`
                    );

                    continue;
                }


                weatherRecords.push({

                    grid_id:
                        grid.grid_id,

                    recorded_at:
                        weather.hourly.time[0],


                    latitude:
                        grid.latitude,

                    longitude:
                        grid.longitude,


                    temperature:
                        weather.hourly.temperature_2m[0],

                    relative_humidity:
                        weather.hourly.relative_humidity_2m[0],

                    wind_speed_kmh:
                        weather.hourly.wind_speed_10m[0],

                    wind_direction:
                        weather.hourly.wind_direction_10m[0],


                    solar_radiation:
                        weather.hourly.shortwave_radiation[0],

                    direct_radiation:
                        weather.hourly.direct_radiation[0],

                    diffuse_radiation:
                        weather.hourly.diffuse_radiation[0],

                    terrestrial_radiation:
                        weather.hourly.terrestrial_radiation[0],


                    dew_point:
                        weather.hourly.dew_point_2m[0],

                    surface_pressure:
                        weather.hourly.surface_pressure[0],

                    wet_bulb_temperature:
                        weather.hourly.wet_bulb_temperature_2m[0],


                    surface_temperature:
                        weather.hourly.surface_temperature[0],

                    cloud_cover:
                        weather.hourly.cloud_cover[0]
                });
            }


            console.log(
                `Collected ${weatherRecords.length} hourly records.`
            );


            // --------------------------------------------------
            // Bulk insert into PostgreSQL
            // --------------------------------------------------

            if (weatherRecords.length > 0) {

                await insertWeatherDataBatch(
                    weatherRecords
                );

                console.log(
                    `Inserted ${weatherRecords.length} records.`
                );
            }


            // --------------------------------------------------
            // Wait before next API request
            // --------------------------------------------------

            if (start + batchSize < grids.length) {

                console.log(
                    `Waiting ${requestDelay / 1000}s before next API request...`
                );

                await sleep(requestDelay);
            }
        }


        console.log(
            "\nHourly weather update completed successfully."
        );


    } catch (error) {

        console.error(
            "\nGrid weather fetch failed:",
            error.message
        );

    } finally {

        await pool.end();
    }
}


fetchGridWeather();

