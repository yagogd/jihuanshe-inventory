import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'

export default function SettingsPage() {
  const [form, setForm] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api
      .getSettings()
      .then((data) =>
        setForm({
          threshold: fen2yuan(data.alipay_fee_threshold_fen),
          rate: String(data.alipay_fee_rate * 100),
          fx: String(data.fx_cny_eur),
          fx_mode: data.fx_mode || 'historical',
          display_currency: data.display_currency || 'EUR',
        })
      )
      .catch((e) => setError(e.message))
  }, [])

  async function save() {
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      const body = {
        alipay_fee_threshold_fen: yuan2fen(form.threshold),
        alipay_fee_rate: (parseFloat(form.rate) || 0) / 100,
        fx_cny_eur: parseFloat(form.fx) || 0,
        fx_mode: form.fx_mode,
        display_currency: form.display_currency,
      }
      const data = await api.updateSettings(body)
      setForm({
        threshold: fen2yuan(data.alipay_fee_threshold_fen),
        rate: String(data.alipay_fee_rate * 100),
        fx: String(data.fx_cny_eur),
        fx_mode: data.fx_mode,
        display_currency: data.display_currency,
      })
      setSaved(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (!form) return error ? <div className="err">{error}</div> : <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Ajustes</h1>
      <div className="card">
        {error && <div className="err">{error}</div>}
        {saved && <div className="ok">Ajustes guardados ✓</div>}
        <div className="row" style={{ marginTop: 12 }}>
          <div className="field">
            <label>Umbral fee Alipay (¥)</label>
            <input
              value={form.threshold}
              onChange={(e) => setForm({ ...form, threshold: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Tasa Alipay (%)</label>
            <input
              value={form.rate}
              onChange={(e) => setForm({ ...form, rate: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Conversión CNY→EUR</label>
            <select
              value={form.fx_mode}
              onChange={(e) => setForm({ ...form, fx_mode: e.target.value })}
            >
              <option value="historical">Tipo del día (automático)</option>
              <option value="fixed">Tasa fija</option>
            </select>
          </div>
          {form.fx_mode === 'fixed' && (
            <div className="field">
              <label>FX CNY→EUR fijo</label>
              <input
                value={form.fx}
                onChange={(e) => setForm({ ...form, fx: e.target.value })}
              />
            </div>
          )}
          <div className="field">
            <label>Moneda de visualización</label>
            <select
              value={form.display_currency}
              onChange={(e) => setForm({ ...form, display_currency: e.target.value })}
            >
              <option value="EUR">Euro (€)</option>
              <option value="CNY">Yuan (¥)</option>
            </select>
          </div>
        </div>
        <div className="muted" style={{ marginTop: 12 }}>
          La moneda de visualización se usa arriba de cada precio; debajo siempre se muestra el equivalente en euros.
        </div>
        <div className="muted" style={{ marginTop: 4 }}>
          {form.fx_mode === 'historical'
            ? 'Conversión: se usa el tipo de cambio oficial del día de compra (ECB). Sin conexión se usa la tasa fija.'
            : 'Conversión: se usa la tasa fija para todas las órdenes nuevas.'}
        </div>
        <div className="row" style={{ marginTop: 16 }}>
          <button onClick={save} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar ajustes'}
          </button>
        </div>
      </div>
    </div>
  )
}
