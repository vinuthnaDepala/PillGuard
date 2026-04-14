function getDayColor(pct) {
  if (pct === null || pct === undefined) return { bg: '#F0EDE6', text: '#A89B8C' }
  if (pct >= 0.8) return { bg: '#4A7A4C', text: '#ffffff' }
  if (pct >= 0.5) return { bg: '#8BAF8C', text: '#ffffff' }
  if (pct > 0)   return { bg: '#F4A261', text: '#ffffff' }
  return { bg: '#E05C5C', text: '#ffffff' }
}

export default function CalendarHeatmap({ dailyAdherence = [] }) {
  if (dailyAdherence.length === 0) {
    return (
      <div
        className="rounded-2xl p-6 shadow-sm"
        style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
      >
        <h3 className="text-base font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
          Calendar Heatmap
        </h3>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No data yet</p>
      </div>
    )
  }

  const adherenceMap = {}
  dailyAdherence.forEach((d) => {
    adherenceMap[d.date] = d.pct
  })

  const days = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().slice(0, 10)
    days.push({
      date: dateStr,
      dayOfWeek: d.getDay(),
      day: d.getDate(),
      pct: adherenceMap[dateStr] ?? null,
    })
  }

  return (
    <div
      className="rounded-2xl p-6 shadow-sm"
      style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
    >
      <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
        Calendar Heatmap
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {days.map((d) => {
          const { bg, text } = getDayColor(d.pct)
          return (
            <div
              key={d.date}
              title={`${d.date}: ${d.pct !== null ? Math.round(d.pct * 100) + '%' : 'No data'}`}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-semibold shadow-sm transition-transform hover:scale-110"
              style={{ background: bg, color: text }}
            >
              {d.day}
            </div>
          )
        })}
      </div>
      <div className="flex items-center gap-5 mt-4 text-xs" style={{ color: 'var(--text-muted)' }}>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm inline-block" style={{ background: '#4A7A4C' }}></span>
          Full
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm inline-block" style={{ background: '#8BAF8C' }}></span>
          Partial
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm inline-block" style={{ background: '#E05C5C' }}></span>
          Missed
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm inline-block" style={{ background: '#F0EDE6' }}></span>
          No data
        </div>
      </div>
    </div>
  )
}
