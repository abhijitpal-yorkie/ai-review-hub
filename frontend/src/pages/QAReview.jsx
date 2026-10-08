import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Loader2, Send } from 'lucide-react'
import axios from 'axios'
export default function QAReview() {
  const [ticket, setTicket] = useState(''); const [report, setReport] = useState(null); const [loading, setLoading] = useState(false)
  const run = async () => {
    if (!ticket.trim()) return
    setLoading(true); setReport(null)
    try { const r = await axios.post('/api/tickets/generate-from-text', {ticket_text: ticket}); setReport(r.data) }
    catch (e) { setReport({error: e.response?.data?.detail || e.message}) }
    finally { setLoading(false) }
  }
  return (
    <div>
      <h1>QA Test Case Generator</h1>
      <p className="sub">Paste any ticket text to generate + validate test cases (no Linear required).</p>
      <textarea placeholder="Paste your ticket description..." value={ticket} onChange={e=>setTicket(e.target.value)} />
      <button className="primary" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={14} className="spin"/> : <Send size={14}/>}
        {loading ? 'Running pipeline...' : 'Generate + Validate'}
      </button>
      {report?.error && <div className="report" style={{color:'var(--red)'}}>{report.error}</div>}
      {report?.validation && <div className="report"><h2>Validation</h2>
        <p><span className={`badge ${report.validation.passed?'badge-pass':'badge-fail'}`}>{report.validation.passed?'PASSED':'NEEDS WORK'} · {report.validation.overall_score}/100</span></p>
        <p style={{marginTop:'.5rem',fontSize:'.88rem'}}>{report.validation.recommendation}</p></div>}
      {report?.test_cases_markdown && <div className="report"><h2>Test Cases</h2><ReactMarkdown>{report.test_cases_markdown}</ReactMarkdown></div>}
    </div>
  )
}
