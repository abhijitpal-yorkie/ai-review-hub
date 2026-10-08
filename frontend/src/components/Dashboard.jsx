import React from 'react'
export default function Dashboard() {
  return (
    <div>
      <h1>Welcome to AI Review Hub</h1>
      <p style={{color:'var(--text2)'}}>Multi-agent QA + UX pipeline powered by free-tier LLMs.</p>
      <div className="card-grid">
        <div className="stat"><h3>QA Cycles / day</h3><div className="value">~750</div><small>Gemini Flash-Lite + Groq fallback</small></div>
        <div className="stat"><h3>UX Reviews / day</h3><div className="value">~40</div><small>Gemini 2.5 Flash + NVIDIA fallback</small></div>
        <div className="stat"><h3>Active Agents</h3><div className="value">5</div><small>Generate · Validate · Execute · Audit · Mockup</small></div>
        <div className="stat"><h3>Providers</h3><div className="value">5</div><small>Gemini · Groq · Cerebras · NVIDIA · OpenRouter</small></div>
      </div>
      <div className="card">
        <h2>How it works</h2>
        <p style={{color:'var(--text2)',fontSize:'.9rem'}}>
          <strong>QA pipeline:</strong> Paste a ticket → Agent 1 generates test cases → Agent 2 validates coverage/semantics → Agent 3 executes against your UAT URL (optional).<br/><br/>
          <strong>UX pipeline:</strong> Enter a URL or upload a screenshot → Agent 4 audits 5 UX parameters → Agent 5 builds an HTML mockup with improvements, preserving the original style.
        </p>
      </div>
    </div>
  )
}
