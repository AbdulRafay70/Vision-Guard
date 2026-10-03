// Flattened list of every assignable location, for selects.
export function locationOptions(cities) {
  const out = [];
  for (const c of cities) {
    for (const a of c.areas) {
      out.push({ value: JSON.stringify({ cityId: c.id, areaId: a.id }), label: `${c.name} / ${a.name}` });
      for (const s of a.streets) {
        out.push({ value: JSON.stringify({ cityId: c.id, areaId: a.id, streetId: s.id }), label: `${c.name} / ${a.name} / ${s.name}` });
      }
    }
  }
  return out;
}

export const placementKey = (p) => (p ? JSON.stringify(p.streetId ? { cityId: p.cityId, areaId: p.areaId, streetId: p.streetId } : { cityId: p.cityId, areaId: p.areaId }) : '');
