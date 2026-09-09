const cron = require("node-cron");
const { exec } = require("child_process");
const pool = require("./config/db");

function runPipeline() {

    console.log("======================================");
    console.log("Hourly heatwave pipeline started");
    console.log("======================================");

    exec("node src/fetchGridWeather.js", (error, stdout, stderr) => {

        if (error) {
            console.error("Weather fetch failed:");
            console.error(error.message);
            return;
        }

        console.log(stdout);
        console.log("Weather fetch completed.");
        console.log("Starting thermal calculation...");

        exec("python python/calculate_thermal.py", async(error, stdout, stderr) => {

            if (error) {
                console.error("Thermal calculation failed:");
                console.error(error.message);
                return;
            }

            console.log(stdout);

            if (stderr) {
                console.error(stderr);
            }

            console.log("Thermal calculation completed.");
            try {
                const result = await pool.query(`
                    DELETE FROM weather_data
                    WHERE recorded_at < NOW() - INTERVAL '15 days';
                `);

                console.log(`15-day cleanup completed. Deleted ${result.rowCount} old weather records.`);
                } catch (error) {
                    console.error("15-day cleanup failed:", error.message);
            }
        });
    });
}


cron.schedule("0 * * * *", runPipeline);