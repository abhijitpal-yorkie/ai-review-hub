
import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import {
  Loader2, RefreshCw, Zap, Play, CheckCircle2, XCircle, AlertCircle,
  Inbox, X, Send, GitBranch, Download, FileText, ListChecks
} from 'lucide-react'
import { logger } from '../lib/logger'

const ResultIcon = ({ status }) => {
  if (status === 'PASS') return <CheckCircle2 size={13} />
  if (status === 'FAIL') return <XCircle size={13} />
  return <AlertCircle size={13} />
}

export default function Tickets() {
  const [tickets, setTickets] = useState([])
  const [loadingTickets, setLoadingTickets] = useState(false)
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('overview')
  const [cases, setCases] = useState([])
  const [validation, setValidation] = useState(null)
  const [results, setResults] = useState({})
  const [running, setRunning] = useState({})
  const [generating, setGenerating] = useState(false)
  const [runningAll, setRunningAll] = useState(false)
  const [posting, setPosting] = useState(false)
  const [creatingChildren, setCreatingChildren] = useState(false)
  const [baseUrl, setBaseUrl] = useState('')
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')
  const [log, setLog] = useState([])
  const t0 = useRef(0)

  const pushLog = (msg, isErr = false) => {
    const t = ((Date.now() - t0.current) / 1000).toFixed(1)
    setLog(prev => [...prev, { t, msg, isErr }])
  }

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(''), 3500) }

  const load = async () => {
    setLoadingTickets(true); setError('')
    try {
      const r = await axios.get('/api/tickets', { timeout: 30000 })
      setTickets(r.data.tickets || [])
      const s = await axios.get('/api/settings', { timeout: 10000 })
      if (s.data.defaults?.uat_url) setBaseUrl(s.data.defaults.uat_url)
    } catch (e) { setError(e.response?.data?.detail || e.message) }
    finally { setLoadingTickets(false) }
  }
  useEffect(() => { load() }, [])

  const open = (t) => {
    setSelected(t); setTab('overview'); setCases([]); setValidation(null)
    setResults({}); setError(''); setLog([])
  }
  const close = () => { setSelected(null); setLog([]) }

  const generate = async () => {
    if (!selected) return
    setCases([]); setValidation(null); setResults({}); setGenerating(true)
    setError(''); setLog([]); t0.current = Date.now(); setTab('tests')
    pushLog(`Generating for ${selected.identifier}…`)
    try {
      const r = await axios.post(`/api/tickets/${selected.id}/generate`, {}, { timeout: 240000 })
      pushLog(`Generated ${r.data.test_cases?.length || 0} cases · score ${r.data.validation?.overall_score ?? '—'}/100`)
      setCases(r.data.test_cases || []); setValidation(r.data.validation)
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      pushLog(`ERROR: ${msg}`, true); setError(msg)
    } finally { setGenerating(false) }
  }

  const runCase = async (tc) => {
    if (!baseUrl) { setError('Set the UAT URL at the top first'); return }
    setRunning(p => ({ ...p, [tc.id]: true })); setLog([]); t0.current = Date.now()
    pushLog(`${tc.id}: opening Chromium (visible)`); setTab('tests')
    try {
      const r = await axios.post('/api/execute/case',
        { test_case: tc, base_url: baseUrl }, { timeout: 240000 })
      const result = r.data.result
      pushLog(`${tc.id}: ${result.status} — ${result.reason || ''}`, result.status !== 'PASS')
      setResults(p => ({ ...p, [tc.id]: result }))
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      pushLog(`${tc.id}: ERROR — ${msg}`, true)
      setResults(p => ({ ...p, [tc.id]: { status: 'ERROR', reason: msg } }))
    } finally { setRunning(p => ({ ...p, [tc.id]: false })) }
  }

  const runAll = async () => {
    if (!baseUrl) { setError('Set the UAT URL first'); return }
    setRunningAll(true); setError(''); setLog([]); t0.current = Date.now()
    pushLog(`Running ${cases.length} cases sequentially…`); setTab('tests')
    try {
      const r = await axios.post('/api/execute/all',
        { test_cases: cases, base_url: baseUrl, issue_id: selected?.id },
        { timeout: 900000 })
      const map = {}; (r.data.executions || []).forEach(e => { map[e.test_id] = e })
      setResults(map)
      const passed = Object.values(map).filter(x => x.status === 'PASS').length
      pushLog(`Done: ${passed}/${cases.length} passed`)
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      pushLog(`ERROR: ${msg}`, true); setError(msg)
    } finally { setRunningAll(false) }
  }

  const postReport = async () => {
    if (!selected) return
    const executions = Object.values(results)
    if (executions.length === 0) { showToast('Run some tests first'); return }
    setPosting(true)
    try {
      await axios.post(`/api/tickets/${selected.id}/post-report`, {
        test_cases: cases, executions,
        base_url: baseUrl, validation,
      }, { timeout: 60000 })
      showToast('Report posted to Linear')
    } catch (e) { showToast('Failed: ' + (e.response?.data?.detail || e.message)) }
    finally { setPosting(false) }
  }

  const createChildren = async () => {
    if (!selected) return
    const executions = Object.values(results)
    const failures = executions.filter(e => e.status !== 'PASS')
    if (failures.length === 0) { showToast('No failures to convert'); return }
    setCreatingChildren(true)
    try {
      const r = await axios.post(`/api/tickets/${selected.id}/create-children`, {
        test_cases: cases, executions, base_url: baseUrl,
      }, { timeout: 120000 })
      const created = r.data.created || []
      showToast(`Created ${created.length} child ticket${created.length === 1 ? '' : 's'} in Linear`)
    } catch (e) { showToast('Failed: ' + (e.response?.data?.detail || e.message)) }
    finally { setCreatingChildren(false) }
  }

  const hasCases = cases.length > 0
  const executions = Object.values(results)
  const passed = executions.filter(e => e.status === 'PASS').length
  const failed = executions.filter(e => e.status === 'FAIL').length
  const errored = executions.filter(e => e.status === 'ERROR' || e.status === 'TIMEOUT').length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="page-head" style={{ paddingBottom: '16px' }}>
        <div className="page-eyebrow">Workspace</div>
        <h1 className="page-title">Tickets</h1>
        <p className="page-sub">Select a ticket → generate test cases → run against UAT → post results back to Linear.</p>
        <div className="gap-row" style={{ marginTop: '16px' }}>
          <input className="input" style={{ flex: 1, maxWidth: '560px' }}
            placeholder="UAT base URL — e.g. https://e2e-test.uat.lexful.net/docs/assets"
            value={baseUrl} onChange={e => setBaseUrl(e.target.value)} />
          <button className="ghost" onClick={load} disabled={loadingTickets}>
            {loadingTickets ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />} Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '0 32px' }}>
          <div className="banner error">{error}</div>
        </div>
      )}

      <div style={{ flex: 1, overflow: 'hidden', padding: '0 32px 24px' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: '12px', overflowY: 'auto', height: '100%', paddingRight: '4px',
        }}>
          {loadingTickets && tickets.length === 0 && (
            <div className="empty-state" style={{ gridColumn: '1/-1' }}>
              <Loader2 className="spin" size={22} style={{ color: 'var(--primary)' }} />
            </div>
          )}
          {tickets.map(t => (
            <div key={t.id} className={`ticket ${selected?.id === t.id ? 'selected' : ''}`}
              onClick={() => open(t)}>
              <div className="ticket-row">
                <span className="ticket-id">{t.identifier}</span>
                <span className="badge badge-neutral">{t.state?.name || '—'}</span>
              </div>
              <div className="ticket-title">{t.title}</div>
              <div className="ticket-meta">
                <span>{t.assignee?.name || 'Unassigned'}</span>
                <span>{t.team?.name}</span>
              </div>
            </div>
          ))}
          {!loadingTickets && tickets.length === 0 && (
            <div className="empty-state" style={{ gridColumn: '1/-1' }}>
              <div className="empty-icon"><Inbox size={22} /></div>
              <div>No tickets found</div>
            </div>
          )}
        </div>
      </div>

      {/* ── SIDE DRAWER ── */}
      {selected && (
        <>
          <div className="drawer-scrim" onClick={close} />
          <div className="drawer">
            <div className="drawer-hd">
              <div className="drawer-hd-info">
                <div className="ticket-id">{selected.identifier}</div>
                <h2 className="drawer-hd-title">{selected.title}</h2>
              </div>
              <div className="drawer-hd-actions">
                {!hasCases && !generating && (
                  <button className="primary" onClick={generate}>
                    <Zap size={14} /> Generate test cases
                  </button>
                )}
                {generating && (
                  <button className="primary" disabled>
                    <Loader2 size={14} className="spin" /> Generating…
                  </button>
                )}
                {hasCases && (
                  <>
                    <button className="primary" onClick={runAll} disabled={runningAll}>
                      {runningAll ? <Loader2 size={14} className="spin" /> : <Play size={14} />}
                      {runningAll ? 'Running…' : `Run all (${cases.length})`}
                    </button>
                    <button className="ghost" onClick={generate} disabled={generating || runningAll}>
                      <RefreshCw size={14} /> Regenerate
                    </button>
                  </>
                )}
                <button className="ghost" onClick={close}><X size={14} /></button>
              </div>
            </div>

            <div className="drawer-tabs">
              <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>
                <FileText size={14} /> Overview
              </button>
              <button className={tab === 'tests' ? 'active' : ''} onClick={() => setTab('tests')}>
                <ListChecks size={14} /> Test cases
                {hasCases && <span className="tab-count">{cases.length}</span>}
              </button>
              <button className={tab === 'results' ? 'active' : ''} onClick={() => setTab('results')}>
                <CheckCircle2 size={14} /> Results
                {executions.length > 0 && <span className="tab-count">{executions.length}</span>}
              </button>
            </div>

            <div className="drawer-body">
              {tab === 'overview' && (
                <>
                  <div className="card" style={{ marginBottom: '16px' }}>
                    <div className="card-title" style={{ marginBottom: '12px' }}>Description</div>
                    <div className="md">
                      <ReactMarkdown>{selected.description || '_No description._'}</ReactMarkdown>
                    </div>
                  </div>

                  {validation && (
                    <div className="card" style={{ marginBottom: '16px' }}>
                      <div className="card-hd">
                        <div className="card-title">Validation score</div>
                        <span className={`badge ${validation.passed ? 'badge-pass' : 'badge-fail'}`}>
                          {validation.overall_score}/100
                        </span>
                      </div>
                      <p className="muted">{validation.recommendation}</p>
                    </div>
                  )}

                  {executions.length > 0 && (
                    <>
                      <div className="stat-row">
                        <div className="stat-tile">
                          <div className="stat-label">Total run</div>
                          <div className="stat-value">{executions.length}</div>
                        </div>
                        <div className="stat-tile">
                          <div className="stat-label">Passed</div>
                          <div className="stat-value pass">{passed}</div>
                        </div>
                        <div className="stat-tile">
                          <div className="stat-label">Failed</div>
                          <div className="stat-value fail">{failed}</div>
                        </div>
                        <div className="stat-tile">
                          <div className="stat-label">Errored</div>
                          <div className="stat-value fail">{errored}</div>
                        </div>
                      </div>

                      <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>Write back to Linear</div>
                        <p className="muted" style={{ marginBottom: '14px' }}>
                          Post the report as a comment, or create child tickets for each failure.
                        </p>
                        <div className="btn-row" style={{ marginTop: 0 }}>
                          <button className="primary" onClick={postReport} disabled={posting}>
                            {posting ? <Loader2 size={14} className="spin" /> : <Send size={14} />}
                            {posting ? 'Posting…' : 'Post report to ticket'}
                          </button>
                          <button className="ghost" onClick={createChildren}
                            disabled={creatingChildren || (failed + errored) === 0}>
                            {creatingChildren ? <Loader2 size={14} className="spin" /> : <GitBranch size={14} />}
                            {creatingChildren ? 'Creating…' : `Create child tickets (${failed + errored})`}
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </>
              )}

              {tab === 'tests' && (
                <>
                  {log.length > 0 && (
                    <div className="live-log" style={{ marginBottom: '16px' }}>
                      <div className="live-log-title">Live activity</div>
                      {log.map((l, i) => (
                        <div key={i} className={`live-log-line ${l.isErr ? 'error' : ''}`}>
                          [{l.t}s] {l.msg}
                        </div>
                      ))}
                    </div>
                  )}

                  {generating && (
                    <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
                      <Loader2 className="spin" size={22} style={{ color: 'var(--primary)' }} />
                      <p className="muted" style={{ marginTop: '12px' }}>Generating and validating…</p>
                    </div>
                  )}

                  {hasCases && (
                    <div className="case-list" style={{ marginTop: 0 }}>
                      {cases.map(tc => {
                        const r = results[tc.id]
                        const isRunning = running[tc.id]
                        return (
                          <div key={tc.id} className={`case ${isRunning ? 'running' : ''}`}>
                            <div className="case-hd">
                              <div className="case-hd-left">
                                <span className="ticket-id">{tc.id}</span>
                                {tc.priority && <span className={`badge badge-priority-${tc.priority}`}>{tc.priority}</span>}
                                {r && (
                                  <span className={`badge badge-${r.status === 'PASS' ? 'pass' : r.status === 'FAIL' ? 'fail' : 'warn'}`}>
                                    <ResultIcon status={r.status} /> {r.status}
                                  </span>
                                )}
                              </div>
                              <button className="btn-run" onClick={() => runCase(tc)} disabled={isRunning || runningAll}>
                                {isRunning ? <Loader2 size={12} className="spin" /> : <Play size={12} />}
                                {isRunning ? 'Running' : 'Run'}
                              </button>
                            </div>
                            <div className="case-body">
                              <div className="case-title">{tc.title}</div>
                              {(tc.preconditions || tc.steps || tc.expected) && (
                                <dl className="case-dl">
                                  {tc.preconditions && <><dt>Preconditions</dt><dd>{tc.preconditions}</dd></>}
                                  {tc.steps && <><dt>Steps</dt><dd>{tc.steps}</dd></>}
                                  {tc.expected && <><dt>Expected</dt><dd>{tc.expected}</dd></>}
                                </dl>
                              )}
                              {r?.reason && <div className="case-result">{r.reason}</div>}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {!generating && !hasCases && (
                    <div className="empty-state">
                      <div className="empty-icon"><Zap size={22} /></div>
                      <div style={{ fontWeight: 600, color: 'var(--ink)', marginBottom: '4px' }}>No cases yet</div>
                      <div>Click "Generate test cases" above to start.</div>
                    </div>
                  )}
                </>
              )}

              {tab === 'results' && (
                <>
                  {executions.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-icon"><CheckCircle2 size={22} /></div>
                      <div style={{ fontWeight: 600, color: 'var(--ink)', marginBottom: '4px' }}>No results yet</div>
                      <div>Run a test case to see its result here.</div>
                    </div>
                  ) : (
                    <>
                      <div className="stat-row">
                        <div className="stat-tile">
                          <div className="stat-label">Passed</div>
                          <div className="stat-value pass">{passed}</div>
                        </div>
                        <div className="stat-tile">
                          <div className="stat-label">Failed</div>
                          <div className="stat-value fail">{failed}</div>
                        </div>
                        <div className="stat-tile">
                          <div className="stat-label">Errored</div>
                          <div className="stat-value fail">{errored}</div>
                        </div>
                      </div>

                      <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>Post to Linear</div>
                        <div className="btn-row" style={{ marginTop: 0 }}>
                          <button className="primary" onClick={postReport} disabled={posting}>
                            {posting ? <Loader2 size={14} className="spin" /> : <Send size={14} />}
                            {posting ? 'Posting…' : 'Post report to ticket'}
                          </button>
                          <button className="ghost" onClick={createChildren}
                            disabled={creatingChildren || (failed + errored) === 0}>
                            {creatingChildren ? <Loader2 size={14} className="spin" /> : <GitBranch size={14} />}
                            {creatingChildren ? 'Creating…' : `Create child tickets (${failed + errored})`}
                          </button>
                        </div>
                      </div>

                      <div className="case-list" style={{ marginTop: '16px' }}>
                        {executions.map(e => (
                          <div key={e.test_id} className="case">
                            <div className="case-hd">
                              <div className="case-hd-left">
                                <span className="ticket-id">{e.test_id}</span>
                                <span className={`badge badge-${e.status === 'PASS' ? 'pass' : e.status === 'FAIL' ? 'fail' : 'warn'}`}>
                                  <ResultIcon status={e.status} /> {e.status}
                                </span>
                              </div>
                            </div>
                            <div className="case-body">
                              {e.reason && <div className="case-result">{e.reason}</div>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </>
      )}

      {toast && (
        <div style={{
          position: 'fixed', bottom: '24px', right: '24px',
          background: 'var(--ink)', color: 'white',
          padding: '12px 20px', borderRadius: '10px',
          boxShadow: '0 6px 20px rgba(0,0,0,.2)', zIndex: 100,
          fontSize: '13.5px', fontWeight: 500,
        }}>{toast}</div>
      )}
    </div>
  )
}
