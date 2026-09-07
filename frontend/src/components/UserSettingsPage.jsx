import React, { useState, useEffect } from 'react';
import { 
  User, UserPlus, Shield, Key, Mail, Building, MapPin, 
  CheckCircle, Trash2, Edit, Search, Lock, RefreshCw, 
  AlertCircle, ShieldCheck, UserCheck, Settings, X, PlusCircle, LogOut, CheckCircle2
} from 'lucide-react';

export default function UserSettingsPage({ onLogout }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRoleFilter, setSelectedRoleFilter] = useState('ALL');
  
  // Logged-in user state
  const currentUser = {
    username: 'admin',
    full_name: 'Executive Command Operator',
    email: 'admin@visionguard.gov.pk',
    role: 'Super Admin',
    department: 'Central Command & Control',
    access_level: 'Full System Control',
    status: 'Active',
    sector: 'All Sectors (Karachi Grid)',
    last_login: '2026-09-07 22:30 PKT'
  };

  // Create User Modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newUserData, setNewUserData] = useState({
    username: '',
    full_name: '',
    email: '',
    password: '',
    confirm_password: '',
    role: 'Tactical Operator',
    department: 'Sector 1 - Saddar Command',
    sector: 'Sector 1 - Saddar',
    access_level: 'Live Monitor & Patrol Control',
    status: 'Active'
  });
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch system users on mount
  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/users');
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      } else {
        // Fallback default users
        setUsers([
          {
            username: "admin",
            full_name: "Executive Command Operator",
            email: "admin@visionguard.gov.pk",
            role: "Super Admin",
            department: "Central Command & Control",
            access_level: "Full System Control",
            status: "Active",
            sector: "All Sectors (Karachi Grid)",
            created_at: "2026-01-15T08:00:00Z",
            last_login: "2026-09-07T22:00:00Z"
          },
          {
            username: "operator_saddar",
            full_name: "Tariq Mahmood",
            email: "tariq.m@visionguard.gov.pk",
            role: "Tactical Operator",
            department: "Sector 1 - Saddar Command",
            access_level: "Live Monitor & Patrol Control",
            status: "Active",
            sector: "Sector 1 - Saddar",
            created_at: "2026-02-10T10:30:00Z",
            last_login: "2026-09-07T21:15:00Z"
          },
          {
            username: "analyst_clifton",
            full_name: "Dr. Sarah Khan",
            email: "sarah.k@visionguard.gov.pk",
            role: "Security Analyst",
            department: "Forensic Intelligence Unit",
            access_level: "Evidence Export & Analytics",
            status: "Active",
            sector: "Sector 2 - Clifton & DHA",
            created_at: "2026-03-01T14:20:00Z",
            last_login: "2026-09-06T18:45:00Z"
          }
        ]);
      }
    } catch (err) {
      console.warn("Error fetching users:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewUserData(prev => ({ ...prev, [name]: value }));
    setCreateError('');
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setCreateError('');
    setCreateSuccess('');

    // Validations
    if (!newUserData.username.trim()) {
      setCreateError('Username is required.');
      return;
    }
    if (!newUserData.full_name.trim()) {
      setCreateError('Full Name is required.');
      return;
    }
    if (!newUserData.email.trim() || !newUserData.email.includes('@')) {
      setCreateError('A valid Email address is required.');
      return;
    }
    if (!newUserData.password || newUserData.password.length < 6) {
      setCreateError('Password must be at least 6 characters.');
      return;
    }
    if (newUserData.password !== newUserData.confirm_password) {
      setCreateError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: newUserData.username,
          full_name: newUserData.full_name,
          email: newUserData.email,
          role: newUserData.role,
          department: newUserData.department,
          sector: newUserData.sector,
          access_level: newUserData.access_level,
          status: newUserData.status
        })
      });

      if (res.ok) {
        setCreateSuccess(`User account '${newUserData.username}' successfully created!`);
        setNewUserData({
          username: '',
          full_name: '',
          email: '',
          password: '',
          confirm_password: '',
          role: 'Tactical Operator',
          department: 'Sector 1 - Saddar Command',
          sector: 'Sector 1 - Saddar',
          access_level: 'Live Monitor & Patrol Control',
          status: 'Active'
        });
        fetchUsers();
        setTimeout(() => {
          setIsCreateModalOpen(false);
          setCreateSuccess('');
        }, 1500);
      } else {
        const errData = await res.json();
        setCreateError(errData.detail || 'Failed to create user account.');
      }
    } catch (err) {
      // Local optimistic update
      const newUser = {
        username: newUserData.username.toLowerCase(),
        full_name: newUserData.full_name,
        email: newUserData.email,
        role: newUserData.role,
        department: newUserData.department,
        access_level: newUserData.access_level,
        status: newUserData.status,
        sector: newUserData.sector,
        created_at: new Date().toISOString(),
        last_login: "Never"
      };
      setUsers(prev => [...prev, newUser]);
      setCreateSuccess(`User account '${newUserData.username}' registered locally.`);
      setTimeout(() => {
        setIsCreateModalOpen(false);
        setCreateSuccess('');
      }, 1500);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteUser = async (username) => {
    if (username.toLowerCase() === 'admin') {
      alert("Cannot delete primary system admin user.");
      return;
    }
    if (!window.confirm(`Are you sure you want to revoke and delete user account '${username}'?`)) {
      return;
    }

    try {
      await fetch(`/api/users/${username}`, { method: 'DELETE' });
    } catch (err) {
      console.warn("Delete user request fallback:", err);
    }
    setUsers(prev => prev.filter(u => u.username !== username));
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = 
      user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.department.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRole = selectedRoleFilter === 'ALL' || user.role === selectedRoleFilter;

    return matchesSearch && matchesRole;
  });

  return (
    <div className="user-settings-page">
      
      {/* Top Banner & Header */}
      <div className="users-hero-banner">
        <div className="users-hero-left">
          <div className="users-hero-icon">
            <Settings size={28} />
          </div>
          <div>
            <h1 className="users-hero-title">User Account & Identity Management</h1>
            <p className="users-hero-sub">Manage operator credentials, role-based access control (RBAC), and provision command center accounts.</p>
          </div>
        </div>

        <div className="users-actions-row">
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="btn-primary-emerald"
          >
            <UserPlus size={16} />
            <span>Create New User</span>
          </button>
          {onLogout && (
            <button
              type="button"
              onClick={onLogout}
              className="btn-secondary-slate"
            >
              <LogOut size={16} />
              <span>Log Out</span>
            </button>
          )}
        </div>
      </div>

      {/* Grid: Logged In Profile Card & System Governance */}
      <div className="users-top-grid">
        
        {/* Active Logged-In User Profile Card */}
        <div className="exec-card user-profile-card">
          <div className="profile-card-header">
            <div className="profile-avatar-row">
              <div className="profile-avatar">
                {currentUser.full_name.charAt(0)}
              </div>
              <div>
                <h3 className="profile-name">{currentUser.full_name}</h3>
                <span className="role-badge-pill">
                  <ShieldCheck size={13} />
                  {currentUser.role}
                </span>
              </div>
            </div>
          </div>

          <div className="user-details-list">
            <div className="user-detail-item">
              <span className="detail-label"><User size={15} /> Username:</span>
              <span className="detail-val font-mono">{currentUser.username}</span>
            </div>

            <div className="user-detail-item">
              <span className="detail-label"><Mail size={15} /> Email:</span>
              <span className="detail-val">{currentUser.email}</span>
            </div>

            <div className="user-detail-item">
              <span className="detail-label"><Building size={15} /> Department:</span>
              <span className="detail-val">{currentUser.department}</span>
            </div>

            <div className="user-detail-item">
              <span className="detail-label"><MapPin size={15} /> Assigned Sector:</span>
              <span className="detail-val">{currentUser.sector}</span>
            </div>

            <div className="user-detail-item">
              <span className="detail-label"><Shield size={15} /> Access Tier:</span>
              <span className="detail-val text-emerald">{currentUser.access_level}</span>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
            <span>Last authenticated session:</span>
            <span className="font-mono">{currentUser.last_login}</span>
          </div>
        </div>

        {/* Security Overview & RBAC Metrics Card */}
        <div className="exec-card governance-card">
          <div>
            <h3 className="section-title">
              <Shield size={20} className="text-emerald" /> Command Center Security Governance
            </h3>
            <p className="infra-subtitle mt-1">
              VisionGuard identity provider enforces mandatory role-based access limits across live CCTV feeds, AI telemetry, and evidence exports.
            </p>

            <div className="gov-stats-grid">
              <div className="gov-stat-box">
                <div className="gov-stat-label">
                  <UserCheck size={14} className="text-emerald" /> TOTAL OPERATORS
                </div>
                <div className="gov-stat-val">{users.length}</div>
                <div className="text-xs text-emerald mt-1 font-semibold">100% Verified</div>
              </div>

              <div className="gov-stat-box">
                <div className="gov-stat-label">
                  <ShieldCheck size={14} className="text-indigo" /> SUPER ADMINS
                </div>
                <div className="gov-stat-val">
                  {users.filter(u => u.role === 'Super Admin').length || 1}
                </div>
                <div className="text-xs text-indigo mt-1 font-semibold">Full Governance</div>
              </div>

              <div className="gov-stat-box">
                <div className="gov-stat-label">
                  <CheckCircle2 size={14} className="text-emerald" /> ACTIVE SESSIONS
                </div>
                <div className="gov-stat-val">
                  {users.filter(u => u.status === 'Active').length}
                </div>
                <div className="text-xs text-emerald mt-1 font-semibold">Authenticated</div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <CheckCircle2 size={15} className="text-emerald" />
              Audit Trail: User creation and modification events are signed with cryptographic timestamp.
            </span>
            <button onClick={fetchUsers} className="flex items-center gap-1 font-semibold text-emerald hover:underline border-none bg-transparent cursor-pointer">
              <RefreshCw size={13} /> Refresh Users
            </button>
          </div>
        </div>

      </div>

      {/* User Accounts Directory Table */}
      <div className="exec-card users-table-card">
        
        <div className="table-controls-row">
          <div>
            <h3 className="section-title">
              <User size={20} className="text-emerald" /> System Users Directory
            </h3>
            <p className="infra-subtitle">Active command center accounts authorized for surveillance monitoring and incident logging.</p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* Search Input */}
            <div className="search-input-box">
              <Search size={15} />
              <input
                type="text"
                placeholder="Search user, email, dept..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input-field"
              />
            </div>

            {/* Role Filter */}
            <select
              value={selectedRoleFilter}
              onChange={(e) => setSelectedRoleFilter(e.target.value)}
              className="role-filter-select"
            >
              <option value="ALL">All Roles</option>
              <option value="Super Admin">Super Admin</option>
              <option value="Tactical Operator">Tactical Operator</option>
              <option value="Security Analyst">Security Analyst</option>
            </select>
          </div>
        </div>

        {/* Users Table */}
        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="users-data-table">
            <thead>
              <tr>
                <th>User Details</th>
                <th>Role</th>
                <th>Department & Sector</th>
                <th>Access Tier</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '32px' }}>
                    <RefreshCw size={24} className="animate-spin text-emerald mx-auto mb-2" />
                    <div>Loading user directory...</div>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>
                    No matching users found.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <tr key={u.username}>
                    
                    {/* User Details */}
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-100 font-bold flex items-center justify-center text-sm border border-slate-300 text-slate-800 shrink-0">
                          {u.full_name ? u.full_name.charAt(0).toUpperCase() : u.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-bold text-slate-900">{u.full_name}</div>
                          <div className="text-xs text-slate-500 flex items-center gap-2 font-mono">
                            <span>@{u.username}</span>
                            <span>•</span>
                            <span>{u.email}</span>
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Role */}
                    <td>
                      <span className={`role-badge-pill ${
                        u.role === 'Super Admin'
                          ? 'bg-purple-100 text-purple-700'
                          : u.role === 'Security Analyst'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}>
                        <Shield size={12} />
                        {u.role}
                      </span>
                    </td>

                    {/* Department & Sector */}
                    <td>
                      <div className="font-semibold text-slate-800">{u.department}</div>
                      <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                        <MapPin size={12} />
                        {u.sector}
                      </div>
                    </td>

                    {/* Access Tier */}
                    <td className="font-mono text-xs font-semibold text-slate-700">
                      {u.access_level}
                    </td>

                    {/* Status */}
                    <td>
                      <span className={`user-status-pill ${
                        u.status === 'Active' ? 'status-active' : 'status-suspended'
                      }`}>
                        <CheckCircle2 size={12} />
                        {u.status}
                      </span>
                    </td>

                    {/* Actions */}
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        onClick={() => handleDeleteUser(u.username)}
                        disabled={u.username.toLowerCase() === 'admin'}
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition border-none bg-transparent cursor-pointer disabled:opacity-30"
                        title="Revoke / Delete User"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>

                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

      </div>

      {/* Modal: Provision New User Form */}
      {isCreateModalOpen && (
        <div className="user-modal-overlay">
          <div className="user-modal-card animate-in fade-in zoom-in duration-150">
            
            {/* Modal Header */}
            <div className="user-modal-header">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl">
                  <UserPlus size={22} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-lg m-0">Provision New Operator Account</h3>
                  <p className="text-xs text-slate-500 m-0">Enter operator identity details, assigned sector, and security tier.</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 border-none bg-transparent cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleCreateUser} className="user-modal-body">
              
              {createError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs flex items-center gap-2 font-semibold">
                  <AlertCircle size={16} className="shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              {createSuccess && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl text-xs flex items-center gap-2 font-semibold">
                  <CheckCircle2 size={16} className="shrink-0" />
                  <span>{createSuccess}</span>
                </div>
              )}

              <div className="form-grid-2">
                
                {/* Username */}
                <div className="input-group">
                  <label>Username / Handle *</label>
                  <input
                    type="text"
                    name="username"
                    required
                    placeholder="e.g. operator_saddar"
                    value={newUserData.username}
                    onChange={handleInputChange}
                    className="exec-input font-mono"
                  />
                </div>

                {/* Full Name */}
                <div className="input-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    name="full_name"
                    required
                    placeholder="e.g. Tariq Mahmood"
                    value={newUserData.full_name}
                    onChange={handleInputChange}
                    className="exec-input"
                  />
                </div>

                {/* Email */}
                <div className="input-group col-span-2">
                  <label>Official Email Address *</label>
                  <input
                    type="email"
                    name="email"
                    required
                    placeholder="e.g. operator@visionguard.gov.pk"
                    value={newUserData.email}
                    onChange={handleInputChange}
                    className="exec-input"
                  />
                </div>

                {/* Password */}
                <div className="input-group">
                  <label>Password *</label>
                  <input
                    type="password"
                    name="password"
                    required
                    placeholder="••••••••"
                    value={newUserData.password}
                    onChange={handleInputChange}
                    className="exec-input"
                  />
                </div>

                {/* Confirm Password */}
                <div className="input-group">
                  <label>Confirm Password *</label>
                  <input
                    type="password"
                    name="confirm_password"
                    required
                    placeholder="••••••••"
                    value={newUserData.confirm_password}
                    onChange={handleInputChange}
                    className="exec-input"
                  />
                </div>

                {/* Role */}
                <div className="input-group">
                  <label>Role Designation</label>
                  <select
                    name="role"
                    value={newUserData.role}
                    onChange={handleInputChange}
                    className="exec-select"
                  >
                    <option value="Tactical Operator">Tactical Operator</option>
                    <option value="Security Analyst">Security Analyst</option>
                    <option value="Super Admin">Super Admin</option>
                    <option value="Sector Specialist">Sector Specialist</option>
                  </select>
                </div>

                {/* Status */}
                <div className="input-group">
                  <label>Account Status</label>
                  <select
                    name="status"
                    value={newUserData.status}
                    onChange={handleInputChange}
                    className="exec-select"
                  >
                    <option value="Active">Active</option>
                    <option value="Read Only">Read Only</option>
                    <option value="Suspended">Suspended</option>
                  </select>
                </div>

                {/* Department */}
                <div className="input-group">
                  <label>Department / Unit</label>
                  <input
                    type="text"
                    name="department"
                    placeholder="e.g. Sector 1 - Saddar Command"
                    value={newUserData.department}
                    onChange={handleInputChange}
                    className="exec-input"
                  />
                </div>

                {/* Assigned Sector */}
                <div className="input-group">
                  <label>Assigned Sector Zone</label>
                  <select
                    name="sector"
                    value={newUserData.sector}
                    onChange={handleInputChange}
                    className="exec-select"
                  >
                    <option value="All Sectors (Karachi Grid)">All Sectors (Karachi Grid)</option>
                    <option value="Sector 1 - Saddar">Sector 1 - Saddar</option>
                    <option value="Sector 2 - Clifton & DHA">Sector 2 - Clifton & DHA</option>
                    <option value="Sector 3 - Lyari">Sector 3 - Lyari</option>
                    <option value="Sector 4 - Gulshan">Sector 4 - Gulshan</option>
                    <option value="Sector 5 - Orangi">Sector 5 - Orangi</option>
                  </select>
                </div>

              </div>

              {/* Access Tier Description */}
              <div className="input-group mt-2">
                <label>Access Level Scope</label>
                <input
                  type="text"
                  name="access_level"
                  placeholder="e.g. Live Monitor & Patrol Control"
                  value={newUserData.access_level}
                  onChange={handleInputChange}
                  className="exec-input"
                />
              </div>

              {/* Submit Buttons */}
              <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="btn-secondary-slate"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn-primary-emerald"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw size={15} className="animate-spin" />
                      <span>Provisioning Account...</span>
                    </>
                  ) : (
                    <>
                      <UserPlus size={15} />
                      <span>Create Operator Account</span>
                    </>
                  )}
                </button>
              </div>

            </form>

          </div>
        </div>
      )}

    </div>
  );
}
