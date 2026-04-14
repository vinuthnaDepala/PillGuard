import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Settings from './pages/Settings'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/history', label: 'History' },
  { to: '/settings', label: 'Settings' },
]

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen" style={{ background: 'var(--cream)' }}>
        <nav style={{ background: 'var(--olive)', borderBottom: '1px solid #2a3924' }} className="shadow-lg">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-lg shadow-sm"
                  style={{ background: 'var(--sage)' }}
                >
                  💊
                </div>
                <span className="text-xl font-bold text-white tracking-tight">PillGuard</span>
              </div>
              <div className="flex gap-1">
                {NAV_ITEMS.map(({ to, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={to === '/'}
                    className={({ isActive }) =>
                      `px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        isActive
                          ? 'text-white'
                          : 'text-green-200 hover:text-white hover:bg-white/10'
                      }`
                    }
                    style={({ isActive }) =>
                      isActive ? { background: 'var(--sage-dark)' } : {}
                    }
                  >
                    {label}
                  </NavLink>
                ))}
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
