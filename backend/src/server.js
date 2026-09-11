const dotenv=require('dotenv')
const path = require("path");
dotenv.config({ path: path.join(__dirname, "../.env") });
const app=require('./app')
const pool = require("./config/db");
require("./scheduler");

const port=process.env.PORT

async function startServer() {
    try {
        await pool.query("SELECT NOW()");
        console.log("Database connection successful");

        app.listen(port, () => {
            console.log(`Server running on port ${port}`);
        });
    } catch (error) {
        console.error("Database connection failed:", error.message);
    }
}

startServer();
