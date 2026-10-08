import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Loader2, RefreshCw, CheckCircle2, XCircle, AlertCircle, Info, Trash2 } from 'lucide-react'

const CATEGORIES = ['all','system','settings','linear','provider','qa','execution','webhook']
const STATUSES = ['all','success','error','warn','info']

const StatusIcon = ({ s }) => {
  if (s === 'success') return <CheckCircle2 size={14} style={{color:'var(--success)'}}/>
  if (s === 'error')   return <XCircle size={14} style={{color:'var(--danger)'}}/>
  if (s === 'warn')    return <AlertCircle size={14} style={{color:'var(--warn)'}}/>
  return <Info size={14} style={{color:'var(--text-3)'}}/>
}

const timeAgo = (iso) => {
  const d = new Date(iso); const s = (Date.now() - d) / 1000
  if (s < 60) return `${Math.floor(s)}s ago`
  if (s < 3600) return `${Math.floor(s/60)}m ago`
  if (s < 86400) return `${Math.floor(s/3600)}h ago`
  return d.toLocaleDateString()
}

export default function Audit() {
  const [events, setEvents] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [cat, setCat] = useState('all')
  const [status, setStatus] = useState('all')

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (cat !== 'all') params.category = cat
      if (status !== 'all') params.status = status
      params.limit = 300
      const r = await axios.get('/api/audit', { params })
      setEvents(r.data.events || []); setStats(r.data.stats)
    } finally { setLoading(false) }
  }
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [cat, status])

  const clearLog = async () => {
    if (!confirm('Clear all audit log entries? This cannot be undone.')) return
    await axios.delete('/api/audit'); load()
  }

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow">Configure</div>
        <h1>Audit log</h1>
        <p className="page-sub">Every meaningful action — Linear calls, LLM tests, test-case generation, UAT executions, setting changes. Auto-refreshes every 10s.</p>
      </div>

      {stats && (
        <div className="stat-grid">
          <div className="stat"><div className="stat-label">Total events</div><div className="stat-value">{stats.total}</div></div>
          <div className="stat"><div className="stat-label">Success</div><div className="stat-value" style={{color:'var(--success)'}}>{stats.by_status.success || 0}</div></div>
          <div className="stat"><div className="stat-label">Errors</div><div className="stat-value" style={{color:'var(--danger)'}}>{stats.by_status.error || 0}</div></div>
          <div className="stat"><div className="stat-label">Warnings</div><div className="stat-value" style={{color:'var(--warn)'}}>{stats.by_status.warn || 0}</div></div>
        </div>
      )}

      <div className="card" style={{padding:'1rem 1.25rem'}}>
        <div style={{display:'flex',gap:'.75rem',alignItems:'center',flexWrap:'wrap'}}>
          <select className="input" style={{width:'auto',minWidth:'160px'}} value={cat} onChange={e=>setCat(e.target.value)}>
            {CATEGORIES.map(c => <option key={c} value={c}>{c === 'all' ? 'All categories' : c}</option>)}
          </select>
          <select className="input" style={{width:'auto',minWidth:'140px'}} value={status} onChange={e=>setStatus(e.target.value)}>
            {STATUSES.map(s => <option key={s} value={s}>{s === 'all' ? 'All statuses' : s}</option>)}
          </select>
          <div style={{marginLeft:'auto',display:'flex',gap:'.5rem'}}>
            <button className="ghost" onClick={load} disabled={loading}>
              <RefreshCw size={14} className={loading?'spin':''}/> Refresh
            </button>
            <button className="ghost" onClick={clearLog}><Trash2 size={14}/> Clear</button>
          </div>
        </div>
      </div>

      <div className="card" style={{padding:0,overflow:'hidden'}}>
        {events.length === 0 && <div className="empty"><div>No events yet</div></div>}
        {events.length > 0 && (
          <div style={{display:'flex',flexDirection:'column'}}>
            {events.map((e, i) => (
              <div key={i} style={{
                padding:'1rem 1.35rem',
                borderBottom: i < events.length-1 ? '1px solid var(--border)' : 'none',
                display:'grid', gridTemplateColumns:'auto 1fr auto',
                gap:'1rem', alignItems:'flex-start',
              }}>
                <div style={{paddingTop:'.15rem'}}><StatusIcon s={e.status}/></div>
                <div style={{minWidth:0}}>
                  <div style={{display:'flex',alignItems:'center',gap:'.6rem',flexWrap:'wrap'}}>
                    <span style={{fontWeight:600,fontSize:'.88rem',color:'var(--text)'}}>{e.event}</span>
                    <span className="badge badge-neutral">{e.category}</span>
                    {e.target && <span className="badge badge-neutral" style={{fontFamily:'var(--mono)',fontSize:'.68rem'}}>{e.target}</span>}
                  </div>
                  {e.detail && Object.keys(e.detail).length > 0 && (
                    <div style={{marginTop:'.35rem',fontSize:'.78rem',color:'var(--text-3)',fontFamily:'var(--mono)',wordBreak:'break-word'}}>
                      {Object.entries(e.detail).map(([k,v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' · ')}
                    </div>
                  )}
                </div>
                <div style={{fontSize:'.75rem',color:'var(--text-3)',whiteSpace:'nowrap'}}>{timeAgo(e.ts)}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
