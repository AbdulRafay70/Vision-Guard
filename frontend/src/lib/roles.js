// Mirrors the role sets enforced by the backend (prototype/web/console_db.py).
export const ROLES = ['Super Admin', 'Supervisor', 'Tactical Operator', 'Security Analyst', 'Viewer'];
export const can = {
  manageCameras: (u) => ['Super Admin', 'Supervisor'].includes(u?.role),
  operateCameras: (u) => ['Super Admin', 'Supervisor', 'Tactical Operator'].includes(u?.role),
  handleIncidents: (u) => u && u.role !== 'Viewer',
  manageUsers: (u) => u?.role === 'Super Admin',
  viewAudit: (u) => ['Super Admin', 'Supervisor'].includes(u?.role),
};
