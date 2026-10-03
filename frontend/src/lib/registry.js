import { useCallback, useEffect, useMemo, useState } from 'react';

// Location hierarchy (City → Area → Street) and camera placements.
// The backend has no notion of these, so they live in this browser's localStorage.
const KEY = 'vg.registry';

const SEED = {
  cities: [
    {
      id: 'khi', name: 'Karachi', areas: [
        { id: 'khi-saddar', name: 'Saddar', streets: [] },
        { id: 'khi-clifton', name: 'Clifton', streets: [] },
      ],
    },
  ],
  placements: {},
};

function load() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY));
    if (v && Array.isArray(v.cities) && v.placements) return v;
  } catch { /* storage unavailable or corrupt */ }
  return SEED;
}

const slug = (s) => s.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'loc';
const uid = (prefix, name) => `${prefix ? `${prefix}-` : ''}${slug(name)}-${Math.random().toString(36).slice(2, 6)}`;

const mapCity = (cities, cityId, fn) => cities.map((c) => (c.id === cityId ? fn(c) : c));
const mapArea = (city, areaId, fn) => ({ ...city, areas: city.areas.map((a) => (a.id === areaId ? fn(a) : a)) });

// A placement is in scope when it matches every level the scope specifies.
export function inScope(placement, scope = {}) {
  if (!scope.cityId) return true;
  if (!placement) return false;
  if (placement.cityId !== scope.cityId) return false;
  if (scope.areaId && placement.areaId !== scope.areaId) return false;
  if (scope.streetId && placement.streetId !== scope.streetId) return false;
  return true;
}

export function useRegistry() {
  const [data, setData] = useState(load);

  useEffect(() => {
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch { /* storage unavailable */ }
  }, [data]);

  const addCity = useCallback((name) => {
    const id = uid('', name);
    setData((d) => ({ ...d, cities: [...d.cities, { id, name: name.trim(), areas: [] }] }));
    return id;
  }, []);

  const addArea = useCallback((cityId, name) => {
    const id = uid(cityId, name);
    setData((d) => ({ ...d, cities: mapCity(d.cities, cityId, (c) => ({ ...c, areas: [...c.areas, { id, name: name.trim(), streets: [] }] })) }));
    return id;
  }, []);

  const addStreet = useCallback((cityId, areaId, name) => {
    const id = uid(areaId, name);
    setData((d) => ({
      ...d,
      cities: mapCity(d.cities, cityId, (c) => mapArea(c, areaId, (a) => ({ ...a, streets: [...a.streets, { id, name: name.trim() }] }))),
    }));
    return id;
  }, []);

  const place = useCallback((cameraId, placement) => {
    setData((d) => ({ ...d, placements: { ...d.placements, [cameraId]: placement } }));
  }, []);

  const unplace = useCallback((cameraId) => {
    setData((d) => {
      const placements = { ...d.placements };
      delete placements[cameraId];
      return { ...d, placements };
    });
  }, []);

  // Removing a node unassigns every camera placed at or below it
  const removeNode = useCallback((level, ids) => {
    setData((d) => {
      let cities = d.cities;
      if (level === 'city') cities = cities.filter((c) => c.id !== ids.cityId);
      else if (level === 'area') cities = mapCity(cities, ids.cityId, (c) => ({ ...c, areas: c.areas.filter((a) => a.id !== ids.areaId) }));
      else cities = mapCity(cities, ids.cityId, (c) => mapArea(c, ids.areaId, (a) => ({ ...a, streets: a.streets.filter((s) => s.id !== ids.streetId) })));
      const placements = Object.fromEntries(Object.entries(d.placements).filter(([, p]) => !inScope(p, ids)));
      return { cities, placements };
    });
  }, []);

  return useMemo(
    () => ({ cities: data.cities, placements: data.placements, addCity, addArea, addStreet, place, unplace, removeNode }),
    [data, addCity, addArea, addStreet, place, unplace, removeNode],
  );
}
