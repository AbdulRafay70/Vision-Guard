// Resolve a placement or scope to names in the location hierarchy.
function resolve(cities, ref = {}) {
  const city = cities.find((c) => c.id === ref.cityId);
  const area = city?.areas.find((a) => a.id === ref.areaId);
  const street = area?.streets.find((s) => s.id === ref.streetId);
  return [city, area, street].filter(Boolean).map((n) => n.name);
}

export function locationLabel(cities, placement) {
  if (!placement) return null;
  const parts = resolve(cities, placement);
  return parts.length ? parts.reverse().join(', ') : null;
}

export function scopeLabel(cities, scope) {
  const parts = resolve(cities, scope);
  return parts.length ? parts.join(' › ') : 'All locations';
}
