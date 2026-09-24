import React, { FormEvent, ReactNode, useEffect, useState } from 'react';
import { Link, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import indiaMap from '@svg-maps/india';
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import './index.css';
import MultiUploadPage from './MultiUploadPage';
import IntegrationPage from './IntegrationPage';
import { API_BASE, Role, useAuth } from './auth';
const levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const palette: Record<string, string> = { LOW: '#48a88a', MEDIUM: '#d7a64a', HIGH: '#e4774c', CRITICAL: '#d95b67' };

type Project = {
  id: number; project_name: string; project_code?: string; state: string; district: string; constituency?: string;
  category?: string; agency?: string; sanction_amount?: number; expenditure?: number; utilization_ratio?: number;
  expected_completion_date?: string; actual_completion_date?: string;
  anomaly_score?: number; normalized_ml_score?: number; ml_anomaly_flag?: boolean; risk_score?: number; risk_level?: string;
  status?: string; delay_days?: number; peer_median?: number; contextual_cost_deviation?: number;
  reasons?: string[]; primary_reason?: string; signal_components?: Record<string, number>; duplicate_flag?: boolean; source_datasets?: string[]; source_lineage?: Record<string, unknown>; cross_dataset_conflict?: boolean;
  calamity_type?: string; calamity_name?: string; consent_date?: string; consent_amount?: number; mp_name?: string; allocation_limit?: number; vendor_name?: string; payment_status?: string;
};
type Dashboard = {
  total_projects: number; total_sanction_amount: number; total_expenditure: number; total_utilization_ratio: number;
  high_risk_projects: number; critical_projects: number; active_alerts: number; risk_distribution: Record<string, number>; alert_distribution?: Record<string, number>;
  state_wise: any[]; district_wise: any[]; category_wise: any[]; risk_score_distribution: any[];
  utilization_distribution: any[]; delay_distribution: any[]; last_analysis?: string; model_status: string;
  dataset_status: string; top_projects: Project[];
  state_options?: string[];
};
type Alert = { id: number; project_id: number; project_name: string; severity: string; title: string; message: string; state: string; district: string };
type AuditCase = { id: number; project_id: number; title: string; priority: string; status: string; notes?: string; assigned_authority?: string; created_at?: string; updated_at?: string };

const money = (value?: number) => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value) : '—';
const compactMoney = (value?: number) => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(value) : '—';
const pct = (value?: number) => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '—';
const dateText = (value?: string) => value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'Not available';
const cx = (...parts: Array<string | false | undefined>) => parts.filter(Boolean).join(' ');
const projectTitle = (project: Project) => {
  const name = project.project_name?.trim();
  const code = project.project_code?.trim();
  return name && name !== code ? name : `${project.category || 'Public'} project in ${project.district || 'the recorded district'}, ${project.state || 'the recorded state'}`;
};
const reviewLevel = (project: Project) => {
  if (project.risk_level === 'DATA_QUALITY_REVIEW') return project.risk_level;
  const score = project.risk_score;
  if (typeof score !== 'number' || !Number.isFinite(score)) return project.risk_level || 'LOW';
  return score >= 80 ? 'CRITICAL' : score >= 60 ? 'HIGH' : score >= 35 ? 'MEDIUM' : 'LOW';
};

function RiskBadge({ level = 'LOW' }: { level?: string }) {
  return <span className={cx('risk-badge', `risk-${level.toLowerCase()}`)}><span className="risk-dot" />{level}</span>;
}
function Stat({ label, value, detail, tone = 'teal' }: { label: string; value: string; detail?: string; tone?: string }) {
  return <div className="stat-block"><div className="stat-label">{label}</div><div className="stat-value">{value}</div>{detail && <div className={cx('stat-detail', `tone-${tone}`)}>{detail}</div>}</div>;
}
function EmptyState({ title, text }: { title: string; text: string }) { return <div className="empty-state"><div className="empty-mark">/</div><strong>{title}</strong><span>{text}</span></div>; }
class ProjectPageBoundary extends React.Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() { return this.state.error ? <div className="page-stack"><section className="panel"><h2>Project page could not be displayed</h2><p>{this.state.error.message}</p></section></div> : this.props.children; }
}

const navGroups = [
  { label: 'MONITOR', items: [['Overview', '/', '01'], ['Risk Intelligence', '/risk', '02'], ['Projects', '/projects', '03']] },
  { label: 'OPERATE', items: [['Upload & Analyze', '/upload', '04'], ['Audit Copilot', '/audit-search', '05'], ['Alerts', '/alerts', '06'], ['Audit Cases', '/cases', '07']] },
  { label: 'INSIGHT', items: [['Analytics', '/analytics', '07'], ['Agency Intelligence', '/agencies', '08'], ['Fund Reconciliation', '/reconciliation', '09'], ['Duplicate Detection', '/duplicates', '10'], ['Data Integration', '/integration', '11'], ['Data Quality', '/data-quality', '12']] },
];
const roleTitles: Record<Role, string> = { MINISTRY: 'Ministry / National', STATE_NODAL_AUTHORITY: 'State Nodal Authority', DISTRICT_AUTHORITY: 'District Authority', MEMBER_OF_PARLIAMENT: 'Member of Parliament' };
function Shell({ children }: { children: ReactNode }) {
  const location = useLocation(); const navigate = useNavigate(); const [search, setSearch] = useState(''); const { user, logout, can } = useAuth();
  const visible = (path: string) => path !== '/upload' && path !== '/integration' || can('dataset:upload');
  const submitSearch = (event: FormEvent) => { event.preventDefault(); if (search.trim()) navigate(`/projects?search=${encodeURIComponent(search.trim())}`); };
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-seal">M</div><div><div className="brand-kicker">MPLADS AI</div><div className="brand-title">Audit Intelligence</div></div></div>
      <div className="side-rule" />
      {navGroups.map(group => <div className="nav-group" key={group.label}><div className="nav-label">{group.label}</div>{group.items.filter(([, path]) => visible(path)).map(([label, path, number]) => <Link key={path} to={path} className={cx('nav-item', location.pathname === path || (path !== '/' && location.pathname.startsWith(path)) ? 'active' : '')}><span className="nav-number">{number}</span><span>{label}</span></Link>)}</div>)}
      {(user?.role === 'MINISTRY' || user?.role === 'STATE_NODAL_AUTHORITY') && <div className="nav-group"><div className="nav-label">ADMINISTRATION</div><Link to="/users" className={cx('nav-item', location.pathname.startsWith('/users') ? 'active' : '')}><span className="nav-number">13</span><span>User Management</span></Link></div>}
      <div className="sidebar-bottom"><div className="system-card"><div className="status-line"><span className="live-dot" />System ready</div><div className="system-row"><span>Information</span><strong>Up to date</strong></div><div className="system-row"><span>Scope</span><strong>{user?.scope_id || 'National'}</strong></div></div><div className="authority"><span className="avatar">{user?.name.slice(0, 2).toUpperCase()}</span><div><strong>{user?.name}</strong><small>{user ? roleTitles[user.role] : ''}</small><button className="logout-link" onClick={logout}>Sign out</button></div></div></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="crumb">{user?.scope_type === 'NATIONAL' ? 'NATIONAL MONITORING' : `${user?.scope_type} MONITORING`} <span>/</span> {location.pathname === '/' ? 'OVERVIEW' : location.pathname.replace('/', '').replace('-', ' ').toUpperCase()}</div><form className="global-search" onSubmit={submitSearch}><span>⌕</span><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search projects, states, districts..." /><kbd>Enter</kbd></form><div className="top-actions"><button className="icon-button" title="Notifications" onClick={() => navigate('/alerts')}>!</button><div className="timestamp">09 SEP 2026<br /><span>{user?.scope_id || 'National'} workspace</span></div></div></header><main className="content">{children}</main></div>
  </div>;
}

