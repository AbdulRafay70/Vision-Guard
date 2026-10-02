import { useState } from 'react';
import { ChevronRight } from './Icons';
import { inScope } from '../lib/registry';

// Collapsible City → Area → Street tree with camera counts. Selecting a node sets the scope.
export default function LocationTree({ cities, cameras, scope, onSelect }) {
  const [open, setOpen] = useState(() => new Set(cities.map((c) => c.id)));
  const toggle = (id) => setOpen((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const count = (sc) => cameras.filter((c) => inScope(c.placement, sc)).length;
  const isSel = (sc) => scope.cityId === sc.cityId && scope.areaId === sc.areaId && scope.streetId === sc.streetId;
  const unassigned = cameras.filter((c) => !c.placement).length;

  const row = ({ depth, sc, label, id, expandable }) => (
    <div key={id} className={`tree-row depth-${depth} ${isSel(sc) ? 'is-selected' : ''}`}>
      {expandable ? (
        <button className={`tree-caret ${open.has(id) ? 'is-open' : ''}`} onClick={() => toggle(id)} aria-label="Expand"><ChevronRight size={13} /></button>
      ) : <span className="tree-caret" />}
      <button className="tree-label" onClick={() => onSelect(sc)}>
        <span>{label}</span>
        <span className="tree-count mono">{count(sc)}</span>
      </button>
    </div>
  );

  return (
    <div className="tree">
      <div className={`tree-row depth-0 ${!scope.cityId ? 'is-selected' : ''}`}>
        <span className="tree-caret" />
        <button className="tree-label" onClick={() => onSelect({})}>
          <span>All locations</span><span className="tree-count mono">{cameras.length}</span>
        </button>
      </div>
      {cities.map((city) => (
        <div key={city.id}>
          {row({ depth: 0, id: city.id, sc: { cityId: city.id }, label: city.name, expandable: city.areas.length > 0 })}
          {open.has(city.id) && city.areas.map((area) => (
            <div key={area.id}>
              {row({ depth: 1, id: area.id, sc: { cityId: city.id, areaId: area.id }, label: area.name, expandable: area.streets.length > 0 })}
              {open.has(area.id) && area.streets.map((st) => (
                row({ depth: 2, id: st.id, sc: { cityId: city.id, areaId: area.id, streetId: st.id }, label: st.name })
              ))}
            </div>
          ))}
        </div>
      ))}
      {unassigned > 0 && <p className="tree-note">{unassigned} camera{unassigned > 1 ? 's' : ''} without a location</p>}
    </div>
  );
}
