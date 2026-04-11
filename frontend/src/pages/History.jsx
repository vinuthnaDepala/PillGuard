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
    return <div className="text-center py-12 text-slate-400">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Medication History</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CalendarHeatmap dailyAdherence={stats?.daily_adherence || []} />
        <AdherenceChart dailyAdherence={stats?.daily_adherence || []} />
      </div>

      {/* Event Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">All Events</h3>
        </div>
        {!events || events.length === 0 ? (
          <div className="p-6 text-slate-400 text-sm">No data yet</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3">State</th>
                  <th className="px-6 py-3">Confidence</th>
                  <th className="px-6 py-3">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {events.map((event) => (
                  <tr key={event.id} className="hover:bg-slate-50">
                    <td className="px-6 py-3 text-sm text-slate-600 whitespace-nowrap">{formatTime(event.timestamp)}</td>
                    <td className="px-6 py-3"><StateBadge state={event.state} /></td>
                    <td className="px-6 py-3 text-sm text-slate-600">
                      {event.confidence != null ? `${Math.round(event.confidence * 100)}%` : '—'}
                    </td>
                    <td className="px-6 py-3 text-sm text-slate-600">{event.reason || '—'}</td>
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
