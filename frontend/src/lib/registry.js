// Location registry: City → Area → Street and camera placements, stored in the
// backend database (/api/locations). Mutations write through and then reload.
import { useCallback, useEffect, useState } from 'react';
import { api } from './api';

export function useRegistry(enabled = true) {
  const [cities, setCities] = useState([]);
  const [placements, setPlacements] = useState({});
  const [error, setError] = useState('');

  const reload = useCallback(async () => {
    try {
      const data = await api.locations();
      setCities(data.cities || []);
      setPlacements(data.placements || {});
      setError('');
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => { if (enabled) reload(); }, [enabled, reload]);

  const run = useCallback(async (fn) => {
    const result = await fn();
    await reload();
    return result;
  }, [reload]);

  return {
    cities,
    placements,
    error,
    reload,
    addCity: (name) => run(() => api.addCity(name)).then((n) => n.id),
    addArea: (cityId, name) => run(() => api.addArea(cityId, name)).then((n) => n.id),
    addStreet: (_cityId, areaId, name) => run(() => api.addStreet(areaId, name)).then((n) => n.id),
    rename: (level, id, name) => run(() => api.renameLocation(level, id, name)),
    removeNode: (level, ids) => run(() => api.deleteLocation(level, level === 'city' ? ids.cityId : level === 'area' ? ids.areaId : ids.streetId)),
    place: (cameraId, p) => run(() => api.placeCamera(cameraId, p)),
    unplace: (cameraId) => run(() => api.unplaceCamera(cameraId)),
  };
}

export function describePlacement(cities, p) {
  if (!p) return { city: null, area: null, street: null };
  const city = cities.find((c) => c.id === p.cityId);
  const area = city?.areas.find((a) => a.id === p.areaId);
  const street = area?.streets.find((s) => s.id === p.streetId);
  return { city: city?.name ?? null, area: area?.name ?? null, street: street?.name ?? null };
}

export function inScope(p, scope) {
  if (!scope || !scope.cityId) return true;
  if (!p) return false;
  if (p.cityId !== scope.cityId) return false;
  if (scope.areaId && p.areaId !== scope.areaId) return false;
  if (scope.streetId && p.streetId !== scope.streetId) return false;
  return true;
}
