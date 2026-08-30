import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function InventoryPage() {
  const [lots, setLots] = useState(null)
  const [filters, setFilters] = useState({ q: '', available_only: true })
  const [error, setError] = useState(null)

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

  if (error) return <div className="err">{error}</div>
  if (!lots) return <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Inventario</h1>
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
      </div>

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
              <td>{lot.name}</td>
              <td className="muted">
                {lot.set_code}·{lot.collector_number}
              </td>
              <td className="muted">{lot.condition || '—'}</td>
              <td>
                <strong>{lot.available}</strong>
              </td>
              <td className="muted">{lot.quantity}</td>
              <td>
                <button className="secondary" onClick={() => act(lot, 'SELL', 'Vender')}>
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
                Sin inventario. Recibe un envío en la sección Envíos.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
