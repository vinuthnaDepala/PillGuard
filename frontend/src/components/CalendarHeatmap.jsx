const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function getDayColor(pct) {
  if (pct === null || pct === undefined) return 'bg-slate-100'
  if (pct >= 0.8) return 'bg-green-400'
  if (pct >= 0.5) return 'bg-green-200'
  if (pct > 0) return 'bg-red-300'
  return 'bg-red-400'
}

export default function CalendarHeatmap({ dailyAdherence = [] }) {
  if (dailyAdherence.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">Calendar Heatmap</h3>
        <p className="text-slate-400 text-sm">No data yet</p>
      </div>
    )
  }

  // Build a map for quick lookup
  const adherenceMap = {}
  dailyAdherence.forEach((d) => {
    adherenceMap[d.date] = d.pct
  })

  // Build grid: last 30 days
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
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-3">Calendar Heatmap</h3>
      <div className="flex flex-wrap gap-1.5">
        {days.map((d) => (
          <div
            key={d.date}
            title={`${d.date}: ${d.pct !== null ? Math.round(d.pct * 100) + '%' : 'No data'}`}
            className={`w-8 h-8 rounded-md flex items-center justify-center text-xs font-medium ${getDayColor(d.pct)} ${
              d.pct !== null ? 'text-white' : 'text-slate-400'
            }`}
          >
            {d.day}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
        <div className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-400 inline-block"></span> Taken</div>
        <div className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-400 inline-block"></span> Missed</div>
        <div className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-slate-100 inline-block"></span> No data</div>
      </div>
    </div>
  )
}