function FilterBar({ onChange, values }: { onChange: (key: string, value: string) => void; values: Record<string, string> }) {
  const categories = ['Roads', 'Water Supply', 'Education', 'Health', 'Sanitation', 'Community Infrastructure', 'Trust and Society', 'Normal/Others', 'Calamity Relief'];
  return <div className="filter-bar"><div className="filter-title">FILTERS</div><select value={values.state} onChange={event => onChange('state', event.target.value)}><option value="">All states</option>{(values.stateOptions?.split('|') || []).filter(Boolean).sort((a, b) => a.localeCompare(b)).map(option => <option key={option}>{option}</option>)}</select><select value={values.category} onChange={event => onChange('category', event.target.value)}><option value="">All categories</option>{categories.sort((a, b) => a.localeCompare(b)).map(option => <option key={option}>{option}</option>)}</select><select value={values.risk_level} onChange={event => onChange('risk_level', event.target.value)}><option value="">All review levels</option>{levels.map(option => <option key={option}>{option}</option>)}</select><button className="button ghost" type="button" onClick={() => { onChange('state', ''); onChange('category', ''); onChange('risk_level', ''); }}>Clear all</button></div>;
}
function useDashboardFilters() { const [filters, setFilters] = useState<Record<string, string>>({ state: '', category: '', risk_level: '', stateOptions: '' }); const change = (key: string, value: string) => setFilters(previous => ({ ...previous, [key]: value })); return { filters, change }; }

function StateMap({ dashboard, selected, onSelect }: { dashboard: Dashboard; selected: string; onSelect: (state: string) => void }) {
  const stateRows = new Map((dashboard.state_wise || []).map(row => [row.name, row]));
  const maxRisk = Math.max(...(dashboard.state_wise || []).map(row => row.average_risk || 0), 1);
  const locations = (indiaMap as any).locations || [];
  return <div className="map-wrap"><div className="map-legend"><span>Lower risk</span><i className="legend-low" /><i className="legend-mid" /><i className="legend-high" /><span>Higher risk</span></div><svg className="india-map" viewBox={(indiaMap as any).viewBox} role="img" aria-label="Interactive India state risk map">{locations.map((location: any) => { const row = stateRows.get(location.name); const intensity = row ? Math.min((row.average_risk || 0) / maxRisk, 1) : 0; const fill = selected === location.name ? '#f2c66d' : `rgba(39, 151, 137, ${0.22 + intensity * 0.7})`; return <path key={location.id} d={location.path} fill={fill} className="state-shape" onClick={() => onSelect(location.name)}><title>{location.name}: {row ? `${row.projects} projects, avg risk ${row.average_risk.toFixed(1)}` : 'No analyzed projects'}</title></path>; })}</svg><div className="map-note">Select a state to inspect its risk concentration. Values are calculated from analyzed records.</div></div>;
}

function DashboardPage() {
  const location = useLocation();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null); const [compliance, setCompliance] = useState<any>(null); const [coverage, setCoverage] = useState<any>(null); const [fraudSummary, setFraudSummary] = useState<any>(null); const [reviewError, setReviewError] = useState(''); const { filters, change } = useDashboardFilters(); const [selectedState, setSelectedState] = useState('');
  const selectedRunId = new URLSearchParams(location.search).get('run_id');
  useEffect(() => { axios.get(`${API_BASE}/api/dashboard`, { params: { run_id: selectedRunId || undefined, state: selectedState || filters.state || undefined, category: filters.category || undefined, risk_level: filters.risk_level || undefined } }).then(response => { setDashboard(response.data); change('stateOptions', (response.data.state_options || []).join('|')); }); }, [selectedRunId, selectedState, filters.state, filters.category, filters.risk_level]);
  useEffect(() => { const params = { run_id: selectedRunId || undefined }; setReviewError(''); Promise.all([axios.get(`${API_BASE}/api/compliance/summary`, { params }), axios.get(`${API_BASE}/api/integration/coverage`, { params }), axios.get(`${API_BASE}/api/fraud-risk/summary`, { params })]).then(([findings, sourceCoverage, fraud]) => { setCompliance(findings.data); setCoverage(sourceCoverage.data); setFraudSummary(fraud.data); }).catch(() => setReviewError('Compliance, fraud-risk, and source coverage could not be loaded for this analysis run.')); }, [selectedRunId]);
  if (!dashboard) return <div className="page-loading">Loading intelligence workspace...</div>;
    const riskData = levels.map(level => ({ name: level, value: dashboard.risk_distribution?.[level] || 0 }));
  const stateData = (dashboard.state_wise || []).slice(0, 8).map(row => ({ name: row.name.replace(' Pradesh', ''), risk: Number(row.average_risk.toFixed(1)), projects: row.projects }));
  return <div className="page-stack"><div className="page-heading"><div><div className="eyebrow">NATIONAL PROJECT REVIEW</div><h1>Public project review</h1><p>Clear, evidence-based information to help officers decide what needs a closer look.</p></div><div className="heading-meta"><span className="live-dot" />DATA UPDATED<small>{dateText(dashboard.last_analysis)}</small></div></div>
    {dashboard.total_projects === 0 && <div className="notice demo-notice"><strong>No project data yet</strong><span>Upload one or more project files to begin. The overview will update from your files.</span></div>}
    <FilterBar values={filters} onChange={change} />
    <section className="kpi-grid"><Stat label="Projects analyzed" value={dashboard.total_projects.toLocaleString('en-IN')} detail="Across monitored records" /><Stat label="Sanctioned value" value={compactMoney(dashboard.total_sanction_amount)} detail={money(dashboard.total_sanction_amount)} tone="gold" /><Stat label="Expenditure" value={compactMoney(dashboard.total_expenditure)} detail={`${pct(dashboard.total_utilization_ratio)} overall utilization`} tone="blue" /><Stat label="High risk" value={String(dashboard.high_risk_projects)} detail={`${dashboard.critical_projects} critical cases`} tone="orange" /><Stat label="Open alerts" value={String(dashboard.active_alerts)} detail="Signals requiring review" tone="red" /></section>
    {reviewError ? <section className="notice">{reviewError}</section> : compliance && <section className="panel"><div className="eyebrow">COMPLIANCE AND FRAUD-RISK REVIEW</div><h2>{compliance.total_findings} compliance findings requiring human review</h2><p className="muted">These are review signals, not findings of fraud or wrongdoing.</p><div className="risk-summary">{Object.entries(compliance.by_severity || {}).map(([level, count]) => <div key={level}><span>{level}</span><strong>{String(count)}</strong></div>)}</div>{fraudSummary && <><h3>Potential fraud-risk indicators</h3><div className="risk-summary"><div><span>Projects with signals</span><strong>{fraudSummary.projects_with_signals}</strong></div><div><span>Project splitting</span><strong>{fraudSummary.project_splitting_count}</strong></div><div><span>Payment timing</span><strong>{fraudSummary.payment_timing_anomaly_count}</strong></div><div><span>Duplicate payments</span><strong>{fraudSummary.duplicate_payment_count}</strong></div><div><span>Repeated works</span><strong>{fraudSummary.repeated_work_count}</strong></div><div><span>Across years</span><strong>{fraudSummary.repeated_work_across_years_count}</strong></div></div><p className="muted">Potential fraud-risk signals require human verification and are not proof of wrongdoing.</p></> }<h3>Top compliance rules</h3><ul className="plain-list">{(compliance.items || []).slice(0, 5).map((item: any, index: number) => <li key={`${item.rule_code}-${index}`}><strong>{item.title}</strong> — {item.recommended_action}</li>)}</ul>{coverage && <p className="muted">Source coverage: {Object.entries(coverage.coverage_percentages || {}).map(([role, value]) => `${role}: ${value}%`).join(' · ') || 'Not available'}. Ambiguous rows: {(coverage.ambiguous_matches || []).length}; unmatched rows: {(coverage.unmatched_rows || []).length}.</p>}</section>}
    <div className="grid-2-1"><section className="panel map-panel"><div className="panel-head"><div><div className="eyebrow">STATE VIEW</div><h2>Where do projects need attention?</h2></div><button className="button ghost" onClick={() => { setSelectedState(''); change('state', ''); }}>All states</button></div><div className="map-layout"><StateMap dashboard={dashboard} selected={selectedState} onSelect={state => { setSelectedState(state); change('state', state); }} /><div className="state-insight"><div className="eyebrow">SELECTED STATE</div><h3>{selectedState || 'All India'}</h3>{selectedState ? <>{(() => { const row = dashboard.state_wise.find(item => item.name === selectedState); return row ? <><div className="insight-number">{row.average_risk.toFixed(1)}<small> avg risk</small></div><div className="insight-list"><div><span>Projects</span><strong>{row.projects}</strong></div><div><span>Sanctioned</span><strong>{compactMoney(row.sanctioned)}</strong></div><div><span>High risk</span><strong>{row.high_risk}</strong></div><div><span>Critical</span><strong>{row.critical}</strong></div></div></> : <EmptyState title="No records" text="This state has no analyzed records." />; })()}</> : <><div className="insight-number">{dashboard.total_utilization_ratio ? pct(dashboard.total_utilization_ratio) : '—'}<small> national utilization</small></div><div className="insight-list"><div><span>States covered</span><strong>{dashboard.state_wise.length}</strong></div><div><span>High risk</span><strong>{dashboard.high_risk_projects}</strong></div><div><span>Alerts</span><strong>{dashboard.active_alerts}</strong></div></div></>}</div></div></section>
      <section className="panel"><div className="panel-head"><div><div className="eyebrow">RISK PROFILE</div><h2>Projects by review level</h2></div><Link to="/alerts" className="text-link">Open reminders →</Link></div><div className="donut-wrap"><ResponsiveContainer width="60%" height={220}><PieChart><Pie data={riskData} dataKey="value" innerRadius={62} outerRadius={88} paddingAngle={3}>{riskData.map(item => <Cell key={item.name} fill={palette[item.name]} />)}</Pie><Tooltip formatter={(value: any, name: any) => [`${value} projects`, name]} /></PieChart></ResponsiveContainer><div className="risk-list">{riskData.map(item => <div key={item.name}><span className="risk-key" style={{ background: palette[item.name] }} />{item.name}<strong>{item.value}</strong></div>)}</div></div></section></div>
    <div className="grid-2"><section className="panel chart-panel"><div className="panel-head"><div><div className="eyebrow">STATE COMPARISON</div><h2>Average risk by state</h2></div></div><ResponsiveContainer width="100%" height={250}><BarChart data={stateData} margin={{ left: 0, right: 10, bottom: 25 }}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="name" angle={-25} textAnchor="end" height={55} tick={{ fill: '#65736e', fontSize: 11 }} /><YAxis tick={{ fill: '#65736e', fontSize: 11 }} /><Tooltip /><Bar dataKey="risk" fill="#238f82" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></section><section className="panel chart-panel"><div className="panel-head"><div><div className="eyebrow">OPERATIONAL SIGNAL</div><h2>Delayed completion profile</h2></div></div><ResponsiveContainer width="100%" height={250}><LineChart data={dashboard.delay_distribution}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="range" tick={{ fill: '#65736e', fontSize: 11 }} /><YAxis tick={{ fill: '#65736e', fontSize: 11 }} /><Tooltip /><Line type="monotone" dataKey="projects" stroke="#d57c4c" strokeWidth={3} dot={{ fill: '#d57c4c', r: 4 }} /></LineChart></ResponsiveContainer></section></div>
    <FilterBar values={filters} onChange={change} />
    <section className="panel attention-panel"><div className="panel-head"><div><div className="eyebrow">PROJECTS TO CHECK</div><h2>Priority attention required</h2><p>Projects with the strongest reasons for a closer review.</p></div><Link to="/risk" className="button secondary">View all projects to check</Link></div><ProjectTable projects={dashboard.top_projects} compact /></section>
  </div>;
}

