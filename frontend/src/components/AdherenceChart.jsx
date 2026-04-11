import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

function linearRegression(data) {
  const n = data.length
  if (n < 2) return { slope: 0, intercept: 0 }

  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0
  data.forEach((d, i) => {
    sumX += i
    sumY += d.pct
    sumXY += i * d.pct
    sumX2 += i * i
  })

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
  const intercept = (sumY - slope * sumX) / n
  return { slope, intercept }
}

export default function AdherenceChart({ dailyAdherence = [] }) {
  if (dailyAdherence.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">30-Day Adherence Trend</h3>
        <p className="text-slate-400 text-sm">No data yet</p>
      </div>
    )
  }

  const { slope, intercept } = linearRegression(dailyAdherence)
  const chartData = dailyAdherence.map((d, i) => ({
    date: d.date.slice(5), // "MM-DD"
    pct: Math.round(d.pct * 100),
    trend: Math.round(Math.max(0, Math.min(100, (intercept + slope * i) * 100))),
  }))

  // Current week adherence
  const lastWeek = dailyAdherence.slice(-7)
  const weekAvg = lastWeek.reduce((sum, d) => sum + d.pct, 0) / lastWeek.length
  const showWarning = slope < 0 && weekAvg < 0.7

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-3">30-Day Adherence Trend</h3>
      {showWarning && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm font-medium">
          Adherence declining — consult physician
        </div>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="#94a3b8" unit="%" />
          <Tooltip formatter={(val) => `${val}%`} />
          <Legend />
          <Line type="monotone" dataKey="pct" name="Adherence" stroke="#3b82f6" strokeWidth={2} dot={{ r: 2 }} />
          <Line type="monotone" dataKey="trend" name="Trend" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
