import { supabase } from "../lib/supabaseClient";

export async function getRiskPredictions() {
  const { data, error } = await supabase
    .from("risk_predictions")
    .select("*")
    .order("forecast_time");

  if (error) {
    console.error("Error fetching risk predictions:", error);
    throw error;
  }

  return data;
}