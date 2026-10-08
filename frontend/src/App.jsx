
import React, { useState, useEffect } from 'react'
import { Inbox, Palette, Settings as SettingsIcon, Activity, History as HistoryIcon, FileCode } from 'lucide-react'
import axios from 'axios'
import Tickets from './pages/Tickets'
import UXReview from './pages/UXReview'
import Skills from './pages/Skills'
import SettingsPage from './pages/Settings'
import History from './pages/History'
import Audit from './pages/Audit'

export default function App() {
  const [view, setView] = useState('tickets')
  const [profile, setProfile] = useState({ name: '', role: '' })

  useEffect(() => {
    axios.get('/api/settings').then(r => setProfile(r.data?.profile || {})).catch(() => {})
  }, [view])

  const initials = ((profile?.name || 'You').split(' ').map(s => s[0]).join('') || 'Y').slice(0, 2).toUpperCase()

  const Item = ({ id, icon, label }) => (
    <button className={`nav-item ${view === id ? 'active' : ''}`} onClick={() => setView(id)}>
      {icon} <span>{label}</span>
    </button>
  )

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="brand">
          <div className="brand-mark">AR</div>
          <span>AI Review Hub</span>
        </div>

        <div className="nav-section">
          <div className="nav-label">Workspace</div>
          <Item id="tickets" icon={<Inbox size={15} />} label="Tickets" />
          <Item id="ux" icon={<Palette size={15} />} label="UX Audit" />
        </div>

        <div className="nav-section">
          <div className="nav-label">Reports</div>
          <Item id="history" icon={<HistoryIcon size={15} />} label="History" />
          <Item id="audit" icon={<Activity size={15} />} label="Audit log" />
        </div>

        <div className="nav-section">
          <div className="nav-label">Configure</div>
          <Item id="skills" icon={<FileCode size={15} />} label="Skills" />
          <Item id="settings" icon={<SettingsIcon size={15} />} label="Settings" />
        </div>

        <div className="profile-card" onClick={() => setView('settings')}>
          <div className="avatar">{initials}</div>
          <div className="profile-meta">
            <div className="profile-name">{profile?.name || 'Set your name'}</div>
            <div className="profile-role">{profile?.role || 'Open settings'}</div>
          </div>
        </div>
      </nav>

      <main className="main">
        {view === 'tickets' && <Tickets />}
        {view === 'ux' && <UXReview />}
        {view === 'history' && <div className="main-scroll"><History /></div>}
        {view === 'audit' && <div className="main-scroll"><Audit /></div>}
        {view === 'skills' && <div className="main-scroll"><Skills /></div>}
        {view === 'settings' && <div className="main-scroll"><SettingsPage /></div>}
      </main>
    </div>
  )
}
