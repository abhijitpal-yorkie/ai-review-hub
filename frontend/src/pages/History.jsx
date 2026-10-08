import React, { useState, useEffect } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import { Loader2, Palette, FlaskConical, RefreshCw, Trash2, Eye, X } from 'lucide-react'

const timeAgo = (iso) => {
  const d = new Date(iso); const s = (Date.now() - d) / 1000
  if (s < 60) return `${Math.floor(s)}s ago`
  if (s < 3600) return `${Math.floor(s/60)}m ago`
  if (s < 86400) return `${Math.floor(s/3600)}h ago`
  return d.toLocaleDateString()
}

export default function History() {
  const [tab, setTab] = useState('ux')
  const [ux, setUx] = useState({records:[], stats:null})
  const [tickets, setTickets] = useState({records:[], stats:null})
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [a, b] = await Promise.all([
        axios.get('/api/history/ux?limit=100'),
        axios.get('/api/history/tickets?limit=100'),
      ])
      setUx(a.data); setTickets(b.data)
    } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const remove = async (kind, id) => {
    if (!confirm('Delete this record?')) return
    await axios.delete(`/api/history/${kind}/${id}`)
    if (selected?.id === id) setSelected(null)
    load()
  }

  const current = tab === 'ux' ? ux : tickets
  const records = current.records || []

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow">Reports</div>
        <h1>History</h1>
        <p className="page-sub">Every UX audit and ticket test run is recorded here with full artifacts — reports, mockups, execution results.</p>
      </div>

      <div className="tab-bar">
        <button className={tab==='ux'?'active':''} onClick={()=>{setTab('ux');setSelected(null)}}>
          <Palette size={13}/> UX Audits ({ux.stats?.total || 0})
        </button>
        <button className={tab==='tickets'?'active':''} onClick={()=>{setTab('tickets');setSelected(null)}}>
          <FlaskConical size={13}/> Ticket Runs ({tickets.stats?.total || 0})
        </button>
        <button className="ghost" onClick={load} disabled={loading} style={{marginLeft:'auto'}}>
          <RefreshCw size={14} className={loading?'spin':''}/> Refresh
        </button>
      </div>

      <div style={{display:'grid',gridTemplateColumns: selected ? '380px 1fr' : '1fr', gap:'1.5rem'}}>
        <div>
          {records.length === 0 && (
            <div className="empty">No {tab === 'ux' ? 'UX audits' : 'ticket runs'} yet.</div>
          )}
          {records.map(r => (
            <div key={r.id} className={`ticket ${selected?.id===r.id?'selected':''}`}
                 onClick={()=>setSelected(r)} style={{cursor:'pointer'}}>
              <div className="ticket-row">
                <span className="ticket-id">{r.id}</span>
                <span className={`badge badge-${r.status==='success'?'pass':'fail'}`}>{r.status}</span>
              </div>
              <div className="ticket-title">
                {tab === 'ux'
                  ? (r.url || '(image)')
                  : (r.identifier || r.issue_id || r.action || 'batch')}
              </div>
              <div className="ticket-meta">
                <span>{timeAgo(r.ts)}</span>
                {tab === 'ux' && r.persona && <span>as {r.persona}</span>}
                {tab === 'tickets' && r.action === 'run_all' && <span>{r.passed}/{r.total} passed</span>}
                {tab === 'tickets' && r.action === 'generate' && <span>{r.test_cases?.length || 0} cases</span>}
              </div>
            </div>
          ))}
        </div>

        {selected && (
          <div>
            <div className="card">
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:'1rem'}}>
                <div>
                  <div className="ticket-id" style={{marginBottom:'.35rem'}}>{selected.id}</div>
                  <h2 style={{margin:'0 0 .25rem'}}>{selected.url || selected.identifier || selected.action}</h2>
                  <div style={{fontSize:'.8rem',color:'var(--text-3)'}}>{new Date(selected.ts).toLocaleString()}</div>
                </div>
                <div style={{display:'flex',gap:'.5rem'}}>
                  <button className="ghost" onClick={()=>remove(tab, selected.id)}><Trash2 size={14}/></button>
                  <button className="ghost" onClick={()=>setSelected(null)}><X size={14}/></button>
                </div>
              </div>
            </div>

            {tab === 'ux' && (
              <>
                {selected.audit_report && (
                  <div className="report">
                    <h2>UX Audit</h2>
                    <ReactMarkdown>{selected.audit_report}</ReactMarkdown>
                  </div>
                )}
                {selected.mockup_html && (
                  <div className="mockup-viewer">
                    <div className="mockup-toolbar">
                      <button className="active">Improved Mockup (archived)</button>
                    </div>
                    <div className="mockup-frame">
                      <iframe srcDoc={selected.mockup_html} title="Archived mockup" sandbox="allow-scripts"/>
                    </div>
                  </div>
                )}
              </>
            )}

            {tab === 'tickets' && (
              <>
                {selected.validation && (
                  <div className="report">
                    <h2>Validation</h2>
                    <p><span className={`badge ${selected.validation.passed?'badge-pass':'badge-fail'}`}>
                      {selected.validation.overall_score}/100
                    </span> · {selected.validation.recommendation}</p>
                  </div>
                )}
                {selected.executions?.length > 0 && (
                  <div className="report">
                    <h2>Execution Results</h2>
                    {selected.executions.map((e,i)=>(
                      <p key={i} style={{margin:'.35rem 0'}}>
                        <span className={`badge ${e.status==='PASS'?'badge-pass':'badge-fail'}`}>{e.status}</span>{' '}
                        <strong>{e.test_id}</strong> — {(e.reason||'').slice(0,200)}
                      </p>
                    ))}
                  </div>
                )}
                {selected.report_markdown && (
                  <div className="report">
                    <h2>Full Report</h2>
                    <ReactMarkdown>{selected.report_markdown}</ReactMarkdown>
                  </div>
                )}
                {selected.test_cases_markdown && (
                  <div className="report">
                    <h2>Test Cases</h2>
                    <ReactMarkdown>{selected.test_cases_markdown}</ReactMarkdown>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
