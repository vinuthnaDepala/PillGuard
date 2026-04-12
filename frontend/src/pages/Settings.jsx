import { useState, useEffect } from 'react'

const API = '/api'

const inputStyle = {
  width: '100%',
  padding: '0.6rem 0.75rem',
  border: '1px solid var(--cream-border)',
  borderRadius: '0.75rem',
  fontSize: '0.875rem',
  background: 'var(--cream)',
  color: 'var(--text-primary)',
  outline: 'none',
  transition: 'border-color 0.15s, box-shadow 0.15s',
  boxSizing: 'border-box',
}

const inputFocusStyle = {
  borderColor: 'var(--sage)',
  boxShadow: '0 0 0 3px rgba(139,175,140,0.18)',
}

function StyledInput({ style, ...props }) {
  const [focused, setFocused] = useState(false)
  return (
    <input
      {...props}
      style={{ ...inputStyle, ...(focused ? inputFocusStyle : {}), ...style }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  )
}

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
      await fetch(`${API}/patient/1`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, caretaker_name: caretakerName, caretaker_phone: caretakerPhone }),
      })

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
    return (
      <div className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
        Loading...
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Settings
        </h1>
        <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
          Manage patient and caretaker information
        </p>
      </div>

      <div
        className="rounded-2xl p-6 shadow-sm space-y-5"
        style={{ background: 'var(--cream-card)', border: '1px solid var(--cream-border)' }}
      >
        {/* Section: Patient Info */}
        <div>
          <p
            className="text-xs font-semibold uppercase tracking-wider mb-4"
            style={{ color: 'var(--sage-dark)' }}
          >
            Patient Information
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                Patient Name
              </label>
              <StyledInput
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                Caretaker Name
              </label>
              <StyledInput
                type="text"
                value={caretakerName}
                onChange={(e) => setCaretakerName(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                Caretaker Phone
              </label>
              <StyledInput
                type="tel"
                value={caretakerPhone}
                onChange={(e) => setCaretakerPhone(e.target.value)}
                placeholder="+1xxxxxxxxxx"
              />
            </div>
          </div>
        </div>

        {/* Divider */}
        <div style={{ borderTop: '1px solid var(--cream-border)' }} />

        {/* Section: Schedule */}
        <div>
          <p
            className="text-xs font-semibold uppercase tracking-wider mb-4"
            style={{ color: 'var(--sage-dark)' }}
          >
            Pill Schedule
          </p>
          <div className="space-y-2">
            {schedule.map((entry, i) => (
              <div key={i} className="flex items-center gap-3">
                <input
                  type="time"
                  value={entry.time}
                  onChange={(e) => updateTime(i, e.target.value)}
                  style={{
                    ...inputStyle,
                    width: 'auto',
                  }}
                />
                <button
                  onClick={() => removeTime(i)}
                  className="px-3 py-2 text-sm rounded-xl transition-colors"
                  style={{
                    color: '#B91C1C',
                    background: '#FEF2F2',
                    border: '1px solid #FECACA',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#FEE2E2'}
                  onMouseLeave={(e) => e.currentTarget.style.background = '#FEF2F2'}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={addTime}
            className="mt-3 px-4 py-2 text-sm rounded-xl transition-colors font-medium"
            style={{
              color: 'var(--sage-dark)',
              background: 'var(--sage-xlight)',
              border: '1px solid var(--sage-light)',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--sage-light)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'var(--sage-xlight)'}
          >
            + Add Time
          </button>
        </div>

        {/* Divider */}
        <div style={{ borderTop: '1px solid var(--cream-border)' }} />

        {/* Weekly Pill Count */}
        <div>
          <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
            Weekly Pill Count
          </label>
          <input
            type="number"
            min="1"
            value={weeklyPillCount}
            onChange={(e) => setWeeklyPillCount(parseInt(e.target.value) || 1)}
            style={{ ...inputStyle, width: '8rem' }}
          />
        </div>

        {/* Save */}
        <div className="pt-1">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white transition-all shadow-sm disabled:opacity-50"
            style={{ background: 'var(--olive)' }}
            onMouseEnter={(e) => !saving && (e.currentTarget.style.background = 'var(--sage-dark)')}
            onMouseLeave={(e) => e.currentTarget.style.background = 'var(--olive)'}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          {message && (
            <p
              className="mt-2 text-sm font-medium"
              style={{ color: message.includes('Failed') ? '#B91C1C' : 'var(--sage-dark)' }}
            >
              {message}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
