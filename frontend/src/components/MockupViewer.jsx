import React, { useState } from 'react'
import { Download } from 'lucide-react'

export default function MockupViewer({ html, beforeSrc, auditText }) {
  const [view, setView] = useState('split')

  const download = () => {
    const doc = `<!doctype html><html><head><meta charset="utf-8"><title>UX Audit Report</title>
<style>body{font-family:system-ui;max-width:1400px;margin:2rem auto;padding:1rem;color:#1a1a1a}
h1{margin:0 0 1rem}.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1rem 0}
.panel{border:1px solid #ddd;border-radius:12px;overflow:hidden;background:#fff}
.panel h2{margin:0;padding:.75rem 1rem;background:#f4f8f4;font-size:.9rem;border-bottom:1px solid #e5e5e0}
.panel img{max-width:100%;display:block}.panel iframe{width:100%;height:800px;border:0}
.audit{background:#fafaf7;padding:1.5rem;border-radius:12px;margin-top:2rem;white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace;font-size:.85rem}
</style></head><body>
<h1>UX Audit Report</h1>
<p>Generated ${new Date().toISOString()}</p>
<div class="grid">
<div class="panel"><h2>BEFORE</h2>${beforeSrc ? `<img src="${beforeSrc}">` : '<p>No screenshot</p>'}</div>
<div class="panel"><h2>AFTER (mockup)</h2><iframe srcDoc="${(html || '').replace(/"/g, '&quot;')}"></iframe></div>
</div>
<div class="audit">${(auditText || '').replace(/</g, '&lt;')}</div>
</body></html>`
    const blob = new Blob([doc], { type: 'text/html' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `ux-audit-${Date.now()}.html`
    a.click()
  }

  return (
    <div className="mockup-viewer">
      <div className="mockup-toolbar" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex' }}>
          <button className={view==='split'?'active':''} onClick={()=>setView('split')}>Before + After</button>
          <button className={view==='before'?'active':''} onClick={()=>setView('before')}>Before only</button>
          <button className={view==='after'?'active':''} onClick={()=>setView('after')}>After only</button>
        </div>
        <button onClick={download} style={{ padding: '.5rem 1rem', display: 'inline-flex', alignItems: 'center', gap: '.4rem' }}>
          <Download size={14} /> Download report
        </button>
      </div>

      <div style={{ display: 'grid',
                    gridTemplateColumns: view==='split' ? '1fr 1fr' : '1fr',
                    gap: '1px', background: 'var(--border)' }}>
        {(view === 'split' || view === 'before') && (
          <div style={{ background: '#fff', minHeight: '500px' }}>
            <div style={{ padding: '.5rem 1rem', background: 'var(--surface-2)', fontSize: '.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em' }}>Before</div>
            {beforeSrc
              ? <img src={beforeSrc} alt="Original screenshot" style={{ width: '100%', display: 'block' }} />
              : <div style={{ padding: '2rem', color: 'var(--text-3)', textAlign: 'center' }}>No screenshot available</div>}
          </div>
        )}
        {(view === 'split' || view === 'after') && (
          <div style={{ background: '#fff', minHeight: '500px' }}>
            <div style={{ padding: '.5rem 1rem', background: 'var(--surface-2)', fontSize: '.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em' }}>After (mockup)</div>
            <iframe srcDoc={html} title="Improved mockup" sandbox="allow-scripts"
                    style={{ width: '100%', height: '500px', border: 0 }} />
          </div>
        )}
      </div>
    </div>
  )
}
