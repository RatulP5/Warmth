import { supabase } from "../lib/supabaseClient";

export async function getWards() {
  const { data, error } = await supabase
    .from("wards")
    .select("*")
    .order("ward_id");

  if (error) {
    console.error("Error fetching wards:", error);
    throw error;
  }

  return data.map((row) => {
    const wardNumber = Number(String(row.ward_name).trim());

    return {
      id: wardNumber,
      name: `Ward ${wardNumber}`,
      population: row.population,
      dbId: row.ward_id,
      geometry: row.geometry,
    };
  });
}

export async function getWardEnvironmentalFeatures(wardNumber) {
  const { data, error } = await supabase
    .from("ward_environmental_features")
    .select("*")
    .eq("ward_no", String(wardNumber))
    .order("recorded_at", { ascending: false })
    .limit(1)
    .single();

  if (error) {
    console.error(
      "Error fetching ward environmental features:",
      error
    );
    throw error;
  }

  if (!data) {
    return null;
  }

  return {
    wardNumber: Number(String(data.ward_no).trim()),
    recordedAt: data.recorded_at,

    temperature:
      data.avg_temperature != null
        ? Number(Number(data.avg_temperature).toFixed(1))
        : null,

    humidity:
      data.avg_humidity != null
        ? Number(Number(data.avg_humidity).toFixed(1))
        : null,

    windSpeed:
      data.avg_wind_speed != null
        ? Number(Number(data.avg_wind_speed).toFixed(1))
        : null,

    wbgt:
      data.avg_wbgt != null
        ? Number(Number(data.avg_wbgt).toFixed(1))
        : null,

    utci:
      data.avg_utci != null
        ? Number(Number(data.avg_utci).toFixed(1))
        : null,

    heatIndex:
      data.avg_heat_index != null
        ? Number(Number(data.avg_heat_index).toFixed(1))
        : null,
  };
}