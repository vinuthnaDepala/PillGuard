const STATE_STYLES = {
  TOOK_PILL: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-200', label: 'Took Pill' },
  NO_TAKE:   { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-200', label: 'No Take' },
  DISTRESS:  { bg: 'bg-red-100',   text: 'text-red-800',   border: 'border-red-200',   label: 'Distress' },
  NO_SHOW:   { bg: 'bg-gray-100',  text: 'text-gray-800',  border: 'border-gray-200',  label: 'No Show' },
}

function StateBadge({ state }) {
  const style = STATE_STYLES[state] || STATE_STYLES.NO_SHOW
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  )
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp + 'Z')
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function AlertFeed({ events = [] }) {
  if (events.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">Recent Alerts</h3>
        <p className="text-slate-400 text-sm">No data yet</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-3">Recent Alerts</h3>
      <div className="space-y-2">
        {events.slice(0, 10).map((event) => (
          <div
            key={event.id}
            className={`flex items-center justify-between p-3 rounded-lg border ${STATE_STYLES[event.state]?.border || 'border-slate-200'} ${STATE_STYLES[event.state]?.bg || 'bg-slate-50'}`}
          >
            <div className="flex items-center gap-3">
              <StateBadge state={event.state} />
              <span className="text-sm text-slate-600">{event.reason || ''}</span>
            </div>
            <span className="text-xs text-slate-400 whitespace-nowrap ml-2">{formatTime(event.timestamp)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export { StateBadge, formatTime, STATE_STYLES }
