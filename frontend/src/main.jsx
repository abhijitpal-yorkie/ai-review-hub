import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

class ErrorBoundary extends React.Component {
  constructor(p){ super(p); this.state = {err: null, info: null} }
  componentDidCatch(err, info){ this.setState({err, info}) }
  render(){
    if (this.state.err) {
      return (
        <div style={{padding:'2rem',fontFamily:'monospace',background:'#fef2f2',color:'#7f1d1d',minHeight:'100vh'}}>
          <h2 style={{marginBottom:'1rem'}}>App crashed — paste this to me:</h2>
          <pre style={{whiteSpace:'pre-wrap',fontSize:'.8rem',background:'white',padding:'1rem',borderRadius:'8px',overflow:'auto'}}>
            {String(this.state.err?.stack || this.state.err)}
            {'\n\nComponent stack:\n'}
            {this.state.info?.componentStack}
          </pre>
        </div>
      )
    }
    return this.props.children
  }
}

try {
  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <ErrorBoundary><App /></ErrorBoundary>
    </React.StrictMode>
  )
} catch (e) {
  document.getElementById('root').innerHTML =
    '<pre style="padding:2rem;color:red;font-family:monospace">Boot error: '+e.message+'\n'+e.stack+'</pre>'
}
