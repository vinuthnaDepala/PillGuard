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
    return (
      <div className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
        Loading...
      </div>
    )
  }

  const lastEvent = events && events.length > 0 ? events[0] : null

  const scheduleItems = (patient?.pill_schedule || []).map((entry) => {
    const now = new Date()
    const [h, m] = entry.time.split(':').map(Number)
    const pillTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m)
    const isPast = now > new Date(pillTime.getTime() + 30 * 60000)
    const isCurrent = Math.abs(now - pillTime) <= 30 * 60000

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

  let streak = 0
  if (stats?.daily_adherence) {
    const days = [...stats.daily_adherence].reverse()
    for (const d of days) {
      if (d.pct >= 1) streak++
      else break
    }
  }

  const scheduleStatusStyles = {
    taken: {
      background: 'var(--sage-xlight)',
      border: '1px solid var(--sage-light)',
      color: 'var(--sage-dark)',
    },
    missed: {
      background: '#FEF2F2',
      border: '1px solid #FECACA',
      color: '#B91C1C',
    },
    current: {
      background: '#EFF6FF',
      border: '1px solid #BFDBFE',
      color: '#1D4ED8',
    },
    upcoming: {
      background: 'var(--cream)',
      border: '1px solid var(--cream-border)',
      color: 'var(--text-muted)',
    },
  }

  return (
    <div className="space-y-6">
      {error && (
        <div
          className="p-3 rounded-xl text-sm"
          style={{
            background: '#FFFBEB',
            border: '1px solid #FDE68A',
            color: '#92400E',
          }}
        >
          Backend unreachable — showing cached data
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {patient?.name || 'Patient'}'s Dashboard
          </h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Medication tracking overview
          </p>
        </div>
        <div
          className="px-4 py-2 rounded-xl text-sm font-medium text-white shadow-sm"
          style={{ background: 'var(--olive)' }}
        >
          Live
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Today Taken', value: stats?.today_taken ?? '—', color: 'var(--sage-dark)', icon: '✓' },
          { label: 'Today Missed', value: stats?.today_missed ?? '—', color: '#B91C1C', icon: '⚠️' },
          { label: 'Week Adherence', value: stats?.week_adherence_pct != null ? `${stats.week_adherence_pct}%` : '—', color: 'var(--sage-dark)', icon: '📊' },
          { label: 'Current Streak', value: `${streak}d`, color: 'var(--olive)', icon: '🔥' },
        ].map(({ label, value, color, icon }) => (
          <div
            key={label}
            className="rounded-2xl p-5 shadow-sm"
            style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{label}</p>
              <span className="text-base">{icon}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Today's Schedule */}
      <div
        className="rounded-2xl p-6 shadow-sm"
        style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
      >
        <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
          Today's Schedule
        </h3>
        {scheduleItems.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No schedule configured</p>
        ) : (
          <div className="flex flex-wrap gap-3">
            {scheduleItems.map((item) => (
              <div
                key={item.time}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl"
                style={scheduleStatusStyles[item.status]}
              >
                <span className="font-mono font-semibold text-sm">{item.time}</span>
                <span className="text-xs capitalize opacity-80">{item.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Last Event */}
      {lastEvent && (
        <div
          className="rounded-2xl p-6 shadow-sm"
          style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
        >
          <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Last Event
          </h3>
          <div className="flex items-center gap-3">
            <StateBadge state={lastEvent.state} />
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{lastEvent.reason}</span>
            <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>
              {formatTime(lastEvent.timestamp)}
            </span>
          </div>
        </div>
      )}

      {/* Alert Feed */}
      <AlertFeed events={events || []} />
    </div>
  )
}
