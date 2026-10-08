import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Loader2, Send } from 'lucide-react'
import axios from 'axios'

export default function QAReview() {
  const [ticket, setTicket] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [execute, setExecute] = useState(false)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    if (!ticket.trim()) return
    setLoading(true); setReport(null)
    try {
      const res = await axios.post('/api/qa/generate', {
        ticket_text: ticket, base_url: baseUrl || null, execute_tests: execute && !!baseUrl
      })
      setReport(res.data)
    } catch (e) {
      setReport({ error: e.response?.data?.detail || e.message })
    } finally { setLoading(false) }
  }

  return (
    <div>
      <h1>QA Test Case Generator</h1>
      <textarea placeholder="Paste your ticket description..." value={ticket} onChange={e=>setTicket(e.target.value)} />
      <div style={{display:'flex',gap:'1rem',marginTop:'1rem',alignItems:'center',flexWrap:'wrap'}}>
        <input type="text" placeholder="UAT URL (optional, e.g. https://staging.example.com)" value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} style={{flex:1,minWidth:'280px'}}/>
        <label style={{display:'flex',alignItems:'center',gap:'.5rem',color:'var(--text2)',fontSize:'.85rem',cursor:'pointer'}}>
          <input type="checkbox" checked={execute} onChange={e=>setExecute(e.target.checked)}/> Execute on UAT
        </label>
      </div>
      <button className="primary" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={16} className="spin"/> : <Send size={16}/>}
        {loading ? 'Running pipeline...' : 'Generate + Validate'}
      </button>
      {report?.error && <div className="report" style={{color:'var(--red)'}}>Error: {report.error}</div>}
      {report?.validation && (
        <div className="report">
          <h2>Validation Report</h2>
          <p><span className={`score-badge ${report.validation.passed?'score-pass':'score-fail'}`}>
            {report.validation.passed?'PASSED':'NEEDS IMPROVEMENT'} · {report.validation.overall_score}/100
          </span></p>
          <p style={{marginTop:'.75rem',color:'var(--text2)',fontSize:'.9rem'}}>{report.validation.recommendation}</p>
          {report.validation.gaps?.length>0 && <><h3>Gaps</h3><ul style={{paddingLeft:'1.25rem',color:'var(--text2)'}}>{report.validation.gaps.map((g,i)=><li key={i}>{g}</li>)}</ul></>}
        </div>
      )}
      {report?.test_cases_markdown && (
        <div className="report">
          <h2>Generated Test Cases</h2>
          <ReactMarkdown>{report.test_cases_markdown}</ReactMarkdown>
        </div>
      )}
      {report?.executions?.length>0 && (
        <div className="report">
          <h2>UAT Execution Results</h2>
          {report.executions.map((x,i)=><p key={i}><strong>{x.test_id}</strong> — <span className={`score-badge ${x.status==='PASS'?'score-pass':'score-fail'}`}>{x.status}</span></p>)}
        </div>
      )}
    </div>
  )
}
