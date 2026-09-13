import { useEffect } from "react";
import { getWardEnvironmentalFeatures } from "../services/wardService";

export default function SupabaseTest() {
  useEffect(() => {
    async function testWeather() {
      try {
        const data = await getWardEnvironmentalFeatures(93);

        console.log("WARD 93 ENVIRONMENTAL DATA FROM REACT:", data);
      } catch (error) {
        console.error("ENVIRONMENTAL TEST FAILED:", error);
      }
    }

    testWeather();
  }, []);

  return <h1>Ward Environmental Test</h1>;
}