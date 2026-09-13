import { getWards } from "./wardService";
import { wards as mockWards } from "../data/wards.js";

export async function getDashboardWards() {
  const databaseWards = await getWards();

  return databaseWards.map((databaseWard) => {
    const mockWard = mockWards.find(
      (ward) => ward.id === databaseWard.id
    );

    if (!mockWard) {
      return databaseWard;
    }

    return {
      ...mockWard,

      // Real database identity
      id: databaseWard.id,
      name: databaseWard.name,
      dbId: databaseWard.dbId,

      // Use real population if it eventually exists
      population:
        databaseWard.population ?? mockWard.population,
    };
  });
}

