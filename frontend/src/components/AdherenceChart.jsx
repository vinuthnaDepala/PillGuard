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
      <div
        className="rounded-2xl p-6 shadow-sm"
        style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
      >
        <h3 className="text-base font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
          30-Day Adherence Trend
        </h3>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No data yet</p>
      </div>
    )
  }

  const { slope, intercept } = linearRegression(dailyAdherence)
  const chartData = dailyAdherence.map((d, i) => ({
    date: d.date.slice(5),
    pct: Math.round(d.pct * 100),
    trend: Math.round(Math.max(0, Math.min(100, (intercept + slope * i) * 100))),
  }))

  const lastWeek = dailyAdherence.slice(-7)
  const weekAvg = lastWeek.reduce((sum, d) => sum + d.pct, 0) / lastWeek.length
  const showWarning = slope < 0 && weekAvg < 0.7

  return (
    <div
      className="rounded-2xl p-6 shadow-sm"
      style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
    >
      <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
        30-Day Adherence Trend
      </h3>
      {showWarning && (
        <div
          className="mb-4 p-3 rounded-xl text-sm font-medium"
          style={{ background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C' }}
        >
          Adherence declining — consult physician
        </div>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8E2D5" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#8A9E8B' }} stroke="#D4E4D5" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#8A9E8B' }} stroke="#D4E4D5" unit="%" />
          <Tooltip
            contentStyle={{
              background: 'var(--cream-card)',
              border: '1px solid var(--cream-border)',
              borderRadius: '0.75rem',
              fontSize: '0.8rem',
            }}
            formatter={(val) => `${val}%`}
          />
          <Legend
            wrapperStyle={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}
          />
          <Line
            type="monotone"
            dataKey="pct"
            name="Adherence"
            stroke="#4A7A4C"
            strokeWidth={2.5}
            dot={{ r: 2.5, fill: '#4A7A4C' }}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="trend"
            name="Trend"
            stroke="#C8A96E"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
