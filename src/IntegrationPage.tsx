import { useEffect, useState } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';
import { API_BASE } from './auth';
const labels: Record<string, string> = { 
  SANCTIONED_WORKS: 'Sanctioned works', 
  COMPLETED_WORKS: 'Completed works', 
  EXPENDITURE: 'Expenditure', 
  MP_ALLOCATION: 'MP allocation', 
  CALAMITY: 'Calamity relief',
  OTHER: 'Needs confirmation' 
};

export default function IntegrationPage() {
  const [run, setRun] = useState<any>(null);
  const location = useLocation();
  const runId = new URLSearchParams(location.search).get('run_id');
  useEffect(() => { const request = runId ? axios.get(`${API_BASE}/api/analysis-runs/${runId}`) : axios.get(`${API_BASE}/api/analysis-runs/active`); request.then(response => setRun(response.data)).catch(() => setRun(null)); }, [runId]);
  if (!run) return <div className="page-stack"><div className="page-heading simple"><div><div className="eyebrow">DATA INTEGRATION</div><h1>Source relationships</h1><p>Loading the latest analysis.</p></div></div></div>;
  const summary = run.summary || {};
  return <div className="page-stack"><div className="page-heading simple"><div><div className="eyebrow">DATA INTEGRATION</div><h1>Source relationships</h1><p>Canonical project records, workbook roles, and join coverage for the latest analysis run.</p></div></div><div className="notice"><strong>Run #{run.id}</strong><span>Every analytical record retains the source datasets that contributed to it.</span><span className="notice-tag">SOURCE LINEAGE</span></div><section className="kpi-grid"><div className="stat-block"><div className="stat-label">Rows processed</div><div className="stat-value">{Number(summary.rows_processed || 0).toLocaleString('en-IN')}</div></div><div className="stat-block"><div className="stat-label">Projects created</div><div className="stat-value">{Number(summary.projects_created || 0).toLocaleString('en-IN')}</div></div><div className="stat-block"><div className="stat-label">Completed matches</div><div className="stat-value">{Number(summary.matched_completed || 0).toLocaleString('en-IN')}</div></div><div className="stat-block"><div className="stat-label">Expenditure matches</div><div className="stat-value">{Number(summary.matched_expenditure || 0).toLocaleString('en-IN')}</div></div><div className="stat-block"><div className="stat-label">Allocation matched</div><div className="stat-value">{Number(summary.allocation_matched || 0).toLocaleString('en-IN')}</div></div><div className="stat-block"><div className="stat-label">Calamity records</div><div className="stat-value">{Number(summary.calamity_count || 0).toLocaleString('en-IN')}</div></div><div className="stat-block"><div className="stat-label">Conflicts</div><div className="stat-value">{Number(summary.conflicts?.length || 0).toLocaleString('en-IN')}</div></div></section><section className="panel"><div className="eyebrow">DATASETS PROCESSED</div><h2>Workbook detection and mapping</h2><div className="dataset-list">{(summary.datasets || []).map((dataset: any) => <div className="dataset-card" key={dataset.filename}><div><strong>{dataset.filename}</strong><span>{dataset.file_type.toUpperCase()} · {dataset.selected_sheet}</span></div><div className="dataset-role"><b>{labels[dataset.detected_role] || dataset.detected_role}</b><span>{Number(dataset.confidence || 0).toFixed(0)}% confidence</span><small>{(dataset.sheets || []).map((sheet: any) => `${sheet.sheet}: ${Number(sheet.rows).toLocaleString('en-IN')} rows`).join(' · ')}</small></div></div>)}</div></section><section className="panel"><div className="eyebrow">INTEGRATION RELATIONSHIP</div><h2>How datasets were joined</h2><p>{summary.relationship || 'No relationship information available'}</p></section>{(summary.conflicts && summary.conflicts.length > 0) && <section className="panel"><div className="eyebrow">CROSS-DATASET CONFLICTS</div><h2>Data quality issues detected</h2><div className="dataset-list">{summary.conflicts.slice(0, 10).map((conflict: any, idx: number) => <div className="dataset-card" key={idx}><div><strong>Project: {conflict.project_id}</strong><span>Field: {conflict.field}</span></div><div className="dataset-role"><span>Source: {conflict.source}</span><small>Existing: {conflict.existing} → Incoming: {conflict.incoming}</small></div></div>)}</div></section>}</div>;
}
