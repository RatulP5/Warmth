require("dotenv").config();

const fs = require("fs");
const pool = require("./config/db");

function swapCoordinates(coords) {
    if (typeof coords[0] === "number") {
        return [coords[1], coords[0]];
    }

    return coords.map(swapCoordinates);
}
async function importWards() {
    try {
        const filePath = "./../data/kolkata_wards.geojson";

        const data = JSON.parse(
            fs.readFileSync(filePath, "utf8")
        );

        console.log(`Found ${data.features.length} wards.`);

        for (const feature of data.features) {
            console.log(
                "Processing ward:",
                feature.properties.WARD,
                    "Geometry:",
                feature.geometry.type
                );

            // Clean the ward number
            const wardName = feature.properties.WARD.trim();

            // GeoJSON coordinates
            // Swap latitude/longitude to longitude/latitude
            let correctedGeometry;

if (feature.geometry.type === "GeometryCollection") {
    correctedGeometry = {
        ...feature.geometry,
        geometries: feature.geometry.geometries.map(geometry => ({
            ...geometry,
            coordinates: swapCoordinates(geometry.coordinates)
        }))
    };
} else {
    correctedGeometry = {
        ...feature.geometry,
        coordinates: swapCoordinates(feature.geometry.coordinates)
    };
}

const geometry = JSON.stringify(correctedGeometry);
            const query = `
    INSERT INTO wards (
        ward_name,
        geometry
    )
    VALUES (
        $1,
        ST_Multi(
            ST_CollectionExtract(
                ST_Force2D(
                    ST_SetSRID(
                        ST_GeomFromGeoJSON($2),
                        4326
                    )
                ),
                3
            )
        )::geography
    )
    RETURNING ward_id, ward_name;
`;

            const result = await pool.query(query, [
                wardName,
                geometry
            ]);

            console.log(
                `Inserted ward ${result.rows[0].ward_name}`
            );
        }

        console.log("All wards imported successfully.");
        console.log(
        "\nFirst coordinate:",
                data.features[0].geometry.coordinates[0][0]
);

    } catch (error) {
        console.error("Ward import failed:", error.message);
    } finally {
        await pool.end();
    }
    
}

importWards();