function ProjectTable({ projects, compact = false }: { projects: Project[]; compact?: boolean }) { 
  const navigate = useNavigate(); 
  return <div className="table-scroll"><table className="data-table"><thead><tr><th>Project</th><th>Location</th><th>Category</th><th>Used</th><th>Delay</th><th>Review score (%)</th><th>Review level</th><th /></tr></thead><tbody>{projects.length ? projects.map(project => <tr key={project.id} onClick={() => navigate(`/projects/${project.id}`)}><td><strong>{projectTitle(project)}</strong><small>{project.project_code || `PROJECT-${project.id}`}</small></td><td>{project.state}<small>{project.district}</small></td><td>{project.category || 'Not recorded'}</td><td>{pct(project.utilization_ratio)}</td><td>{project.delay_days ? `${Math.round(project.delay_days)} days` : 'None recorded'}</td><td>{typeof project.risk_score === 'number' && Number.isFinite(project.risk_score) ? `${project.risk_score.toFixed(1)}%` : '—'} {project.ml_anomaly_flag && <span className="signal-chip">Needs review</span>}</td><td><RiskBadge level={reviewLevel(project)} /></td><td><span className="row-arrow">→</span></td></tr>) : <tr><td colSpan={8}><EmptyState title="No projects match" text="Clear a filter or broaden the search." /></td></tr>}</tbody></table></div>; 
}

function RiskPage() { 
  const [projects, setProjects] = useState<Project[]>([]); 
  const [query, setQuery] = useState(''); 
  const [level, setLevel] = useState(''); 
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 500;
  useEffect(() => { 
    axios.get(`${API_BASE}/api/projects`, { params: { page, page_size: pageSize, search: query || undefined, risk_level: level || undefined } }).then(response => { setProjects(response.data.records || response.data.items || []); setTotal(response.data.filtered_count ?? response.data.total_count ?? response.data.total ?? 0); setRiskCounts(response.data.risk_counts || {}); }); 
  }, [query, level, page]); 
  useEffect(() => setPage(1), [query, level]);
  const [riskCounts, setRiskCounts] = useState<Record<string, number>>({});
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return <div className="page-stack"><PageTitle eyebrow="AUDIT TRIAGE WORKSPACE" title="Risk Intelligence" subtitle="Prioritize human review using explainable model and rule signals." /><div className="risk-summary">{levels.map(item => <div key={item}><span className="risk-key" style={{ background: palette[item] }} /><span>{item}</span><strong>{riskCounts[item] || 0}</strong></div>)}</div><div className="toolbar"><div className="table-search">⌕<input placeholder="Search project, location, constituency..." value={query} onChange={event => setQuery(event.target.value)} /></div><select value={level} onChange={event => setLevel(event.target.value)}><option value="">All risk levels</option>{levels.map(item => <option key={item}>{item}</option>)}</select><span className="toolbar-count">{total.toLocaleString('en-IN')} matching projects</span><button className="button secondary" onClick={() => window.print()}>Export view</button></div><section className="panel table-panel"><ProjectTable projects={projects} /><div className="pagination"><button className="button ghost" disabled={page === 1} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page} of {pages} · {pageSize} per page</span><button className="button ghost" disabled={page >= pages} onClick={() => setPage(value => value + 1)}>Next</button></div></section></div>; 
}
function PageTitle({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle: string }) { 
  return <div className="page-heading simple"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div></div>; 
}

