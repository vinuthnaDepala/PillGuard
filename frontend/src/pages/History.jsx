import { useState, useEffect } from 'react'
import AdherenceChart from '../components/AdherenceChart'
import CalendarHeatmap from '../components/CalendarHeatmap'
import { StateBadge, formatTime } from '../components/AlertFeed'

const API = '/api'

export default function History() {
  const [events, setEvents] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API}/events/1?limit=200`).then((r) => r.json()),
      fetch(`${API}/stats/1`).then((r) => r.json()),
    ])
      .then(([eventsData, statsData]) => {
        setEvents(eventsData)
        setStats(statsData)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
        Loading...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Medication History
        </h1>
        <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
          30-day trends and full event log
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CalendarHeatmap dailyAdherence={stats?.daily_adherence || []} />
        <AdherenceChart dailyAdherence={stats?.daily_adherence || []} />
      </div>

      {/* Event Table */}
      <div
        className="rounded-2xl overflow-hidden shadow-sm"
        style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
      >
        <div
          className="px-6 py-4"
          style={{ borderBottom: '1px solid var(--cream-border)' }}
        >
          <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            All Events
          </h3>
        </div>
        {!events || events.length === 0 ? (
          <div className="p-6 text-sm" style={{ color: 'var(--text-muted)' }}>No data yet</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr
                  className="text-left"
                  style={{ background: 'var(--sage-xlight)' }}
                >
                  {['Timestamp', 'State', 'Confidence', 'Reason'].map((h) => (
                    <th
                      key={h}
                      className="px-6 py-3 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--sage-dark)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {events.map((event, idx) => (
                  <tr
                    key={event.id}
                    style={{
                      borderTop: '1px solid var(--cream-border)',
                      background: idx % 2 === 0 ? 'var(--cream-card)' : 'var(--cream)',
                    }}
                    className="transition-colors hover:brightness-95"
                  >
                    <td className="px-6 py-3 text-sm whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
                      {formatTime(event.timestamp)}
                    </td>
                    <td className="px-6 py-3">
                      <StateBadge state={event.state} />
                    </td>
                    <td className="px-6 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                      {event.confidence != null ? `${Math.round(event.confidence * 100)}%` : '—'}
                    </td>
                    <td className="px-6 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                      {event.reason || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
