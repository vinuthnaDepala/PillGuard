import { useState, useEffect, useRef } from 'react'
import AlertFeed from '../components/AlertFeed'
import { StateBadge, formatTime } from '../components/AlertFeed'

const API = '/api'

export default function Dashboard() {
  const [patient, setPatient] = useState(null)
  const [events, setEvents] = useState(null)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(false)
  const cachedEvents = useRef(null)
  const cachedStats = useRef(null)

  useEffect(() => {
    const fetchAll = () => {
      fetch(`${API}/patient/1`)
        .then((r) => r.json())
        .then(setPatient)
        .catch(() => setError(true))

      fetch(`${API}/events/1?limit=50`)
        .then((r) => r.json())
        .then((data) => { cachedEvents.current = data; setEvents(data) })
        .catch(() => { if (cachedEvents.current) setEvents(cachedEvents.current); setError(true) })

      fetch(`${API}/stats/1`)
        .then((r) => r.json())
        .then((data) => { cachedStats.current = data; setStats(data) })
        .catch(() => { if (cachedStats.current) setStats(cachedStats.current); setError(true) })
    }

    fetchAll()
    const eventsInterval = setInterval(() => {
      fetch(`${API}/events/1?limit=50`)
        .then((r) => r.json())
        .then((data) => { cachedEvents.current = data; setEvents(data); setError(false) })
        .catch(() => { if (cachedEvents.current) setEvents(cachedEvents.current); setError(true) })
    }, 10000)
    const statsInterval = setInterval(() => {
      fetch(`${API}/stats/1`)
        .then((r) => r.json())
        .then((data) => { cachedStats.current = data; setStats(data); setError(false) })
        .catch(() => { if (cachedStats.current) setStats(cachedStats.current); setError(true) })
    }, 30000)

    return () => { clearInterval(eventsInterval); clearInterval(statsInterval) }
  }, [])

  if (!patient && !error) {
    return <div className="text-center py-12 text-slate-400">Loading...</div>
  }

  const lastEvent = events && events.length > 0 ? events[0] : null

  // Build today's schedule status
  const scheduleItems = (patient?.pill_schedule || []).map((entry) => {
    const now = new Date()
    const [h, m] = entry.time.split(':').map(Number)
    const pillTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m)
    const isPast = now > new Date(pillTime.getTime() + 30 * 60000)
    const isCurrent = Math.abs(now - pillTime) <= 30 * 60000

    // Check if there's a TOOK_PILL event near this time today
    const todayStr = now.toISOString().slice(0, 10)
    const taken = events?.some((e) => {
      if (e.state !== 'TOOK_PILL') return false
      const ts = e.timestamp || ''
      if (!ts.startsWith(todayStr)) return false
      const eventTime = new Date(ts + 'Z')
      return Math.abs(eventTime - pillTime) <= 30 * 60000
    })

    let status = 'upcoming'
    if (taken) status = 'taken'
    else if (isPast) status = 'missed'
    else if (isCurrent) status = 'current'

    return { time: entry.time, status }
  })

  // Streak calculation
  let streak = 0
  if (stats?.daily_adherence) {
    const days = [...stats.daily_adherence].reverse()
    for (const d of days) {
      if (d.pct >= 1) streak++
      else break
    }
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm">
          Backend unreachable — showing cached data
        </div>
      )}

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">{patient?.name || 'Patient'}'s Dashboard</h1>
      </div>

      {/* Today's Schedule */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">Today's Schedule</h3>
        {scheduleItems.length === 0 ? (
          <p className="text-slate-400 text-sm">No schedule configured</p>
        ) : (
          <div className="flex gap-4">
            {scheduleItems.map((item) => (
              <div
                key={item.time}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                  item.status === 'taken' ? 'bg-green-50 border-green-200 text-green-700' :
                  item.status === 'missed' ? 'bg-red-50 border-red-200 text-red-700' :
                  item.status === 'current' ? 'bg-blue-50 border-blue-200 text-blue-700' :
                  'bg-slate-50 border-slate-200 text-slate-500'
                }`}
              >
                <span className="font-mono font-medium">{item.time}</span>
                <span className="text-xs capitalize">{item.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Today Taken</p>
          <p className="text-2xl font-bold text-green-600">{stats?.today_taken ?? '—'}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Today Missed</p>
          <p className="text-2xl font-bold text-red-600">{stats?.today_missed ?? '—'}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Week Adherence</p>
          <p className="text-2xl font-bold text-blue-600">{stats?.week_adherence_pct ?? '—'}%</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Current Streak</p>
          <p className="text-2xl font-bold text-purple-600">{streak} day{streak !== 1 ? 's' : ''}</p>
        </div>
      </div>

      {/* Last Event */}
      {lastEvent && (
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-3">Last Event</h3>
          <div className="flex items-center gap-3">
            <StateBadge state={lastEvent.state} />
            <span className="text-sm text-slate-600">{lastEvent.reason}</span>
            <span className="text-xs text-slate-400 ml-auto">{formatTime(lastEvent.timestamp)}</span>
          </div>
        </div>
      )}

      {/* Alert Feed */}
      <AlertFeed events={events || []} />
    </div>
  )
}
