import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { ShieldAlert } from './Icons';

// Shared "lawful basis for access" form, used in both connect flows.
// value: { basis, owner_name, owner_contact, reference, note }
export default function AccessFields({ value, onChange, compact }) {
  const [bases, setBases] = useState([]);
  useEffect(() => { api.accessBases().then(setBases).catch(() => {}); }, []);
  const set = (k) => (e) => onChange({ ...value, [k]: e.target.value });
  const current = bases.find((b) => b.id === value.basis);

  return (
    <div className="access-fields">
      {!compact && (
        <div className="access-note">
          <ShieldAlert size={15} />
          <span>Every camera must have a recorded lawful basis for access. This is logged and can be revoked. Only add cameras the agency owns or is authorised to use.</span>
        </div>
      )}
      <label className="field">
        <span>Lawful basis for access</span>
        <select value={value.basis || ''} onChange={set('basis')}>
          <option value="" disabled>Select a basis…</option>
          {bases.map((b) => <option key={b.id} value={b.id}>{b.label}</option>)}
        </select>
      </label>
      {current?.needs_owner && (
        <div className="form-grid two">
          <label className="field"><span>Camera owner</span><input value={value.owner_name || ''} onChange={set('owner_name')} placeholder="Name of person / business" /></label>
          <label className="field"><span>Owner contact <em>optional</em></span><input value={value.owner_contact || ''} onChange={set('owner_contact')} placeholder="Phone or email" /></label>
        </div>
      )}
      {current?.needs_reference && (
        <label className="field">
          <span>Authorisation reference</span>
          <input value={value.reference || ''} onChange={set('reference')} placeholder={value.basis === 'warrant' ? 'Court order / authorisation number' : 'Consent form / MoU reference'} />
        </label>
      )}
      {current && (
        <label className="field"><span>Note <em>optional</em></span><input value={value.note || ''} onChange={set('note')} placeholder="e.g. valid until Dec 2026" /></label>
      )}
    </div>
  );
}

export const BASIS_TAG = {
  owned: 'tag-live', consent: 'tag-info', mou: 'tag-info', warrant: 'tag-warn', public: 'tag-off', demo: 'tag-off',
};
