import { useState, useEffect } from 'react'
import { Play, Square, ExternalLink, Activity, Database } from 'lucide-react'
import './index.css'

function App() {
  const [leads, setLeads] = useState([])
  const [status, setStatus] = useState('stopped')
  const [loading, setLoading] = useState(true)

  const API_BASE = "http://localhost:8000/api"

  const fetchLeads = async () => {
    try {
      const res = await fetch(`${API_BASE}/leads`)
      const data = await res.json()
      setLeads(data.leads || [])
    } catch (err) {
      console.error("Failed to fetch leads", err)
    }
  }

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`)
      const data = await res.json()
      setStatus(data.status)
      setLoading(false)
    } catch (err) {
      console.error("Failed to fetch status", err)
      setLoading(false)
    }
  }

  const toggleEngine = async () => {
    try {
      const endpoint = status === 'running' ? '/engine/stop' : '/engine/start'
      await fetch(`${API_BASE}${endpoint}`, { method: 'POST' })
      setTimeout(fetchStatus, 1000)
    } catch (err) {
      console.error("Failed to toggle engine", err)
    }
  }

  useEffect(() => {
    fetchLeads()
    fetchStatus()
    // Poll every 10 seconds for new leads and status
    const interval = setInterval(() => {
      fetchLeads()
      fetchStatus()
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="dashboard-container">
      <header className="header">
        <div>
          <h1 className="title">JobShield</h1>
          <p style={{color: 'var(--text-muted)', margin: '0.5rem 0 0 0'}}>B2B Lead Generation Engine</p>
        </div>
        
        <div className="controls">
          <div className="status-badge glass-panel">
            <div className={`status-dot ${status}`}></div>
            {status === 'running' ? 'Engine Active' : 'Engine Offline'}
          </div>
          
          <button 
            className={`btn ${status === 'running' ? 'btn-danger' : 'btn-primary'}`}
            onClick={toggleEngine}
            disabled={loading}
          >
            {status === 'running' ? (
              <><Square size={18} /> Stop Engine</>
            ) : (
              <><Play size={18} /> Start Engine</>
            )}
          </button>
        </div>
      </header>

      <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem'}}>
        <Database size={20} color="var(--primary)" />
        <h2 style={{margin: 0, fontSize: '1.25rem'}}>Latest Prospects</h2>
      </div>

      <div className="leads-grid">
        {leads.length === 0 ? (
          <div className="glass-panel" style={{gridColumn: '1 / -1', textAlign: 'center', padding: '3rem'}}>
            <Activity size={48} color="var(--text-muted)" style={{marginBottom: '1rem', opacity: 0.5}} />
            <h3 style={{margin: 0, color: 'var(--text-main)'}}>No Leads Yet</h3>
            <p style={{color: 'var(--text-muted)'}}>Start the engine to begin scraping high-ticket jobs.</p>
          </div>
        ) : (
          leads.map((lead) => (
            <div key={lead.id} className="lead-card glass-panel">
              <div className="lead-header">
                <h3 className="lead-title">{lead.title}</h3>
              </div>
              <div style={{marginBottom: '1rem'}}>
                <span className="lead-budget">{lead.budget}</span>
              </div>
              <p className="lead-desc">{lead.description}</p>
              
              <div className="lead-footer">
                <span className="lead-time">Found: {new Date(lead.timestamp).toLocaleTimeString()}</span>
                <a href={lead.url} target="_blank" rel="noopener noreferrer" className="lead-link">
                  View Job <ExternalLink size={14} />
                </a>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default App
