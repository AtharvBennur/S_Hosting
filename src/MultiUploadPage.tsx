import { ChangeEvent, FormEvent, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_BASE || '';
const MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(['.csv', '.xlsx', '.xls']);

type DatasetInfo = {
  filename: string;
  file_type: string;
  detected_role: string;
  confidence: number;
  selected_sheet?: string;
  sheets?: Array<{ sheet: string; rows: number; role: string; confidence: number }>;
  column_mapping?: Array<{ uploaded_column: string; canonical_field: string; confidence: number; status: string }>;
};

type DatasetIntegrity = {
  id: number;
  file_name: string;
  integrity_status: string;
  algorithm: string;
};

type PrivacyResult = {
  privacy_status: string;
  pii_detected: boolean;
  columns: Array<{ column: string; type: string; confidence: string; count: number }>;
};

const roleLabel: Record<string, string> = {
  SANCTIONED_WORKS: 'Sanctioned works',
  COMPLETED_WORKS: 'Completed works',
  EXPENDITURE: 'Expenditure',
  MP_ALLOCATION: 'MP allocation',
  CALAMITY: 'Calamity relief',
  OTHER: 'Needs confirmation',
};

export default function MultiUploadPage() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [inspected, setInspected] = useState<DatasetInfo[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState('Upload');
  const [privacyResults, setPrivacyResults] = useState<Record<string, PrivacyResult>>({});
  const [privacyBusy, setPrivacyBusy] = useState<number | null>(null);
  const stages = ['Upload', 'Detect', 'Map', 'Integrate', 'Validate', 'Analyze', 'Results'];

  const addFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files || []);
    const invalid = selected.find(file => !ALLOWED_EXTENSIONS.has(file.name.slice(file.name.lastIndexOf('.')).toLowerCase()) || file.size > MAX_UPLOAD_SIZE_BYTES);
    if (invalid) {
      setResult({ error: invalid.size > MAX_UPLOAD_SIZE_BYTES ? 'File exceeds the maximum allowed upload size (50 MB).' : 'Unsupported or invalid file type.' });
      setStage('Results');
      event.target.value = '';
      return;
    }
    setFiles(previous => [...previous, ...selected.filter(file => !previous.some(existing => existing.name === file.name))]);
    event.target.value = '';
  };

  const removeFile = (name: string) => {
    setFiles(previous => previous.filter(file => file.name !== name));
    setInspected(previous => previous.filter(file => file.filename !== name));
  };

  const inspect = async () => {
    if (!files.length) return;
    setBusy(true);
    setStage('Detect');
    const form = new FormData();
    files.forEach(file => form.append('files', file));
    try {
      const response = await axios.post(`${API_BASE}/api/inspect-datasets`, form);
      setInspected(response.data.files);
      setStage('Map');
    } catch (error: any) {
      setResult({ error: error.response?.data?.detail || error.message || 'Dataset inspection failed' });
      setStage('Results');
    } finally {
      setBusy(false);
    }
  };

  const analyze = async (event: FormEvent) => {
    event.preventDefault();
    if (!files.length) return;
    setBusy(true);
    setStage('Integrate');
    const form = new FormData();
    files.forEach(file => form.append('files', file));
    setStage('Validate');
    setStage('Analyze');
    try {
      const response = await axios.post(`${API_BASE}/api/analyze-multi`, form, { timeout: 0 });
      setResult(response.data);
      setStage('Results');
      const analysisRunId = response.data.analysis_run_id;
      if (analysisRunId) {
        navigate(`/?run_id=${encodeURIComponent(String(analysisRunId))}`, { replace: true });
      }
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      setResult({ error: typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : error.message || 'Analysis failed' });
      setStage('Results');
    } finally {
      setBusy(false);
    }
  };

  const scanPrivacy = async (datasetId: number) => {
    setPrivacyBusy(datasetId);
    try {
      const response = await axios.post(`${API_BASE}/api/datasets/${datasetId}/privacy-scan`);
      setPrivacyResults(previous => ({ ...previous, [datasetId]: response.data }));
    } catch (error: any) {
      setResult({ error: error.response?.data?.detail || 'Privacy scan failed' });
    } finally {
      setPrivacyBusy(null);
    }
  };

  return <div className="page-stack">
    <div className="page-heading simple"><div><div className="eyebrow">UPLOAD PROJECT FILES</div><h1>Upload project files</h1><p>Add one or more CSV or Excel files. The overview will use only the files you upload.</p></div></div>
    <div className="notice"><strong>Your files stay connected</strong><span>Files are kept together so project details, spending, progress, and review notes can be checked in one place.</span><span className="notice-tag">YOUR DATA</span></div>
    <section className="panel upload-panel"><div className="stage-line">{stages.map((item, index) => <div className={`stage ${stages.indexOf(stage) >= index ? 'complete' : ''}`} key={item}><span>{String(index + 1).padStart(2, '0')}</span>{item}</div>)}</div>
      <div className="upload-workspace"><div><div className="upload-form"><div className="drop-zone"><div className="upload-symbol">↑</div><h2>Add project files</h2><p>CSV and Excel files are supported. Add one file or several files together.</p><input id="multi-file-picker" type="file" multiple accept=".csv,.xlsx,.xls" onChange={addFiles} /><label className="button secondary" htmlFor="multi-file-picker">Choose files</label></div><div className="upload-side"><div className="eyebrow">PROGRESS</div><strong>{busy ? `${stage}...` : stage}</strong><span>{files.length} file{files.length === 1 ? '' : 's'} selected</span><button className="button secondary" type="button" disabled={!files.length || busy} onClick={inspect}>Check files</button><button className="button primary" type="button" disabled={!files.length || busy} onClick={analyze}>Analyze files</button></div></div></div><aside className="knowledge-context"><div className="eyebrow">WHAT TO INCLUDE</div><h2>Give us the project details</h2><p>For the best result, include a project ID, name or description, state, district, approved amount, and amount spent.</p><h3>Helpful tips</h3><ul><li>Use one row for each project.</li><li>Use the same project ID in related files.</li><li>Include dates in the same format.</li><li>Check the file preview before starting.</li></ul><div className="context-note"><strong>How to read the results</strong><span>Review levels are prompts to check records. They are not proof that anyone did anything wrong.</span></div></aside></div>
      <div className="dataset-list">{files.length ? files.map(file => { const info = inspected.find(item => item.filename === file.name); return <div className="dataset-card" key={file.name}><div><strong>{file.name}</strong><span>{file.name.toLowerCase().endsWith('.xlsx') ? 'XLSX workbook' : 'CSV dataset'} · {(file.size / 1024).toFixed(1)} KB</span></div><div className="dataset-role">{info ? <><b>{roleLabel[info.detected_role] || info.detected_role}</b><span>{info.confidence.toFixed(0)}% confidence · {info.selected_sheet || 'sheet pending'}</span><small>{info.sheets?.map(sheet => `${sheet.sheet}: ${sheet.rows.toLocaleString('en-IN')} rows`).join(' · ')}</small>{info.column_mapping?.length ? <details><summary>Detected column mapping</summary><table className="mapping-table"><thead><tr><th>Uploaded column</th><th>Canonical field</th><th>Confidence</th><th>Status</th></tr></thead><tbody>{info.column_mapping.map(mapping => <tr key={`${mapping.uploaded_column}-${mapping.canonical_field}`}><td>{mapping.uploaded_column}</td><td>{mapping.canonical_field}</td><td>{mapping.confidence.toFixed(0)}%</td><td>{mapping.status}</td></tr>)}</tbody></table></details> : null}</> : <span>Role not inspected</span>}</div><button className="remove-file" onClick={() => removeFile(file.name)} aria-label={`Remove ${file.name}`}>×</button></div>; }) : <div className="empty-state"><div className="empty-mark">+</div><strong>No datasets selected</strong><span>Select any supported CSV or Excel dataset to begin a new isolated analysis run.</span></div>}</div>
      {result && <div className="result-panel"><div><div className="eyebrow">FILES {result.error ? 'NEED ATTENTION' : 'READY'}</div><h2>{result.error ? 'We could not use these files yet' : 'Your files are ready'}</h2></div>{result.error ? <p>{typeof result.error === 'string' ? result.error : JSON.stringify(result.error)}</p> : <><div className="result-stats"><span><strong>{String(result.files_processed || 0)}</strong> files</span><span><strong>{Number(result.rows_processed || 0).toLocaleString('en-IN')}</strong> rows</span><span><strong>{Number(result.projects_created || 0).toLocaleString('en-IN')}</strong> projects</span><span><strong>{String(result.alerts_created || 0)}</strong> review prompts</span></div>{Array.isArray(result.datasets) && <div className="dataset-list">{(result.datasets as DatasetIntegrity[]).map(dataset => { const privacy = privacyResults[dataset.id]; return <div className="dataset-card" key={dataset.id}><div><strong>{dataset.file_name}</strong><span>{dataset.algorithm}</span>{privacy && <small>{privacy.privacy_status}{privacy.columns.length ? ` · ${privacy.columns.length} sensitive column${privacy.columns.length === 1 ? '' : 's'}` : ''}</small>}</div><div><span className="signal-chip">{dataset.integrity_status === 'VERIFIED' ? 'Integrity Verified' : dataset.integrity_status === 'FAILED' ? 'Integrity Check Failed' : 'Integrity Check Not Available'}</span><button className="button ghost" type="button" disabled={privacyBusy === dataset.id} onClick={() => scanPrivacy(dataset.id)}>{privacyBusy === dataset.id ? 'Scanning...' : privacy ? 'Rescan privacy' : 'Scan privacy'}</button></div></div>; })}</div>}</>}</div>}
    </section>
  </div>;
}
