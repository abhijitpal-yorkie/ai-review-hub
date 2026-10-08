import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Loader2, Save, Check, X, Copy, ExternalLink } from 'lucide-react'

export default function Settings() {
  const [data, setData] = useState(null)
  const [form, setForm] = useState({profile:{}, providers:{}, linear:{}, defaults:{}})
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState('')
  const [testing, setTesting] = useState({})
  const [testResult, setTestResult] = useState({})

  const load = async () => {
    const r = await axios.get('/api/settings')
    setData(r.data)
    setForm({
      profile: r.data.profile || {},
      providers: {gemini:'',groq:'',cerebras:'',nvidia:'',openrouter:''},
      linear: {api_key:'', webhook_secret:'', auto_report: r.data.linear?.auto_report ?? true},
      defaults: r.data.defaults || {},
    })
  }
  useEffect(() => { load() }, [])

  const save = async () => {
    setSaving(true)
    try {
      const payload = {
        profile: form.profile,
        defaults: form.defaults,
        linear: {...form.linear, api_key: form.linear.api_key || undefined, webhook_secret: form.linear.webhook_secret || undefined},
        providers: Object.fromEntries(Object.entries(form.providers).filter(([_,v]) => v && v.length > 0)),
      }
      await axios.post('/api/settings', payload)
      setToast('Settings saved'); load()
    } catch (e) { setToast('Save failed: '+e.message) }
    finally { setSaving(false); setTimeout(()=>setToast(''),2000) }
  }

  const test = async (what) => {
    setTesting(p => ({...p, [what]: true}))
    try {
      let body = {}
      if (what === 'linear') body = { key: form.linear.api_key || undefined }
      else body = { key: form.providers[what] || undefined }
      const r = await axios.post(`/api/settings/test/${what}`, body)
      setTestResult(p => ({...p, [what]: r.data}))
      if (r.data.ok) {
        // Auto-saved — refresh masked data + clear the raw field so the placeholder updates
        const fresh = await axios.get('/api/settings')
        setData(fresh.data)
        if (what === 'linear') setForm(f => ({...f, linear: {...f.linear, api_key: ''}}))
        else setForm(f => ({...f, providers: {...f.providers, [what]: ''}}))
        setToast(r.data.saved ? '✓ Verified and saved' : '✓ Verified')
        setTimeout(()=>setToast(''), 2500)
      }
    } catch (e) {
      setTestResult(p => ({...p, [what]: {ok: false, error: e.message}}))
    } finally { setTesting(p => ({...p, [what]: false})) }
  }

  const copy = (t) => { navigator.clipboard.writeText(t); setToast('Copied'); setTimeout(()=>setToast(''),1500) }

  if (!data) return <div className="empty"><Loader2 className="spin"/></div>

  const webhookUrl = data.linear?.suggested_webhook_url || ''

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow">Configure</div>
        <h1>Settings</h1>
        <p className="page-sub">Profile, Linear connection, LLM providers, and defaults. Everything saved here persists across restarts.</p>
      </div>

      {/* PROFILE */}
      <div className="card">
        <h2>Profile</h2>
        <p className="card-desc">Shown in the sidebar.</p>
        <div className="field-row" style={{marginTop:'1rem'}}>
          <div className="field">
            <label>Full name</label>
            <input className="input" value={form.profile.name || ''} onChange={e=>setForm({...form, profile:{...form.profile, name:e.target.value}})} placeholder="Abhijit P."/>
          </div>
          <div className="field">
            <label>Role</label>
            <input className="input" value={form.profile.role || ''} onChange={e=>setForm({...form, profile:{...form.profile, role:e.target.value}})} placeholder="QA Engineer"/>
          </div>
        </div>
        <div className="field">
          <label>Email (optional)</label>
          <input className="input" value={form.profile.email || ''} onChange={e=>setForm({...form, profile:{...form.profile, email:e.target.value}})} placeholder="you@company.com"/>
        </div>
      </div>

      {/* LINEAR */}
      <div className="card">
        <h2>Linear connection</h2>
        <p className="card-desc">Required to fetch tickets and post reports back. Get your API key at Linear → Settings → Security & Access → Personal API Keys.</p>
        <div className="field" style={{marginTop:'1rem'}}>
          <label>Personal API key</label>
          <div style={{display:'flex',gap:'.5rem'}}>
            <input className="input" type="password" value={form.linear.api_key || ''}
              onChange={e=>setForm({...form, linear:{...form.linear, api_key:e.target.value}})}
              placeholder={data.linear?.has_api_key ? `Current: ${data.linear.api_key_masked}  (paste new to replace)` : 'lin_api_...'}/>
            <button className="ghost" onClick={()=>test('linear')} disabled={testing.linear || !form.linear.api_key}>
              {testing.linear ? <Loader2 size={14} className="spin"/> : 'Test'}
            </button>
          </div>
          {!form.linear.api_key && !data.linear?.has_api_key && (
              <div className="input-hint">Paste your key, then click Test. Click Save when done.</div>
            )}
            {testResult.linear && (
            <div className="input-hint" style={{color: testResult.linear.ok ? 'var(--success)' : 'var(--danger)'}}>
              {testResult.linear.ok ? <>✓ Connected as <strong>{testResult.linear.viewer?.name}</strong></> : <>✗ {testResult.linear.error}</>}
            </div>
          )}
        </div>

        <div className="field">
          <label>Webhook URL — paste this into Linear → Settings → API → Webhooks</label>
          <div className="url-box">
            <input className="input" readOnly value={webhookUrl}/>
            <button className="ghost" onClick={()=>copy(webhookUrl)}><Copy size={14}/></button>
          </div>
          {webhookUrl.startsWith('http://') ? (
            <div className="input-hint" style={{color:'var(--warn)',background:'var(--warn-bg)',padding:'.65rem .85rem',borderRadius:'8px',marginTop:'.5rem'}}>
              ⚠ <strong>Linear rejects http:// URLs.</strong> You need an HTTPS tunnel. Run in a terminal:
              <pre style={{background:'var(--surface)',padding:'.5rem .75rem',borderRadius:'6px',marginTop:'.5rem',fontSize:'.78rem',overflow:'auto'}}>ngrok http 8000</pre>
              Then paste the <strong>https://xxxx.ngrok-free.app/api/webhooks/linear</strong> URL it prints into Linear.
            </div>
          ) : (
            <div className="input-hint">✓ HTTPS — paste this into Linear → Settings → Administration → API → Webhooks.</div>
          )}
        </div>

        <div className="field">
          <label>Webhook signing secret (from Linear)</label>
          <input className="input" type="password" value={form.linear.webhook_secret || ''}
            onChange={e=>setForm({...form, linear:{...form.linear, webhook_secret:e.target.value}})}
            placeholder={data.linear?.has_webhook_secret ? `Current: ${data.linear.webhook_secret_masked}` : 'whsec_...'}/>
        </div>

        <label style={{display:'flex',alignItems:'center',gap:'.5rem',fontSize:'.85rem',color:'var(--text-2)',cursor:'pointer'}}>
          <input type="checkbox" checked={form.linear.auto_report} onChange={e=>setForm({...form, linear:{...form.linear, auto_report:e.target.checked}})} style={{accentColor:'var(--primary)'}}/>
          Auto-post execution reports back to Linear tickets
        </label>
      </div>

      {/* PROVIDERS */}
      <div className="card">
        <h2>LLM providers</h2>
        <p className="card-desc">At minimum set Gemini. Add Groq for automatic failover when Gemini rate-limits.</p>
        {['gemini','groq','cerebras','nvidia','openrouter'].map(p => (
          <div className="field" key={p} style={{marginTop:'1rem'}}>
            <label style={{textTransform:'capitalize'}}>{p}</label>
            <div style={{display:'flex',gap:'.5rem'}}>
              <input className="input" type="password" value={form.providers[p] || ''}
                onChange={e=>setForm({...form, providers:{...form.providers, [p]:e.target.value}})}
                placeholder={data.providers?.[p]?.has_key ? `Current: ${data.providers[p].masked}  (paste new to replace)` : `Enter ${p} API key`}/>
              <button className="ghost" onClick={()=>test(p)} disabled={testing[p] || !form.providers[p]}>
                {testing[p] ? <Loader2 size={14} className="spin"/> : 'Test'}
              </button>
            </div>
            {testResult[p] && (
              <div className="input-hint" style={{color: testResult[p].ok ? 'var(--success)' : 'var(--danger)'}}>
                {testResult[p].ok ? '✓ Key works' : `✗ ${testResult[p].error || 'HTTP '+testResult[p].status}`}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* DEFAULTS */}
      <div className="card">
        <h2>Defaults</h2>
        <div className="field" style={{marginTop:'1rem'}}>
          <label>UAT base URL</label>
          <input className="input" value={form.defaults.uat_url || ''} onChange={e=>setForm({...form, defaults:{...form.defaults, uat_url:e.target.value}})} placeholder="https://staging.example.com"/>
          <div className="input-hint">Pre-fills the URL field on the Tickets page.</div>
        </div>
        <div className="field">
          <label>Max test cases per "Run All"</label>
          <input className="input" type="number" min="1" max="20" value={form.defaults.max_parallel_cases || 10}
            onChange={e=>setForm({...form, defaults:{...form.defaults, max_parallel_cases: parseInt(e.target.value)||10}})}/>
        </div>
      </div>

      <div className="btn-row">
        <button className="primary" onClick={save} disabled={saving}>
          {saving ? <Loader2 size={14} className="spin"/> : <Save size={14}/>} Save all settings
        </button>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
