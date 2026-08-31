import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'
import Badge from '../components/Badge.jsx'
import Modal from '../components/Modal.jsx'

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

const emptyFilters = () => ({
  q: '',
  game: '',
  set_code: '',
  condition: '',
  variant: '',
  language: '',
  source: '',
  foil: '',
  promo: '',
  available_only: true,
})

export default function InventoryPage() {
  const [lots, setLots] = useState(null)
  const [filters, setFilters] = useState(emptyFilters())
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm())
  const [uploading, setUploading] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [modal, setModal] = useState(null)

  function buildParams() {
    const params = {
      q: filters.q,
      game: filters.game,
      set_code: filters.set_code,
      condition: filters.condition,
      variant: filters.variant,
      language: filters.language,
      source: filters.source,
      available_only: filters.available_only,
    }
    if (filters.foil === 'true') params.foil = true
    else if (filters.foil === 'false') params.foil = false
    if (filters.promo === 'true') params.promo = true
    else if (filters.promo === 'false') params.promo = false
    return params
  }

  function load() {
    api
      .listInventory(buildParams())
      .then(setLots)
      .catch((e) => setError(e.message))
  }

  useEffect(load, [filters])

  function openAction(lot, kind) {
    setModal({ kind, lot, quantity: '1', price: '', fees: '0' })
  }

  async function confirmAction() {
    const { kind, lot } = modal
    const quantity = parseInt(modal.quantity, 10)
    if (!quantity || quantity < 1) return
    setError(null)
    try {
      if (kind === 'split') await api.splitLot(lot.id, quantity)
      else if (kind === 'GRADE') await api.addLotMovement(lot.id, 'GRADE', quantity)
      else if (kind === 'sell')
        await api.sellLot(lot.id, quantity, yuan2fen(modal.price), yuan2fen(modal.fees || '0'))
      setModal(null)
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

  async function translateAll() {
    setTranslating(true)
    setError(null)
    try {
      const result = await api.translateCards()
      setTranslating(false)
      if (result.translated > 0) load()
      else setError(`No quedan nombres por traducir (o no hay conexión).`)
    } catch (e) {
      setError(e.message)
      setTranslating(false)
    }
  }

  if (error && !lots) return <div className="err">{error}</div>
  if (!lots) return <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Inventario</h1>
      {error && <div className="err">{error}</div>}
      <div className="row" style={{ marginBottom: 12 }}>
        <div className="field">
          <label>Buscar</label>
          <input
            style={{ width: 220 }}
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            placeholder="Nombre, set, número…"
          />
        </div>
        <div className="field">
          <label>Juego</label>
          <input
            value={filters.game}
            onChange={(e) => setFilters({ ...filters, game: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Set</label>
          <input
            value={filters.set_code}
            onChange={(e) => setFilters({ ...filters, set_code: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Condición</label>
          <input
            value={filters.condition}
            onChange={(e) => setFilters({ ...filters, condition: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Idioma</label>
          <input
            value={filters.language}
            onChange={(e) => setFilters({ ...filters, language: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Origen</label>
          <select
            value={filters.source}
            onChange={(e) => setFilters({ ...filters, source: e.target.value })}
          >
            <option value="">Todos</option>
            <option value="RECEIVE">Recibido (envío)</option>
            <option value="MANUAL">Manual</option>
            <option value="PENDING">Pendiente</option>
          </select>
        </div>
        <div className="field">
          <label>Foil</label>
          <select
            value={filters.foil}
            onChange={(e) => setFilters({ ...filters, foil: e.target.value })}
          >
            <option value="">Todos</option>
            <option value="true">Sí</option>
            <option value="false">No</option>
          </select>
        </div>
        <div className="field">
          <label>Promo</label>
          <select
            value={filters.promo}
            onChange={(e) => setFilters({ ...filters, promo: e.target.value })}
          >
            <option value="">Todos</option>
            <option value="true">Sí</option>
            <option value="false">No</option>
          </select>
        </div>
        <label className="field" style={{ flexDirection: 'row', gap: 6, alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={!!filters.available_only}
            onChange={(e) => setFilters({ ...filters, available_only: e.target.checked })}
          />
          Solo disponibles
        </label>
        <div style={{ flex: 1 }} />
        <button className="secondary" onClick={translateAll} disabled={translating}>
          {translating ? 'Traduciendo…' : 'Traducir nombres'}
        </button>
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

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Nombre</th>
              <th>Set/Nº</th>
              <th>Cond.</th>
              <th>Variante/Idioma</th>
              <th>Foil/Promo</th>
              <th>Disp.</th>
              <th>Total</th>
              <th>Coste €</th>
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
                  <a href={`#/cards/${lot.card_id}`}>{lot.name}</a>
                  {lot.source === 'PENDING' && (
                    <Badge tone="warn" style={{ marginLeft: 6 }}>Pendiente</Badge>
                  )}
                  {lot.name_en && (
                    <div className="muted" style={{ fontSize: 12 }}>{lot.name_en}</div>
                  )}
                </td>
                <td className="muted">
                  {lot.set_code}·{lot.collector_number}
                </td>
                <td className="muted">{lot.condition || '—'}</td>
                <td className="muted">
                  {[lot.variant, lot.language].filter(Boolean).join(' · ') || '—'}
                </td>
                <td>
                  {lot.foil && <Badge tone="warn">Foil</Badge>}{' '}
                  {lot.promo && <Badge tone="neutral">Promo</Badge>}
                </td>
                <td>
                  <strong>{lot.available}</strong>
                </td>
                <td className="muted">{lot.quantity}</td>
                <td className="muted">
                  {lot.unit_cost_eur_cents == null
                    ? '—'
                    : fen2yuan(lot.unit_cost_eur_cents)}
                </td>
                <td>
                  {lot.source !== 'PENDING' ? (
                    <>
                      <button className="secondary" onClick={() => openAction(lot, 'sell')}>
                        Vender
                      </button>{' '}
                      <button className="secondary" onClick={() => openAction(lot, 'GRADE')}>
                        Grading
                      </button>{' '}
                      <button className="secondary" onClick={() => openAction(lot, 'split')}>
                        Dividir
                      </button>
                    </>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
              </tr>
            ))}
            {lots.length === 0 && (
              <tr>
                <td colSpan={10} className="muted">
                  Sin cartas que coincidan con los filtros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal
          title={
            modal.kind === 'sell'
              ? `Vender · ${modal.lot.name}`
              : modal.kind === 'GRADE'
                ? `Grading · ${modal.lot.name}`
                : `Dividir · ${modal.lot.name}`
          }
          onClose={() => setModal(null)}
          actions={
            <>
              <button className="secondary" onClick={() => setModal(null)}>
                Cancelar
              </button>
              <button onClick={confirmAction}>Confirmar</button>
            </>
          }
        >
          <div className="field" style={{ marginBottom: 12 }}>
            <label>Cantidad (disponible: {modal.lot.available})</label>
            <input
              type="number"
              min="1"
              value={modal.quantity}
              onChange={(e) => setModal({ ...modal, quantity: e.target.value })}
            />
          </div>
          {modal.kind === 'sell' && (
            <>
              <div className="field" style={{ marginBottom: 12 }}>
                <label>Precio de venta por unidad (€)</label>
                <input
                  value={modal.price}
                  onChange={(e) => setModal({ ...modal, price: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Comisiones/fees totales (€)</label>
                <input
                  value={modal.fees}
                  onChange={(e) => setModal({ ...modal, fees: e.target.value })}
                />
              </div>
            </>
          )}
        </Modal>
      )}
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
