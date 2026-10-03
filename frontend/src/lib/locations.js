// Canonical string key for a placement, used as <select> option values.
export function placementKey(p) {
  if (!p?.cityId || !p?.areaId) return '';
  return JSON.stringify(p.streetId ? { cityId: p.cityId, areaId: p.areaId, streetId: p.streetId } : { cityId: p.cityId, areaId: p.areaId });
}

// Flat list of every area and street, labelled "City › Area › Street".
export function locationOptions(cities) {
  return cities.flatMap((city) =>
    city.areas.flatMap((area) => [
      { value: placementKey({ cityId: city.id, areaId: area.id }), label: `${city.name} › ${area.name}` },
      ...area.streets.map((st) => ({
        value: placementKey({ cityId: city.id, areaId: area.id, streetId: st.id }),
        label: `${city.name} › ${area.name} › ${st.name}`,
      })),
    ]),
  );
}