function downloadProjectReport(project: Project, explanation: any, similar: any[]) {
  const escapeHtml = (value: unknown) => String(value ?? 'Not available').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[character] || character));
  const rows = [
    ['Project ID', project.project_code || project.id],
    ['Project name', projectTitle(project)],
    ['State', project.state],
    ['District', project.district],
    ['Constituency', project.constituency],
    ['MP', project.mp_name],
    ['Category', project.category],
    ['Vendor', project.vendor_name],
    ['Status', project.status],
    ['Sanctioned amount', money(project.sanction_amount)],
    ['Amount spent', money(project.expenditure)],
    ['Amount used', pct(project.utilization_ratio)],
    ['Delay', project.delay_days ? `${Math.round(project.delay_days)} days` : 'No delay recorded'],
    ['Review level', reviewLevel(project)],
    ['Review score', typeof project.risk_score === 'number' ? `${project.risk_score.toFixed(1)}%` : '—'],
    ['Payment status', project.payment_status],
  ];
  const issues = (explanation?.why_flagged || project.reasons || ['No specific issue recorded.']).map((item: string) => `<li>${escapeHtml(item)}</li>`).join('');
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Project report - ${escapeHtml(project.project_name)}</title><style>body{font:15px Arial;color:#173f3b;max-width:900px;margin:40px auto;line-height:1.5}h1{margin-bottom:4px}h2{border-bottom:2px solid #dce8e3;padding-bottom:8px;margin-top:28px}table{border-collapse:collapse;width:100%}td{padding:9px;border-bottom:1px solid #dce8e3}td:first-child{font-weight:700;width:32%}li{margin:8px 0}.card{background:#f5f8f6;padding:16px;border-radius:8px}</style></head><body><h1>${escapeHtml(project.project_name)}</h1><p>Project report for field review</p><h2>Project details</h2><table>${rows.map(([label, value]) => `<tr><td>${escapeHtml(label)}</td><td>${escapeHtml(value)}</td></tr>`).join('')}</table><h2>What needs checking</h2><div class="card"><ul>${issues}</ul></div><h2>Records to request</h2><div class="card"><ul>${(explanation?.recommended_verification || ['Approval papers', 'Bills and payment records', 'Completion proof', 'Site photographs']).map((item: string) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div><h2>Comparable projects</h2><table>${similar.slice(0, 10).map(item => `<tr><td>${escapeHtml(item.project_code || item.id)}</td><td>${escapeHtml(item.project_name)}</td><td>${escapeHtml(item.state)} · ${escapeHtml(item.category)}</td><td>${escapeHtml(item.similarity)}% similar</td></tr>`).join('') || '<tr><td colspan="4">No comparable projects found.</td></tr>'}</table><p>Prepared from the uploaded project records. Review signals are prompts for checking records, not proof of wrongdoing.</p></body></html>`;
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
  link.download = `${project.project_code || `project-${project.id}`}-report.html`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function ProjectOverview({ project, explanation }: { project: Project; explanation: any }) {
  const title = projectTitle(project);
  const approved = project.sanction_amount || 0;
  const spent = project.expenditure || 0;
  const remaining = approved - spent;
  const financialData = [
    { name: 'Approved', amount: approved },
    { name: 'Spent', amount: spent },
    { name: 'Remaining', amount: Math.max(remaining, 0) },
  ];
  const checks = explanation?.recommended_verification || ['Approval papers', 'Bills and payment records', 'Completion proof', 'Site photographs'];
  return <><section className="panel project-intro-panel"><div className="eyebrow">PROJECT AT A GLANCE</div><div className="project-intro-grid"><div><h2>{title}</h2><p className="project-description">This is a {project.category || 'public'} project being carried out in {project.district || 'the recorded district'}, {project.state || 'the recorded state'}. It falls under {project.constituency || 'the recorded constituency'} and is linked to {project.mp_name || 'the recorded MP'}.</p><p className="project-description">The review team should confirm that the approved work, spending, supplier, progress, and completion evidence all describe the same project.</p></div><div className="project-facts"><div><span>Project number</span><strong>{project.project_code || `PROJECT-${project.id}`}</strong></div><div><span>Sector</span><strong>{project.category || 'Not recorded'}</strong></div><div><span>State</span><strong>{project.state || 'Not recorded'}</strong></div><div><span>District</span><strong>{project.district || 'Not recorded'}</strong></div><div><span>Constituency</span><strong>{project.constituency || 'Not recorded'}</strong></div><div><span>MP</span><strong>{project.mp_name || 'Not recorded'}</strong></div><div><span>Supplier</span><strong>{project.vendor_name || 'Not recorded'}</strong></div><div><span>Implementing office</span><strong>{project.agency || 'Not recorded'}</strong></div></div></div></section><div className="project-insight-grid"><section className="panel chart-panel"><div className="eyebrow">MONEY BREAKDOWN</div><h2>Approved, spent, and remaining</h2><ResponsiveContainer width="100%" height={220}><BarChart data={financialData} margin={{ left: 10, right: 10, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="name" tick={{ fill: '#65736e', fontSize: 11 }} /><YAxis tick={{ fill: '#65736e', fontSize: 11 }} tickFormatter={value => `₹${Math.round(Number(value) / 100000)}L`} /><Tooltip formatter={(value: any) => [money(Number(value)), 'Amount']} /><Bar dataKey="amount" fill="#238f82" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer><table className="detail-table"><tbody><tr><th>Approved amount</th><td>{money(approved)}</td></tr><tr><th>Spent so far</th><td>{money(spent)}</td></tr><tr><th>Amount left</th><td>{remaining >= 0 ? money(remaining) : 'Overspent by ' + money(Math.abs(remaining))}</td></tr><tr><th>Use of approved amount</th><td>{pct(project.utilization_ratio)}</td></tr></tbody></table></section><section className="panel"><div className="eyebrow">AUDITOR'S CHECKLIST</div><h2>What to look for</h2><div className="audit-checklist">{checks.slice(0, 6).map((item: string, index: number) => <div key={item}><span>{index + 1}</span><div><strong>{item}</strong><small>Confirm this record matches the project number, location, amount, and dates.</small></div></div>)}</div></section></div></>;
}

function ProjectDetailPage() { 
  const { id } = useParams(); 
  const location = useLocation(); const runId = new URLSearchParams(location.search).get('run_id');
  const [project, setProject] = useState<Project | null>(null); 
  const [modal, setModal] = useState(false); 
  const [saved, setSaved] = useState(''); 
  const [authority, setAuthority] = useState('District audit officer'); 
  const [notes, setNotes] = useState(''); 
  const [explanation, setExplanation] = useState<any>(null);
  const [similar, setSimilar] = useState<any[]>([]);
  const [auditFile, setAuditFile] = useState<any>(null);
  const [compliance, setCompliance] = useState<any[]>([]);
  const [fraudRisk, setFraudRisk] = useState<any>(null);
  const [fraudDisposition, setFraudDisposition] = useState('Requires Evidence');
  const [fraudReason, setFraudReason] = useState('');
  const [fraudEvidence, setFraudEvidence] = useState('');
  const [loadError, setLoadError] = useState('');
  const params = { run_id: runId || undefined };
  const reloadAuditFile = async () => setAuditFile((await axios.get(`${API_BASE}/api/projects/${id}/audit-file`, { params })).data);
  useEffect(() => { 
    Promise.all([axios.get(`${API_BASE}/api/projects/${id}`, { params }), axios.get(`${API_BASE}/api/projects/${id}/explanation`, { params }), axios.get(`${API_BASE}/api/projects/${id}/similar`, { params }), axios.get(`${API_BASE}/api/projects/${id}/audit-file`, { params }), axios.get(`${API_BASE}/api/projects/${id}/compliance`, { params }), axios.get(`${API_BASE}/api/projects/${id}/fraud-risk`, { params })]).then(([projectResponse, explanationResponse, similarResponse, auditResponse, complianceResponse, fraudResponse]) => { setProject(projectResponse.data); setExplanation(explanationResponse.data); setSimilar(similarResponse.data.items || []); setAuditFile(auditResponse.data); setCompliance(complianceResponse.data.items || []); setFraudRisk(fraudResponse.data); }).catch(error => setLoadError(error instanceof Error ? error.message : 'Unable to load this project.'));
  }, [id, runId]);
  if (loadError) return <div className="page-stack"><section className="panel"><h2>Unable to open this project</h2><p>{loadError}</p><Link className="text-link" to="/projects">Return to projects</Link></section></div>;
  if (!project) return <div className="page-loading">Loading investigation workspace...</div>; 
  const createCase = async () => { 
    await axios.post(`${API_BASE}/api/audit-cases`, { project_id: project.id, title: `Review: ${project.project_name}`, priority: project.risk_level === 'CRITICAL' ? 'CRITICAL' : 'HIGH', assigned_authority: authority, notes }); 
    setSaved('Audit case created and assigned'); 
    setModal(false); 
  }; 
  const markReviewed = async () => { await axios.patch(`${API_BASE}/api/projects/${project.id}/audit-status`, { status: 'Under Review' }); await reloadAuditFile(); setSaved('Project review status saved'); };
  const toggleChecklist = async (item: string, completed: boolean) => { await axios.post(`${API_BASE}/api/projects/${project.id}/documents/checklist`, { item, completed }); await reloadAuditFile(); };
  const reviewFraudSignal = async (signalCode: string) => { await axios.post(`${API_BASE}/api/projects/${project.id}/fraud-risk/reviews`, { signal_code: signalCode, disposition: fraudDisposition, decision_reason: fraudReason, evidence_reference: fraudEvidence }, { params }); const refreshed = await axios.get(`${API_BASE}/api/projects/${project.id}/fraud-risk`, { params }); setFraudRisk(refreshed.data); setSaved('Fraud-risk signal review saved'); };
  const components = project.signal_components || {}; 
  const isCalamity = project.category === 'Calamity Relief' || project.calamity_type; 
  const level = reviewLevel(project);
  const utilization = Number(project.utilization_ratio || 0);
  const signalRows = [
    ['Use of funds', utilization],
    ['Delay', components.delay_score_component ?? 0],
    ['Cost increase', components.cost_overrun_score_component ?? 0],
    ['Comparison with similar works', components.peer_deviation_score_component ?? 0],
    ['Repeated record check', components.duplicate_score_component ?? 0],
    ['Missing information', components.data_quality_score_component ?? 0],
  ];
  const signalPercent = (value: unknown) => {
    const numeric = Number(value || 0);
    return `${(numeric * 100).toFixed(1)}%`;
  };
  return <div className="page-stack">
    <div className="page-actions"><Link className="text-link" to="/projects">← Back to projects</Link><div className="action-row"><button className="button secondary" onClick={() => downloadProjectReport(project, explanation, similar)}>Download project report</button><button className="button secondary" onClick={() => setModal(true)}>Create review case</button><button className="button primary" onClick={markReviewed}>Mark reviewed</button></div></div>
    {saved && <div className="notice">{saved}</div>}
    <section className="panel project-header">
      <div className="eyebrow">PROJECT REPORT · {project.project_code || `PROJECT-${project.id}`}</div>
      <h1>{projectTitle(project)}</h1>
      <p>{[project.state, project.district, project.constituency, project.category, project.mp_name && `MP: ${project.mp_name}`].filter(Boolean).join(' · ')}</p>
      <div className="risk-summary"><div><span>Review level</span><strong>{typeof project.risk_score === 'number' ? `${project.risk_score.toFixed(1)}%` : '—'}</strong></div><span className={`badge ${level.toLowerCase()}`}>{level}</span></div>
    </section>
    <ProjectOverview project={project} explanation={explanation} />
    <section className="panel"><div className="eyebrow">POTENTIAL FRAUD-RISK SIGNALS</div><h2>Evidence requiring review</h2><p className="muted">{fraudRisk?.disclaimer || 'Loading review signals…'}</p>{fraudRisk?.signals?.length ? <><div className="toolbar"><select value={fraudDisposition} onChange={event => setFraudDisposition(event.target.value)}><option>Requires Evidence</option><option>Cleared</option><option>Escalated</option><option>Irregularity Confirmed</option><option>Referred for Investigation</option><option>False Positive</option></select><input placeholder="Decision reason" value={fraudReason} onChange={event => setFraudReason(event.target.value)} /><input placeholder="Evidence reference" value={fraudEvidence} onChange={event => setFraudEvidence(event.target.value)} /></div><ul className="plain-list">{fraudRisk.signals.map((item: any, index: number) => <li key={`${item.signal_code}-${index}`}><strong>{item.title}</strong> ({item.severity}, {Math.round(item.confidence * 100)}%) — {item.explanation}<small>{item.recommended_verification}</small><button className="button ghost" type="button" onClick={() => reviewFraudSignal(item.signal_code)}>Save review disposition</button></li>)}</ul></> : <EmptyState title="No potential fraud-risk signals" text="No deterministic indicator was available for this project." />}</section>
    <section className="panel"><div className="eyebrow">PROJECT COMPLIANCE</div><h2>Review findings</h2><p className="muted">Each item is a human-review signal, not a confirmed finding.</p>{compliance.length ? <ul className="plain-list">{compliance.map((item, index) => <li key={`${item.rule_code}-${index}`}><strong>{item.title}</strong> ({item.severity}) — {item.explanation}<small>{item.recommended_action}</small></li>)}</ul> : <EmptyState title="No compliance findings" text="No deterministic compliance issue was available for this project." />}</section>
    <section className="panel"><div className="eyebrow">WHY THIS PROJECT NEEDS A CLOSER LOOK</div><h2>Things to check</h2><p className="muted">Audit status: {auditFile?.audit_status || 'Not Reviewed'}</p><ul className="plain-list">{(explanation?.why_flagged || project.reasons || ['No specific issue recorded.']).map((reason: string) => <li key={reason}>{reason}</li>)}</ul><h3>Records to request</h3><ul className="plain-list">{(explanation?.recommended_verification || ['Approval papers', 'Bills and payment records', 'Completion proof']).map((item: string) => { const completed = Boolean(auditFile?.checklist?.find((entry: any) => entry.item === item)?.completed); return <li key={item}><label><input type="checkbox" checked={completed} onChange={event => toggleChecklist(item, event.target.checked)} /> {item}</label></li>; })}</ul></section>
    <section className="panel progress-panel"><div className="eyebrow">PROJECT PROGRESS</div><h2>Timeline and checks</h2><div className="metric-grid">{signalRows.map(([label, value]) => <div className="metric-card" key={label}><span>{label}</span><strong>{signalPercent(value)}</strong><div className="metric-bar"><i style={{ width: `${Math.min(100, Number(value || 0) * 100)}%` }} /></div></div>)}</div><p className="muted">{project.delay_days ? `${Math.round(project.delay_days)} days recorded between planned and actual completion.` : 'No delay recorded in the uploaded dates.'}</p></section>
    <section className="panel comparable-panel"><div className="eyebrow">COMPARABLE PROJECTS</div><h2>Other works to compare</h2><div className="similar-list">{similar.length ? similar.slice(0, 10).map(item => <Link className="similar-item" to={`/projects/${item.id}${runId ? `?run_id=${encodeURIComponent(runId)}` : ''}`} key={item.id}><strong>{item.project_code || item.id}</strong><span>{projectTitle(item)}</span><span>{money(item.expenditure)} <b>{item.risk_level || reviewLevel(item)}</b></span></Link>) : <p className="muted">No comparable projects found.</p>}</div></section>
    {modal && <div className="modal-backdrop"><section className="modal panel"><button className="modal-close" onClick={() => setModal(false)}>×</button><h2>Create review case</h2><label>Responsible officer<input value={authority} onChange={event => setAuthority(event.target.value)} /></label><label>Notes<textarea value={notes} onChange={event => setNotes(event.target.value)} /></label><button className="button primary" onClick={createCase}>Save review case</button></section></div>}
  </div>;
}

function UploadPage() { 
  const [file, setFile] = useState<File | null>(null); 
  const [status, setStatus] = useState('Upload'); 
  const [result, setResult] = useState<any>(null); 
  const stages = ['Upload', 'Map', 'Validate', 'Analyze', 'Results']; 
  const submit = async (event: FormEvent) => { 
    event.preventDefault(); 
    if (!file) return; 
    const form = new FormData(); 
    form.append('file', file); 
    try { 
      setStatus('Validate'); 
      const validation = await axios.post(`${API_BASE}/api/validate`, form); 
      setResult(validation.data); 
      if (!validation.data.valid) { 
        setStatus('Map'); 
        return; 
      } 
      setStatus('Analyze'); 
      const analysis = await axios.post(`${API_BASE}/api/analyze`, form); 
      setResult({ ...validation.data, ...analysis.data }); 
      setStatus('Results'); 
    } catch (error: any) { 
      setStatus('Results'); 
      setResult({ error: error.response?.data?.detail || 'Analysis failed' }); 
    } 
  }; 
  return <div className="page-stack"><PageTitle eyebrow="DATA INGESTION" title="Upload & Analyze" subtitle="Bring a project register into the monitored evidence pipeline." /><section className="panel upload-panel"><div className="stage-line">{stages.map((stage, index) => <div className={cx('stage', stages.indexOf(status) >= index ? 'complete' : '')} key={stage}><span>{String(index + 1).padStart(2, '0')}</span>{stage}</div>)}</div><form onSubmit={submit} className="upload-form"><div className="drop-zone"><div className="upload-symbol">↑</div><h2>Drop a CSV or XLSX register here</h2><p>Schema validation runs before any model analysis.</p><input type="file" accept=".csv,.xlsx,.xls" onChange={event => setFile(event.target.files?.[0] || null)} /><label className="button secondary" htmlFor="file-picker">Choose dataset</label></div><input id="file-picker" type="file" accept=".csv,.xlsx,.xls" onChange={event => setFile(event.target.files?.[0] || null)} hidden /><div className="upload-side"><div className="eyebrow">SELECTED FILE</div><strong>{file?.name || 'No file selected'}</strong><span>{file ? `${(file.size / 1024).toFixed(1)} KB ready` : 'Supported: CSV, XLSX'}</span><button className="button primary" type="submit" disabled={!file}>Run analysis</button></div></form>{result && <div className="result-panel"><div><div className="eyebrow">ANALYSIS {status.toUpperCase()}</div><h2>{result.error ? 'Validation requires attention' : 'Analysis complete'}</h2></div><div className="result-stats"><span><strong>{result.total_projects || result.rows || 0}</strong> projects</span><span><strong>{result.high_risk_count || 0}</strong> high risk</span><span><strong>{result.critical_count || 0}</strong> critical</span><span><strong>{result.alerts_created || 0}</strong> alerts</span></div><pre>{JSON.stringify(result, null, 2)}</pre></div>}</section></div>; 
}

function AlertsPage() { 
  const [alerts, setAlerts] = useState<Alert[]>([]); 
  useEffect(() => { 
    axios.get(`${API_BASE}/api/alerts`).then(response => setAlerts(response.data.items)); 
  }, []); 
  return <div className="page-stack"><PageTitle eyebrow="PROJECTS TO CHECK" title="Review reminders" subtitle="These reminders point to records that may need a closer look." /><div className="alert-summary">{['CRITICAL', 'HIGH', 'MEDIUM'].map(level => <div key={level}><RiskBadge level={level} /><strong>{alerts.filter(alert => alert.severity === level).length}</strong><span>open reminders</span></div>)}</div><section className="panel alert-panel">{alerts.length ? <div className="alert-list">{alerts.map(alert => <div className="alert-row" key={alert.id}><RiskBadge level={alert.severity} /><div><strong>{alert.project_name}</strong><span>{alert.state} · {alert.district}</span></div><p>{alert.message}</p><Link to={`/projects/${alert.project_id}`} className="text-link">Open project →</Link></div>)}</div> : <EmptyState title="No reminders" text="There are no project records needing extra attention right now." />}</section></div>; 
}

function CasesPage() { 
  const [cases, setCases] = useState<AuditCase[]>([]); 
  const refresh = () => { 
    axios.get(`${API_BASE}/api/audit-cases`).then(response => setCases(response.data.items)); 
  }; 
  useEffect(() => { 
    refresh(); 
  }, []); 
  const update = async (id: number, status: string) => { 
    await axios.patch(`${API_BASE}/api/audit-cases/${id}`, { status }); 
    refresh(); 
  }; 
  return <div className="page-stack"><PageTitle eyebrow="CASE MANAGEMENT" title="Audit Cases" subtitle="Track human review from open signal to resolution." /><div className="case-summary">{['OPEN', 'UNDER_REVIEW', 'ESCALATED', 'RESOLVED'].map(status => <div key={status}><span>{status.replace('_', ' ')}</span><strong>{cases.filter(item => item.status === status || (status === 'OPEN' && item.status === 'Pending Review')).length}</strong></div>)}</div><section className="panel table-panel"><div className="table-scroll"><table className="data-table"><thead><tr><th>Case</th><th>Project</th><th>Priority</th><th>Assigned</th><th>Status</th><th>Created</th></tr></thead><tbody>{cases.length ? cases.map(item => <tr key={item.id}><td><strong>CASE-{String(item.id).padStart(4, '0')}</strong><small>{item.title}</small></td><td>{item.project_id}</td><td><RiskBadge level={item.priority === 'CRITICAL' ? 'CRITICAL' : item.priority === 'HIGH' ? 'HIGH' : 'MEDIUM'} /></td><td>{item.assigned_authority || 'Unassigned'}</td><td><select className="inline-select" value={item.status} onChange={event => update(item.id, event.target.value)}><option>OPEN</option><option>UNDER_REVIEW</option><option>ESCALATED</option><option>RESOLVED</option><option>Pending Review</option></select></td><td>{dateText(item.created_at)}</td></tr>) : <tr><td colSpan={6}><EmptyState title="No audit cases yet" text="Create a case from any project investigation workspace." /></td></tr>}</tbody></table></div></section></div>; 
}

function LoginPage() {
  const { user, login, demoEnvironment } = useAuth();
  const navigate = useNavigate();
  const [role, setRole] = useState<Role>('MINISTRY');
  const [form, setForm] = useState<Record<string, string>>({ role: 'MINISTRY' });
  const [error, setError] = useState('');
  useEffect(() => { if (user) navigate('/', { replace: true }); }, [user, navigate]);
  const set = (key: string, value: string) => setForm(previous => ({ ...previous, [key]: value, role }));
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError('');
    try { await login({ ...form, role }); navigate('/'); } catch (err: any) { setError(err.response?.data?.detail || 'Unable to sign in.'); }
  };
  const fields = role === 'MINISTRY' ? [] : role === 'STATE_NODAL_AUTHORITY' ? ['state'] : role === 'DISTRICT_AUTHORITY' ? ['state', 'district'] : ['state', 'constituency'];
  return <div className="auth-page"><section className="auth-card panel"><div className="brand"><div className="brand-seal">M</div><div><div className="brand-kicker">MPLADS AI</div><div className="brand-title">Audit Intelligence</div></div></div><div className="eyebrow auth-eyebrow">INTERNAL GOVERNMENT ACCESS</div><h1>Sign in to the monitoring workspace</h1><p className="auth-subtitle">Select your official authority pathway. Your provisioned account and jurisdiction are verified by the server.</p><label>Official role<select value={role} onChange={event => { const next = event.target.value as Role; setRole(next); setForm({ role: next }); }}><option value="MINISTRY">Ministry</option><option value="STATE_NODAL_AUTHORITY">State Nodal Authority</option><option value="DISTRICT_AUTHORITY">District Authority</option><option value="MEMBER_OF_PARLIAMENT">Member of Parliament</option></select></label><form onSubmit={submit}><label>Official Government Email / User ID<input required value={form.login || ''} onChange={event => set('login', event.target.value)} placeholder="Provisioned user ID" /></label><label>{role === 'MINISTRY' ? 'Ministry Identity ID' : role === 'MEMBER_OF_PARLIAMENT' ? 'MP Identity ID' : 'Authority / Employee Identity ID'}<input required value={form.identity_id || ''} onChange={event => set('identity_id', event.target.value)} /></label>{fields.map(field => <label key={field}>{field === 'state' ? 'State' : field === 'district' ? 'District' : 'Parliamentary Constituency'}<input required value={form[field] || ''} onChange={event => set(field, event.target.value)} placeholder={`Assigned ${field}`} /></label>)}<label>Password<input required type="password" value={form.password || ''} onChange={event => set('password', event.target.value)} /></label>{error && <div className="auth-error">{error}</div>}<button className="button primary auth-submit" type="submit">Sign in securely</button></form>{demoEnvironment && <div className="notice demo-notice"><strong>Demo Environment</strong><span>Use provisioned demo accounts configured by the operator.</span></div>}<small className="auth-footnote">No public registration. Access is provisioned by authorized authorities.</small></section></div>;
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Checking secure session...</div>;
  return user ? <>{children}</> : <LoginPage />;
}

function AuditIntegrityPanel() {
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const verify = async () => {
    setBusy(true);
    try {
      setResult((await axios.get(`${API_BASE}/api/auth/audit-log/integrity`)).data);
    } catch (error: any) {
      setResult({ error: error.response?.data?.detail || 'Unable to verify audit log integrity.' });
    } finally {
      setBusy(false);
    }
  };
  return <section className="panel"><div className="panel-head"><div><div className="eyebrow">SECURITY VERIFICATION</div><h2>Audit Log Integrity</h2><p>Check whether hash-chained audit records remain consistent.</p></div><button className="button secondary" type="button" onClick={verify} disabled={busy}>{busy ? 'Checking...' : 'Verify now'}</button></div>{result && (result.error ? <div className="auth-error">{result.error}</div> : <div className="result-stats"><span><strong>{result.status}</strong> status</span><span><strong>{result.verified_records}</strong> of {result.total_records} records checked</span>{result.first_failure && <span>First issue: <strong>#{result.first_failure.audit_log_id}</strong> {result.first_failure.reason}</span>}</div>)}</section>;
}

function UserManagementContent() {
  const { can, user } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [draft, setDraft] = useState({ name: '', email: '', identity_id: '', role: user?.role === 'STATE_NODAL_AUTHORITY' ? 'DISTRICT_AUTHORITY' : 'STATE_NODAL_AUTHORITY', state: user?.scope_id || '', scope_id: '', temporary_password: '' });
  const refresh = () => axios.get(`${API_BASE}/api/auth/users`).then(response => setUsers(response.data.items)).catch(() => setMessage('Unable to load provisioned accounts.'));
  useEffect(() => { if (can('users:manage')) refresh(); }, [can]);
  const activate = async (id: number) => { await axios.patch(`${API_BASE}/api/auth/users/${id}`, { status: 'ACTIVE' }); refresh(); };
  const create = async (event: FormEvent) => { event.preventDefault(); setMessage(''); try { await axios.post(`${API_BASE}/api/auth/users`, draft); setMessage('Account created in Pending Activation status.'); setDraft(previous => ({ ...previous, name: '', email: '', identity_id: '', scope_id: '', temporary_password: '' })); refresh(); } catch (error: any) { setMessage(error.response?.data?.detail || 'Unable to create account.'); } };
  const allowedRoles = user?.role === 'STATE_NODAL_AUTHORITY' ? ['DISTRICT_AUTHORITY', 'MEMBER_OF_PARLIAMENT'] : ['MINISTRY', 'STATE_NODAL_AUTHORITY', 'DISTRICT_AUTHORITY', 'MEMBER_OF_PARLIAMENT'];
  const scopeLabel = draft.role === 'MEMBER_OF_PARLIAMENT' ? 'Parliamentary constituency or project district' : draft.role === 'DISTRICT_AUTHORITY' ? 'Assigned district' : 'Assigned state';
  return <div className="page-stack"><PageTitle eyebrow="ACCESS GOVERNANCE" title="User Management" subtitle="Provisioned internal accounts and jurisdiction assignments." /><section className="panel"><div className="panel-head"><div><h2>Provision an account</h2><p>The server assigns role and scope; new accounts require activation.</p></div></div><form className="provision-form" onSubmit={create}><label>Name<input required value={draft.name} onChange={event => setDraft({ ...draft, name: event.target.value })} /></label><label>Official user ID / email<input required value={draft.email} onChange={event => setDraft({ ...draft, email: event.target.value })} /></label><label>Identity ID<input required value={draft.identity_id} onChange={event => setDraft({ ...draft, identity_id: event.target.value })} /></label><label>Role<select value={draft.role} onChange={event => setDraft({ ...draft, role: event.target.value })}>{allowedRoles.map(role => <option key={role} value={role}>{roleTitles[role as Role]}</option>)}</select></label><label>State<input required={draft.role !== 'MINISTRY'} value={draft.state} onChange={event => setDraft({ ...draft, state: event.target.value })} /></label><label>{scopeLabel}<input required={draft.role !== 'MINISTRY' && draft.role !== 'STATE_NODAL_AUTHORITY'} value={draft.scope_id} onChange={event => setDraft({ ...draft, scope_id: event.target.value })} /></label><label>Temporary password<input required type="password" value={draft.temporary_password} onChange={event => setDraft({ ...draft, temporary_password: event.target.value })} /></label><button className="button primary" type="submit">Create pending account</button></form>{message && <div className="auth-error">{message}</div>}</section><section className="panel"><div className="panel-head"><div><h2>Authorized accounts</h2><p>Accounts are created with a server-side role and scope. There is no public registration.</p></div></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Name</th><th>Role</th><th>Scope</th><th>Status</th><th /></tr></thead><tbody>{users.map(account => <tr key={account.id}><td><strong>{account.name}</strong><small>{account.email}</small></td><td>{roleTitles[account.role as Role]}</td><td>{account.scope_id || 'National'}</td><td>{account.status}</td><td>{account.status === 'PENDING_ACTIVATION' && <button className="button secondary" onClick={() => activate(account.id)}>Activate</button>}</td></tr>)}</tbody></table></div></section></div>;
}

function UserManagementPage() {
  const { can } = useAuth();
  return <><UserManagementContent />{can('audit:integrity') && <AuditIntegrityPanel />}</>;
}

function ProjectsPage() { const params = new URLSearchParams(useLocation().search); const [projects, setProjects] = useState<Project[]>([]); const [query, setQuery] = useState(params.get('search') || ''); const [page, setPage] = useState(1); const [total, setTotal] = useState(0); const pageSize = 500; useEffect(() => { axios.get(`${API_BASE}/api/projects`, { params: { page, page_size: pageSize, search: query || undefined } }).then(response => { setProjects(response.data.records || response.data.items || []); setTotal(response.data.filtered_count ?? response.data.total_count ?? response.data.total ?? 0); }); }, [query, page]); useEffect(() => setPage(1), [query]); const pages = Math.max(1, Math.ceil(total / pageSize)); return <div className="page-stack"><PageTitle eyebrow="PROJECT REGISTER" title="Projects" subtitle="Search the complete analyzed register across location, constituency, and category." /><div className="toolbar"><div className="table-search">⌕<input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search project, ID, state, district..." /></div><span className="toolbar-count">{total.toLocaleString('en-IN')} matching projects</span></div><section className="panel table-panel"><ProjectTable projects={projects} /><div className="pagination"><button className="button ghost" disabled={page === 1} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page} of {pages} · {pageSize} per page</span><button className="button ghost" disabled={page >= pages} onClick={() => setPage(value => value + 1)}>Next</button></div></section></div>; }
function AnalyticsPage() { const [dashboard, setDashboard] = useState<Dashboard | null>(null); useEffect(() => { axios.get(`${API_BASE}/api/dashboard`).then(response => setDashboard(response.data)); }, []); if (!dashboard) return <div className="page-loading">Loading analytics...</div>; const stateData = (dashboard.state_wise || []).slice(0, 12); const categoryData = (dashboard.category_wise || []).slice(0, 9); return <div className="page-stack"><PageTitle eyebrow="ANALYTICS" title="Evidence patterns" subtitle="Understand where expenditure, utilization, and completion signals diverge." /><div className="analytics-kpis"><Stat label="Records analyzed" value={dashboard.total_projects.toLocaleString('en-IN')} detail="Uploaded project records" /><Stat label="Overall utilization" value={pct(dashboard.total_utilization_ratio)} detail={money(dashboard.total_expenditure)} tone="blue" /><Stat label="High-risk share" value={pct(dashboard.total_projects ? (dashboard.high_risk_projects / dashboard.total_projects) : 0)} detail={`${dashboard.high_risk_projects} high or critical`} tone="orange" /><Stat label="Open alerts" value={dashboard.active_alerts.toLocaleString('en-IN')} detail="Signals requiring review" tone="red" /></div><div className="grid-2"><section className="panel chart-panel"><div className="eyebrow">RISK SCORE DISTRIBUTION</div><h2>How many projects sit in each band?</h2><ResponsiveContainer width="100%" height={300}><BarChart data={dashboard.risk_score_distribution}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="range" /><YAxis /><Tooltip /><Bar dataKey="projects" fill="#238f82" /></BarChart></ResponsiveContainer></section><section className="panel chart-panel"><div className="eyebrow">UTILIZATION DISTRIBUTION</div><h2>Where is spend approaching sanction?</h2><ResponsiveContainer width="100%" height={300}><BarChart data={dashboard.utilization_distribution}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="range" /><YAxis /><Tooltip /><Bar dataKey="projects" fill="#d6a64f" /></BarChart></ResponsiveContainer></section><section className="panel chart-panel"><div className="eyebrow">RISK BY STATE</div><h2>Where is average risk concentrated?</h2><ResponsiveContainer width="100%" height={300}><BarChart data={stateData} margin={{ bottom: 48, left: 8 }}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="name" angle={-30} textAnchor="end" interval={0} height={65} /><YAxis domain={[0, 100]} /><Tooltip formatter={(value: any) => [`${Number(value).toFixed(1)}%`, 'Average risk']} /><Bar dataKey="average_risk" fill="#d95b67" /></BarChart></ResponsiveContainer></section><section className="panel chart-panel"><div className="eyebrow">DELAY PROFILE</div><h2>How long are projects delayed?</h2><ResponsiveContainer width="100%" height={300}><BarChart data={dashboard.delay_distribution}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="range" angle={-20} textAnchor="end" interval={0} height={58} /><YAxis /><Tooltip /><Bar dataKey="projects" fill="#e4774c" /></BarChart></ResponsiveContainer></section><section className="panel chart-panel wide-chart"><div className="eyebrow">CATEGORY FINANCIALS</div><h2>Sanctioned value versus expenditure</h2><ResponsiveContainer width="100%" height={320}><BarChart data={categoryData} margin={{ bottom: 48, left: 8 }}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="name" angle={-25} textAnchor="end" interval={0} height={70} /><YAxis tickFormatter={(value) => `${(Number(value) / 1000000).toFixed(0)}M`} /><Tooltip formatter={(value: any) => money(Number(value))} /><Bar dataKey="sanctioned" fill="#238f82" name="Sanctioned" /><Bar dataKey="expenditure" fill="#d6a64f" name="Expenditure" /></BarChart></ResponsiveContainer></section><section className="panel chart-panel wide-chart"><div className="eyebrow">STATE PROJECT VOLUME</div><h2>Project count and high-risk cases</h2><ResponsiveContainer width="100%" height={320}><BarChart data={stateData} margin={{ bottom: 48, left: 8 }}><CartesianGrid strokeDasharray="3 3" stroke="#dbe5e1" vertical={false} /><XAxis dataKey="name" angle={-30} textAnchor="end" interval={0} height={65} /><YAxis /><Tooltip /><Bar dataKey="projects" fill="#4b8ca3" name="Projects" /><Bar dataKey="high_risk" fill="#d95b67" name="High risk" /></BarChart></ResponsiveContainer></section></div></div>; }
function DataQualityPage() { const [projects, setProjects] = useState<Project[]>([]); const [quality, setQuality] = useState<any>(null); useEffect(() => { Promise.all([axios.get(`${API_BASE}/api/projects`, { params: { page: 1, page_size: 20, risk_level: 'DATA_QUALITY_REVIEW' } }), axios.get(`${API_BASE}/api/data-quality`)]).then(([projectResponse, qualityResponse]) => { setProjects(projectResponse.data.records || projectResponse.data.items || []); setQuality(qualityResponse.data); }); }, []); if (!quality) return <div className="page-loading">Loading data quality...</div>; return <div className="page-stack"><PageTitle eyebrow="DATA QUALITY" title="Evidence quality" subtitle="Inspect records that may need clarification before audit interpretation." /><div className="kpi-grid quality"><Stat label="Records analyzed" value={quality.total_records.toLocaleString('en-IN')} /><Stat label="Completeness" value={pct(quality.completeness)} detail={`${quality.total_records - quality.data_quality_records} records without review flags`} tone="blue" /><Stat label="Validity" value={pct(quality.validity)} detail={`${quality.data_quality_records} review records`} tone="orange" /><Stat label="Uniqueness" value={pct(quality.uniqueness)} detail={`${quality.duplicate_project_ids} duplicate IDs`} tone="red" /></div><section className="panel"><div className="eyebrow">REVIEW QUEUE</div><h2>Records needing context</h2><ProjectTable projects={projects} /></section></div>; }
function IntelligenceTable({ records }: { records: Project[] }) { return <ProjectTable projects={records} />; }
function AgenciesPage() { const [items, setItems] = useState<any[]>([]); const [vendors, setVendors] = useState<any[]>([]); const location = useLocation(); const runId = new URLSearchParams(location.search).get('run_id'); const params = { run_id: runId || undefined }; useEffect(() => { Promise.all([axios.get(`${API_BASE}/api/agencies`, { params }), axios.get(`${API_BASE}/api/fraud-risk/vendors`, { params })]).then(([agencyResponse, vendorResponse]) => { setItems(agencyResponse.data.items || []); setVendors(vendorResponse.data.items || []); }); }, [runId]); return <div className="page-stack"><PageTitle eyebrow="AGENCY INTELLIGENCE" title="Implementation performance" subtitle="Aggregated from the selected analysis run." /><section className="panel table-panel"><div className="table-scroll"><table className="data-table"><thead><tr><th>Agency</th><th>Projects</th><th>Sanctioned</th><th>Expenditure</th><th>Utilization</th><th>Delayed</th><th>High risk</th><th>Average risk</th></tr></thead><tbody>{items.map(item => <tr key={item.name}><td><strong>{item.name}</strong></td><td>{item.projects}</td><td>{money(item.sanctioned)}</td><td>{money(item.expenditure)}</td><td>{pct(item.average_utilization)}</td><td>{item.delayed}</td><td>{item.high_risk + item.critical}</td><td>{Number(item.average_risk || 0).toFixed(1)}</td></tr>)}</tbody></table></div></section><section className="panel table-panel"><div className="eyebrow">POTENTIAL VENDOR-RISK SIGNALS</div><h2>Vendor concentration requiring review</h2><p className="muted">Aggregates are review signals and are not proof of wrongdoing.</p><div className="table-scroll"><table className="data-table"><thead><tr><th>Vendor</th><th>Projects</th><th>Concentration</th><th>Districts</th><th>Agencies</th><th>High/Critical</th><th>Anomalies</th></tr></thead><tbody>{vendors.length ? vendors.slice(0, 20).map(item => <tr key={item.vendor}><td><strong>{item.vendor}</strong></td><td>{item.projects}</td><td>{item.concentration_percentage}%</td><td>{item.district_count}</td><td>{item.agency_count}</td><td>{item.high_risk_count}/{item.critical_count}</td><td>{item.anomaly_count}</td></tr>) : <tr><td colSpan={7}><EmptyState title="No vendor signals" text="No vendor records were available for this analysis run." /></td></tr>}</tbody></table></div></section></div>; }
function ReconciliationPage() { const [data, setData] = useState<any>(null); useEffect(() => { axios.get(`${API_BASE}/api/reconciliation`).then(response => setData(response.data)); }, []); if (!data) return <div className="page-loading">Loading fund checks...</div>; return <div className="page-stack"><PageTitle eyebrow="FUND CHECKS" title="Check the money figures" subtitle="These projects show a difference between the approved amount and the amount spent." /><div className="kpi-grid"><Stat label="Projects to check" value={String(data.total_mismatches)} tone="red" /><Stat label="Figures available" value={String(data.available_fields.length)} /><Stat label="Figures not supplied" value={String(data.unavailable_fields.length)} tone="orange" /></div><section className="panel table-panel"><h2>Projects with spending above approval</h2><IntelligenceTable records={(data.mismatches || []).map((item: any) => ({ ...item, project_name: item.project_name || item.project_code, project_code: item.project_code, state: item.state || 'Not recorded', district: item.district || 'Not recorded', category: item.category || 'Not recorded', utilization_ratio: item.utilization_ratio, delay_days: item.delay_days, anomaly_score: item.anomaly_score, risk_level: item.risk_level || 'HIGH', id: item.project_id }))} /></section></div>; }
function DuplicatesPage() { const [items, setItems] = useState<any[]>([]); useEffect(() => { axios.get(`${API_BASE}/api/duplicates`).then(response => setItems(response.data.items || [])); }, []); return <div className="page-stack"><PageTitle eyebrow="DUPLICATE WORK DETECTION" title="Potential duplicate candidates" subtitle="Similarity signals require human verification; projects are never merged automatically." /><section className="panel">{items.length ? items.map((item, index) => <div className="alert-row" key={`${item.project_a.id}-${item.project_b.id}`}><div><strong>#{index + 1}</strong><span>{item.similarity}% similarity</span></div><div><strong>{item.project_a.code}</strong><span>{item.project_a.name}</span></div><div><strong>{item.project_b.code}</strong><span>{item.project_b.name}</span><p>{item.reasons.join(' · ')}</p></div><RiskBadge level="MEDIUM" /></div>) : <EmptyState title="No potential duplicates" text="No high-similarity project pairs were found in the active run." />}</section></div>; }
function AuditCopilotPage() { const [question, setQuestion] = useState(''); const [result, setResult] = useState<any>(null); const search = async (event: FormEvent) => { event.preventDefault(); if (question.trim()) setResult((await axios.post(`${API_BASE}/api/audit-search`, { query: question })).data); }; return <div className="page-stack"><PageTitle eyebrow="SEARCH PROJECTS" title="Ask about your projects" subtitle="Type a project name, place, category, or a simple question." /><section className="panel"><form className="copilot-form" onSubmit={search}><input value={question} onChange={event => setQuestion(event.target.value)} placeholder="Show delayed projects in Karnataka above the approved amount" /><button className="button primary">Search projects</button></form>{result && <><div className="integration-note"><strong>YOUR SEARCH</strong><br />{result.interpreted.join(' · ')}<br /><strong>{result.total_count} matching projects</strong></div>{result.records.length ? <IntelligenceTable records={result.records.map((item: any) => ({ ...item, state: item.state || '', district: '', risk_score: item.risk_score, risk_level: item.risk_level }))} /> : <EmptyState title="No matching projects" text="Try a different project name, place, category, or review level." />}</>}</section></div>; }

function App() { return <Routes><Route path="/login" element={<LoginPage />} /><Route path="*" element={<ProtectedRoute><Shell><Routes><Route path="/" element={<DashboardPage />} /><Route path="/risk" element={<RiskPage />} /><Route path="/projects" element={<ProjectsPage />} /><Route path="/projects/:id" element={<ProjectPageBoundary><ProjectDetailPage /></ProjectPageBoundary>} /><Route path="/upload" element={<MultiUploadPage />} /><Route path="/alerts" element={<AlertsPage />} /><Route path="/cases" element={<CasesPage />} /><Route path="/analytics" element={<AnalyticsPage />} /><Route path="/agencies" element={<AgenciesPage />} /><Route path="/reconciliation" element={<ReconciliationPage />} /><Route path="/duplicates" element={<DuplicatesPage />} /><Route path="/audit-search" element={<AuditCopilotPage />} /><Route path="/integration" element={<IntegrationPage />} /><Route path="/data-quality" element={<DataQualityPage />} /><Route path="/users" element={<UserManagementPage />} /></Routes></Shell></ProtectedRoute>} /></Routes>; }
export default App;
