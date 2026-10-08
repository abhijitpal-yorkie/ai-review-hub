import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Upload, Save, Loader2 } from 'lucide-react'
export default function Skills() {
  const [skills, setSkills] = useState([]); const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(false); const [toast, setToast] = useState('')
  const load = async () => {
    try { const r = await axios.get('/api/skills'); setSkills(r.data.skills); setConfig(r.data.config) } catch {}
  }
  useEffect(() => { load() }, [])
  const upload = async (file) => {
    const fd = new FormData(); fd.append('file', file); setLoading(true)
    try { await axios.post('/api/skills/upload', fd); setToast('Skill uploaded'); load() }
    catch (e) { setToast('Upload failed') } finally { setLoading(false); setTimeout(()=>setToast(''),2000) }
  }
  const toggle = (cat, file) => {
    const next = {...config}; const list = next.active_skills[cat] || []
    next.active_skills[cat] = list.includes(file) ? list.filter(x=>x!==file) : [...list, file]
    setConfig(next)
  }
  const save = async () => {
    setLoading(true)
    try { await axios.post('/api/skills/select', {active_skills: config.active_skills}); setToast('Saved') }
    catch { setToast('Save failed') } finally { setLoading(false); setTimeout(()=>setToast(''),2000) }
  }
  if (!config) return <div className="empty"><Loader2 className="spin"/></div>
  const cats = [['qa','QA Generation'],['validation','Validation'],['uat','UAT Execution'],['ux','UX Audit'],['mockup','Mockup Builder']]
  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow">Configure</div>
        <h1>Skills</h1>
        <p className="page-sub">Upload markdown skill files and pick which ones run for each agent.</p>
      </div>

      <div className="card">
        <h2>Upload skill</h2>
        <p className="card-desc">Drop a .md file — it'll appear below and can be toggled per agent.</p>
        <label className="upload" style={{display:'block',marginTop:'1rem'}}>
          <Upload size={20} style={{color:'var(--primary)',marginBottom:'.5rem'}}/>
          <div style={{fontSize:'.85rem'}}>Click to select a .md file</div>
          <input type="file" accept=".md" style={{display:'none'}} onChange={e=>e.target.files[0] && upload(e.target.files[0])}/>
        </label>
      </div>

      {cats.map(([cat, label]) => (
        <div className="card" key={cat}>
          <h2>{label}</h2>
          <p className="card-desc">Choose which skills this agent uses.</p>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(240px,1fr))',gap:'.5rem',marginTop:'1rem'}}>
            {skills.map(s => {
              const on = (config.active_skills[cat] || []).includes(s)
              return (
                <label key={s} style={{display:'flex',alignItems:'center',gap:'.6rem',padding:'.6rem .85rem',
                  background:on?'var(--primary-soft)':'var(--surface-2)',borderRadius:'10px',
                  border:`1px solid ${on?'var(--primary)':'var(--border)'}`,fontSize:'.82rem',cursor:'pointer',
                  color:on?'var(--primary)':'var(--text-2)',fontWeight:on?600:500}}>
                  <input type="checkbox" checked={on} onChange={()=>toggle(cat, s)} style={{accentColor:'var(--primary)'}}/>
                  {s}
                </label>
              )
            })}
          </div>
        </div>
      ))}

      <div className="btn-row">
        <button className="primary" onClick={save} disabled={loading}>
          {loading ? <Loader2 size={14} className="spin"/> : <Save size={14}/>} Save configuration
        </button>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
