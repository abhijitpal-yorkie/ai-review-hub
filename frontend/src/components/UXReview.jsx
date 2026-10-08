import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Loader2, Globe, Upload } from 'lucide-react'
import axios from 'axios'
import MockupViewer from './MockupViewer'

export default function UXReview() {
  const [mode, setMode] = useState('url')
  const [url, setUrl] = useState('')
  const [image, setImage] = useState(null)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true); setReport(null)
    try {
      const payload = { generate_mockup: true }
      if (mode === 'url') payload.url = url
      else if (image) {
        const reader = new FileReader()
        const b64 = await new Promise(res => { reader.onload = () => res(reader.result); reader.readAsDataURL(image) })
        payload.image_base64 = b64
      }
      const res = await axios.post('/api/ux/analyze', payload)
      setReport(res.data)
    } catch (e) {
      setReport({ error: e.response?.data?.detail || e.message })
    } finally { setLoading(false) }
  }

  return (
    <div>
      <h1>UX Audit & Mockup Generator</h1>
      <div className="mode-toggle">
        <button className={mode==='url'?'active':''} onClick={()=>setMode('url')}><Globe size={16}/> URL</button>
        <button className={mode==='upload'?'active':''} onClick={()=>setMode('upload')}><Upload size={16}/> Upload</button>
      </div>
      {mode==='url'
        ? <input type="text" placeholder="https://example.com" value={url} onChange={e=>setUrl(e.target.value)}/>
        : <div className="file-upload"><input type="file" accept="image/*" onChange={e=>setImage(e.target.files[0])}/></div>}
      <button className="primary" onClick={run} disabled={loading || (mode==='url'?!url:!image)}>
        {loading ? <Loader2 size={16} className="spin"/> : <Globe size={16}/>}
        {loading ? 'Analyzing...' : 'Run UX Audit + Build Mockup'}
      </button>
      {report?.error && <div className="report" style={{color:'var(--red)'}}>Error: {report.error}</div>}
      {report?.audit_report && (
        <div className="report">
          <h2>UX Audit</h2>
          <ReactMarkdown>{report.audit_report}</ReactMarkdown>
        </div>
      )}
      {report?.mockup_html && <MockupViewer html={report.mockup_html} />}
    </div>
  )
}
