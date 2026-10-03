import { describePlacement } from './registry';

export function locationLabel(cities, placement) {
  const d = describePlacement(cities, placement);
  return [d.street, d.area, d.city].filter(Boolean).join(', ');
}

export function scopeLabel(cities, scope) {
  if (!scope?.cityId) return 'All locations';
  const d = describePlacement(cities, scope);
  return [d.city, d.area, d.street].filter(Boolean).join(' / ');
}
