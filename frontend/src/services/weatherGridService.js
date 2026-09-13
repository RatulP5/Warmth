import { supabase } from "../lib/supabaseClient";

export async function getWeatherGrid() {
  const { data, error } = await supabase
    .from("weather_grid")
    .select("*")
    .limit(10);

  if (error) {
    console.error("Error fetching weather grid:", error);
    throw error;
  }

  return data;
}