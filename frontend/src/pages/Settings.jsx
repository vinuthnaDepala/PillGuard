import { useState, useEffect } from 'react'

const API = '/api'

export default function Settings() {
  const [patient, setPatient] = useState(null)
  const [name, setName] = useState('')
  const [caretakerName, setCaretakerName] = useState('')
  const [caretakerPhone, setCaretakerPhone] = useState('')
  const [schedule, setSchedule] = useState([])
  const [weeklyPillCount, setWeeklyPillCount] = useState(14)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/patient/1`)
      .then((r) => r.json())
      .then((data) => {
        setPatient(data)
        setName(data.name || '')
        setCaretakerName(data.caretaker_name || '')
        setCaretakerPhone(data.caretaker_phone || '')
        const sched = data.pill_schedule || []
        setSchedule(sched)
        setWeeklyPillCount(data.weekly_pill_count || 14)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const addTime = () => {
    setSchedule([...schedule, { time: '12:00' }])
  }

  const removeTime = (index) => {
    setSchedule(schedule.filter((_, i) => i !== index))
  }

  const updateTime = (index, value) => {
    const updated = [...schedule]
    updated[index] = { time: value }
    setSchedule(updated)
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage('')

    try {
      // Update patient info
      await fetch(`${API}/patient/1`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, caretaker_name: caretakerName, caretaker_phone: caretakerPhone }),
      })

      // Update schedule
      await fetch(`${API}/patient/1/schedule`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pill_schedule: schedule, weekly_pill_count: weeklyPillCount }),
      })

      setMessage('Settings saved successfully!')
    } catch {
      setMessage('Failed to save settings. Is the backend running?')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-slate-400">Loading...</div>
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Settings</h1>

      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
        {/* Patient Name */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Patient Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Caretaker Name */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Caretaker Name</label>
          <input
            type="text"
            value={caretakerName}
            onChange={(e) => setCaretakerName(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Caretaker Phone */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Caretaker Phone</label>
          <input
            type="tel"
            value={caretakerPhone}
            onChange={(e) => setCaretakerPhone(e.target.value)}
            placeholder="+1xxxxxxxxxx"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Pill Schedule */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Pill Schedule</label>
          <div className="space-y-2">
            {schedule.map((entry, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  type="time"
                  value={entry.time}
                  onChange={(e) => updateTime(i, e.target.value)}
                  className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  onClick={() => removeTime(i)}
                  className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={addTime}
            className="mt-2 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors border border-blue-200"
          >
            + Add Time
          </button>
        </div>

        {/* Weekly Pill Count */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Weekly Pill Count</label>
          <input
            type="number"
            min="1"
            value={weeklyPillCount}
            onChange={(e) => setWeeklyPillCount(parseInt(e.target.value) || 1)}
            className="w-32 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Save */}
        <div className="pt-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          {message && (
            <p className={`mt-2 text-sm ${message.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
              {message}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
