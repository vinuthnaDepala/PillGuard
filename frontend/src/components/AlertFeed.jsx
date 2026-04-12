const STATE_STYLES = {
  TOOK_PILL: {
    bg: '#EDF5EE',
    text: '#4A7A4C',
    border: '#C8DCC9',
    badgeBg: '#C8DCC9',
    badgeText: '#3D5135',
    label: 'Took Pill',
  },
  NO_TAKE: {
    bg: '#FFFBEB',
    text: '#92400E',
    border: '#FDE68A',
    badgeBg: '#FDE68A',
    badgeText: '#78350F',
    label: 'No Take',
  },
  DISTRESS: {
    bg: '#FEF2F2',
    text: '#B91C1C',
    border: '#FECACA',
    badgeBg: '#FECACA',
    badgeText: '#991B1B',
    label: 'Distress',
  },
  NO_SHOW: {
    bg: '#F5F2EB',
    text: '#5A6B5B',
    border: '#E8E2D5',
    badgeBg: '#E8E2D5',
    badgeText: '#4A5568',
    label: 'No Show',
  },
}

function StateBadge({ state }) {
  const style = STATE_STYLES[state] || STATE_STYLES.NO_SHOW
  return (
    <span
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: style.badgeBg, color: style.badgeText }}
    >
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
      <div
        className="rounded-2xl p-6 shadow-sm"
        style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
      >
        <h3 className="text-base font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
          Recent Alerts
        </h3>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No data yet</p>
      </div>
    )
  }

  return (
    <div
      className="rounded-2xl p-6 shadow-sm"
      style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
    >
      <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
        Recent Alerts
      </h3>
      <div className="space-y-2">
        {events.slice(0, 10).map((event) => {
          const style = STATE_STYLES[event.state] || STATE_STYLES.NO_SHOW
          return (
            <div
              key={event.id}
              className="flex items-center justify-between p-3 rounded-xl"
              style={{
                background: style.bg,
                border: `1px solid ${style.border}`,
              }}
            >
              <div className="flex items-center gap-3">
                <StateBadge state={event.state} />
                <span className="text-sm" style={{ color: style.text }}>{event.reason || ''}</span>
              </div>
              <span className="text-xs whitespace-nowrap ml-2" style={{ color: 'var(--text-muted)' }}>
                {formatTime(event.timestamp)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export { StateBadge, formatTime, STATE_STYLES }
