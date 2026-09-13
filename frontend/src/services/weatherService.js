import { supabase } from "../lib/supabaseClient";

export async function getWards() {
  // your existing code
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
    console.error("Error fetching ward environmental features:", error);
    throw error;
  }

  if (!data) return null;

  return {
    wardNumber: Number(String(data.ward_no).trim()),
    recordedAt: data.recorded_at,

    temperature: Number(Number(data.avg_temperature).toFixed(1)),
    humidity: Number(Number(data.avg_humidity).toFixed(1)),
    windSpeed: Number(Number(data.avg_wind_speed).toFixed(1)),

    wbgt: Number(Number(data.avg_wbgt).toFixed(1)),
    utci: Number(Number(data.avg_utci).toFixed(1)),

    heatIndex:
      data.avg_heat_index != null
        ? Number(Number(data.avg_heat_index).toFixed(1))
        : null,
  };
}