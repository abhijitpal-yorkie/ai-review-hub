
import React, { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Loader2, Globe, Upload, Layers, Play, Download, Image, Wand2, ShieldCheck } from 'lucide-react'
import axios from 'axios'
import MockupViewer from '../components/MockupViewer'

export default function UXReview() {
  const [mode, setMode] = useState('url')
  const [url, setUrl] = useState('')
  const [image, setImage] = useState(null)
  const [persona, setPersona] = useState('admin')
  const [maxPages, setMaxPages] = useState(15)
  const [crawlMode, setCrawlMode] = useState(false)
  const [report, setReport] = useState(null)
  const [crawl, setCrawl] = useState(null)
  const [loading, setLoading] = useState(false)
  const [flow, setFlow] = useState([])
  const t0 = useRef(0)

  const isLexful = url.includes('lexful.net')

  const setStep = (label, value, status) => {
    setFlow(prev => {
      const copy = [...prev]
      copy.push({ label, value, status, t: ((Date.now() - t0.current) / 1000).toFixed(1) })
      return copy
    })
  }

  const downloadReport = () => {
    if (!report?.audit_report) return
    const doc = `<!doctype html><html><head><meta charset="utf-8"><title>UX Audit</title>
<style>body{font-family:system-ui;max-width:1400px;margin:2rem auto;padding:1rem;color:#111}
h1{margin:0 0 1rem}.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1rem 0}
.panel{border:1px solid #ddd;border-radius:12px;overflow:hidden;background:#fff}
.panel h2{margin:0;padding:.75rem 1rem;background:#f2f4f2;font-size:.85rem;letter-spacing:.06em;text-transform:uppercase}
.panel img{max-width:100%;display:block}.panel iframe{width:100%;height:700px;border:0}
.audit{background:#f7f8f7;padding:1.5rem;border-radius:12px;margin-top:2rem;white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace;font-size:.85rem;line-height:1.6}
</style></head><body>
<h1>UX Audit Report</h1>
<p>${report.final_url || url}${report.persona_used ? ` · as ${report.persona_used}` : ''}</p>
<div class="grid">
<div class="panel"><h2>Before</h2>${report.screenshot_b64 ? `<img src="data:image/png;base64,${report.screenshot_b64}">` : '<p>No screenshot</p>'}</div>
<div class="panel"><h2>After</h2><iframe srcDoc="${(report.mockup_html || '').replace(/"/g, '&quot;')}"></iframe></div>
</div>
<div class="audit">${(report.audit_report || '').replace(/</g, '&lt;')}</div>
</body></html>`
    const blob = new Blob([doc], { type: 'text/html' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `ux-audit-${Date.now()}.html`
    a.click()
  }

  const run = async () => {
    setLoading(true); setReport(null); setCrawl(null); setFlow([])
    t0.current = Date.now()
    setStep('Started', crawlMode ? `Crawl · max ${maxPages} pages` : 'Single page', 'active')

    try {
      if (crawlMode) {
        setStep('Crawling', `up to ${maxPages} pages`, 'active')
        const r = await axios.post('/api/ux/crawl', {
          url, persona: isLexful ? persona : undefined,
          max_pages: maxPages, per_page_audit: false,
        }, { timeout: 400000 })
        setStep('Crawl complete', `${r.data.pages_crawled} pages`, 'done')
        setCrawl(r.data)
      } else {
        if (isLexful) setStep('Authenticating', `persona: ${persona}`, 'active')
        setStep('Navigating + screenshot', url, 'active')
        const payload = { generate_mockup: true }
        if (mode === 'url') {
          payload.url = url
          if (isLexful) payload.persona = persona
        } else if (image) {
          payload.image_base64 = await new Promise(res => {
            const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(image)
          })
        }
        const r = await axios.post('/api/ux/analyze', payload, { timeout: 300000 })
        setStep('Screenshot captured', r.data.final_url || url, 'done')
        if (r.data.persona_used) setStep('Authenticated', `as ${r.data.persona_used}`, 'done')
        setStep('Audit complete', `${(r.data.audit_report || '').length} chars`, 'done')
        if (r.data.mockup_html) setStep('Mockup built', `${r.data.mockup_html.length} chars HTML`, 'done')
        setReport(r.data)
      }
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      setStep('Failed', msg.slice(0, 200), 'failed')
      setReport({ error: msg })
    } finally { setLoading(false) }
  }

  return (
    <div className="main-scroll">
      <div className="page-head">
        <div className="page-eyebrow">Workspace</div>
        <h1 className="page-title">UX Audit</h1>
        <p className="page-sub">Score any URL against 5 UX parameters. See the original and redesigned mockup side by side, and download the full report.</p>
      </div>

      <div style={{ padding: '24px 32px 60px', maxWidth: '1200px' }}>
        <div className="card">
          <div className="gap-row" style={{ marginBottom: '18px' }}>
            <button className="ghost"
              style={!crawlMode && mode === 'url' ? { background: 'var(--primary-soft)', color: 'var(--primary)', borderColor: 'var(--primary)' } : {}}
              onClick={() => { setCrawlMode(false); setMode('url') }}>
              <Globe size={14} /> Single URL
            </button>
            <button className="ghost"
              style={!crawlMode && mode === 'upload' ? { background: 'var(--primary-soft)', color: 'var(--primary)', borderColor: 'var(--primary)' } : {}}
              onClick={() => { setCrawlMode(false); setMode('upload') }}>
              <Upload size={14} /> Upload
            </button>
            <button className="ghost"
              style={crawlMode ? { background: 'var(--primary-soft)', color: 'var(--primary)', borderColor: 'var(--primary)' } : {}}
              onClick={() => { setCrawlMode(true); setMode('url') }}>
              <Layers size={14} /> Crawl site
            </button>
          </div>

          {(mode === 'url' || crawlMode) ? (
            <div className="field">
              <label>Target URL</label>
              <input className="input" placeholder="https://e2e-test.uat.lexful.net/docs/assets"
                value={url} onChange={e => setUrl(e.target.value)} disabled={loading} />
            </div>
          ) : (
            <label style={{
              display: 'block', padding: '32px 24px', textAlign: 'center',
              border: '1.5px dashed var(--line-2)', borderRadius: '12px',
              background: 'var(--surface-2)', cursor: 'pointer',
            }}>
              <Upload size={22} style={{ color: 'var(--primary)', marginBottom: '8px' }} />
              <div style={{ fontSize: '13.5px', color: 'var(--ink-2)' }}>
                {image ? image.name : 'Click to upload a screenshot'}
              </div>
              <input type="file" accept="image/*" style={{ display: 'none' }}
                onChange={e => setImage(e.target.files[0])} />
            </label>
          )}

          {isLexful && mode === 'url' && (
            <div className="field" style={{ marginTop: '14px' }}>
              <label>Lexful UAT persona</label>
              <select className="input" value={persona} onChange={e => setPersona(e.target.value)} disabled={loading}>
                <option value="admin">admin — full access</option>
                <option value="support">support — support role</option>
                <option value="viewer">viewer — read only</option>
              </select>
              <div className="field-hint">Stytch cookies are injected before the screenshot — you get the real authenticated page.</div>
            </div>
          )}

          {crawlMode && (
            <div className="field" style={{ marginTop: '14px' }}>
              <label>Max pages</label>
              <input className="input" type="number" min="1" max="50"
                value={maxPages} onChange={e => setMaxPages(parseInt(e.target.value) || 15)}
                disabled={loading} style={{ maxWidth: '160px' }} />
              <div className="field-hint">Follows same-origin links. Screenshots each page.</div>
            </div>
          )}

          <div className="btn-row">
            <button className="primary" onClick={run} disabled={loading || (mode === 'url' ? !url : !image)}>
              {loading ? <Loader2 size={14} className="spin" /> : <Play size={14} />}
              {loading ? 'Working…' : (crawlMode ? `Crawl ${maxPages} pages` : 'Run audit + mockup')}
            </button>
          </div>
        </div>

        {/* ── FLOW DIAGRAM ── */}
        {flow.length > 0 && (
          <div className="flow" style={{ marginTop: '20px' }}>
            {flow.map((f, i) => (
              <div key={i} className={`flow-step ${f.status}`}>
                <div className="flow-step-label">{f.label}</div>
                <div className="flow-step-value">{f.value}</div>
              </div>
            ))}
          </div>
        )}

        {report?.error && (
          <div className="banner error" style={{ marginTop: '20px' }}>{report.error}</div>
        )}

        {report?.audit_report && (
          <>
            <div className="card" style={{ marginTop: '20px' }}>
              <div className="card-hd">
                <div>
                  <div className="card-title">UX Audit Report</div>
                  {report.final_url && (
                    <p className="muted" style={{ fontFamily: 'var(--mono)', fontSize: '11.5px', marginTop: '4px', wordBreak: 'break-all' }}>
                      {report.final_url}
                      {report.persona_used && <> · as <strong>{report.persona_used}</strong></>}
                    </p>
                  )}
                </div>
                <button className="ghost" onClick={downloadReport}>
                  <Download size={14} /> Download report
                </button>
              </div>
              <div className="md"><ReactMarkdown>{report.audit_report}</ReactMarkdown></div>
            </div>

            <MockupViewer
              html={report.mockup_html}
              beforeSrc={report.screenshot_b64 ? `data:image/png;base64,${report.screenshot_b64}` : null}
              auditText={report.audit_report}
            />
          </>
        )}

        {crawl && (
          <div style={{ marginTop: '24px' }}>
            <div className="card" style={{ marginBottom: '16px' }}>
              <div className="card-title">Crawl summary</div>
              <p className="muted" style={{ marginTop: '8px' }}>
                <strong style={{ color: 'var(--ink)' }}>{crawl.pages_crawled}</strong> pages
                {crawl.persona_used && <> · authenticated as <strong style={{ color: 'var(--ink)' }}>{crawl.persona_used}</strong></>}
              </p>
            </div>
            {crawl.pages.map((p, i) => (
              <div key={i} className="card" style={{ marginBottom: '12px' }}>
                <div className="card-hd">
                  <div>
                    <span className="ticket-id">PAGE {i + 1}</span>
                    <div style={{ fontSize: '13px', marginTop: '4px', wordBreak: 'break-all', color: 'var(--ink-2)' }}>{p.url}</div>
                  </div>
                </div>
                {p.error && <div className="banner error">{p.error}</div>}
                {p.audit_report && (
                  <div className="md" style={{ marginTop: '12px' }}><ReactMarkdown>{p.audit_report}</ReactMarkdown></div>
                )}
                {p.mockup_html && (
                  <MockupViewer html={p.mockup_html}
                    beforeSrc={p.screenshot_b64 ? `data:image/png;base64,${p.screenshot_b64}` : null}
                    auditText={p.audit_report} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
