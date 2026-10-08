import React from 'react'
export default function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <p className="sub">Multi-agent QA + UX pipeline with Linear integration.</p>
      <div className="card-grid">
        <div className="stat"><h3>QA Cycles / day</h3><div className="value">~750</div><small>Gemini Flash-Lite + Groq fallback</small></div>
        <div className="stat"><h3>UX Reviews / day</h3><div className="value">~40</div><small>Gemini 2.5 Flash + NVIDIA fallback</small></div>
        <div className="stat"><h3>Active Agents</h3><div className="value">5</div><small>Generate · Validate · Execute · Audit · Mockup</small></div>
        <div className="stat"><h3>Linear Connected</h3><div className="value">✓</div><small>Webhook + API key configured</small></div>
      </div>
      <div className="card">
        <h2>Workflow</h2>
        <p style={{fontSize:'.9rem'}}>
          <strong>1.</strong> Linear tickets sync automatically via webhook → appear in Tickets.<br/>
          <strong>2.</strong> Click a ticket → generate test cases → validate.<br/>
          <strong>3.</strong> Execute individual or all test cases against your UAT URL.<br/>
          <strong>4.</strong> Report (with annotated screenshots) is posted back to the Linear ticket.
        </p>
      </div>
    </div>
  )
}
