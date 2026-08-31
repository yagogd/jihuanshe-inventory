import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'

const CURRENCIES = ['EUR', 'CNY', 'USD']

const emptyForm = () => ({
  game: '',
  set_code: '',
  collector_number: '',
  name_zh: '',
  name_en: '',
  condition: '',
  quantity: '1',
  amount: '0',
  currency: 'EUR',
  note: '',
  image_path: null,
})

export default function InventoryPage() {
  const [lots, setLots] = useState(null)
  const [filters, setFilters] = useState({ q: '', available_only: true })
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm())
  const [uploading, setUploading] = useState(false)

  function load() {
    api
      .listInventory(filters)
      .then(setLots)
      .catch((e) => setError(e.message))
  }

  useEffect(load, [filters])

  async function act(lot, kind, label) {
    const raw = window.prompt(`${label} cantidad (disponible: ${lot.available})`)
    if (raw == null) return
    const quantity = parseInt(raw, 10)
    if (!quantity) return
    setError(null)
    try {
      if (kind === 'split') await api.splitLot(lot.id, quantity)
      else await api.addLotMovement(lot.id, kind, quantity)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function sell(lot) {
    const qty = window.prompt(`Vender cantidad (disponible: ${lot.available})`, '1')
    if (qty == null) return
    const price = window.prompt('Precio de venta por unidad (€)', '')
    if (price == null) return
    const fees = window.prompt('Comisiones/fees totales (€)', '0')
    setError(null)
    try {
      await api.sellLot(lot.id, parseInt(qty, 10) || 1, yuan2fen(price), yuan2fen(fees || '0'))
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function onImage(file) {
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        const data = String(reader.result).split(',')[1]
        const uploaded = await api.uploadImage({ filename: file.name, data })
        setForm((f) => ({ ...f, image_path: uploaded.image_path }))
        setUploading(false)
      }
      reader.readAsDataURL(file)
    } catch (e) {
      setError(e.message)
      setUploading(false)
    }
  }

  async function submit() {
    setError(null)
    try {
      await api.addInventoryLot({
        game: form.game || null,
        set_code: form.set_code || null,
        collector_number: form.collector_number || null,
        name_zh: form.name_zh || null,
        name_en: form.name_en || null,
        condition: form.condition || null,
        quantity: parseInt(form.quantity, 10) || 1,
        amount: yuan2fen(form.amount),
        currency: form.currency,
        note: form.note || null,
        image_path: form.image_path,
      })
      setForm(emptyForm())
      setShowForm(false)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  if (error && !lots) return <div className="err">{error}</div>
  if (!lots) return <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Inventario</h1>
      {error && <div className="err">{error}</div>}
      <div className="row" style={{ marginBottom: 16 }}>
        <div className="field">
          <label>Buscar</label>
          <input
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Set</label>
          <input
            value={filters.set_code || ''}
            onChange={(e) => setFilters({ ...filters, set_code: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Juego</label>
          <input
            value={filters.game || ''}
            onChange={(e) => setFilters({ ...filters, game: e.target.value })}
          />
        </div>
        <label className="field" style={{ flexDirection: 'row', gap: 6, alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={!!filters.available_only}
            onChange={(e) => setFilters({ ...filters, available_only: e.target.checked })}
          />
          Solo disponibles
        </label>
        <button className="secondary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancelar' : 'Añadir carta'}
        </button>
      </div>

      {showForm && (
        <div className="card">
          <h3>Añadir carta al inventario</h3>
          <div className="row">
            <Field label="Juego" value={form.game} set={(v) => setForm({ ...form, game: v })} />
            <Field label="Set" value={form.set_code} set={(v) => setForm({ ...form, set_code: v })} />
            <Field label="Nº" value={form.collector_number} set={(v) => setForm({ ...form, collector_number: v })} />
            <Field label="Nombre (chino)" value={form.name_zh} set={(v) => setForm({ ...form, name_zh: v })} />
            <Field label="Nombre (inglés)" value={form.name_en} set={(v) => setForm({ ...form, name_en: v })} />
            <Field label="Condición" value={form.condition} set={(v) => setForm({ ...form, condition: v })} />
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <Field label="Cantidad" value={form.quantity} set={(v) => setForm({ ...form, quantity: v })} />
            <Field label="Precio total" value={form.amount} set={(v) => setForm({ ...form, amount: v })} />
            <div className="field">
              <label>Moneda</label>
              <select
                value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
              >
                {CURRENCIES.map((currency) => (
                  <option key={currency} value={currency}>
                    {currency}
                  </option>
                ))}
              </select>
            </div>
            <Field label="Nota de origen" value={form.note} set={(v) => setForm({ ...form, note: v })} />
            <div className="field">
              <label>Imagen (opcional)</label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => onImage(e.target.files[0])}
              />
              {uploading && <span className="muted">Subiendo…</span>}
            </div>
          </div>
          <div className="row" style={{ marginTop: 16 }}>
            <button onClick={submit} disabled={uploading}>
              Guardar carta
            </button>
          </div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th></th>
            <th>Nombre</th>
            <th>Set/Nº</th>
            <th>Cond.</th>
            <th>Disp.</th>
            <th>Total</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {lots.map((lot) => (
            <tr key={lot.id}>
              <td>
                {lot.image_path && (
                  <img className="thumb" src={`/images/${lot.image_path}`} alt="" />
                )}
              </td>
              <td>
                {lot.name}
                {lot.name_en && lot.name !== lot.name_en && (
                  <div className="muted" style={{ fontSize: 12 }}>{lot.name_en}</div>
                )}
              </td>
              <td className="muted">
                {lot.set_code}·{lot.collector_number}
              </td>
              <td className="muted">{lot.condition || '—'}</td>
              <td>
                <strong>{lot.available}</strong>
              </td>
              <td className="muted">{lot.quantity}</td>
              <td>
                <button className="secondary" onClick={() => sell(lot)}>
                  Vender
                </button>{' '}
                <button className="secondary" onClick={() => act(lot, 'GRADE', 'Grading')}>
                  Grading
                </button>{' '}
                <button className="secondary" onClick={() => act(lot, 'split', 'Dividir')}>
                  Dividir
                </button>
              </td>
            </tr>
          ))}
          {lots.length === 0 && (
            <tr>
              <td colSpan={7} className="muted">
                Sin inventario. Recibe un envío o añade cartas manualmente.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function Field({ label, value, set }) {
  return (
    <div className="field">
      <label>{label}</label>
      <input value={value} onChange={(e) => set(e.target.value)} />
    </div>
  )
}
