import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function CardDetailPage({ id }) {
  const [card, setCard] = useState(null)
  const [error, setError] = useState(null)
  const [nameEn, setNameEn] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api
      .getCard(id)
      .then((data) => {
        setCard(data)
        setNameEn(data.name_en || '')
      })
      .catch((e) => setError(e.message))
  }, [id])

  async function saveName() {
    setError(null)
    setSaved(false)
    try {
      const updated = await api.updateCard(id, { name_en: nameEn })
      setCard(updated)
      setSaved(true)
    } catch (e) {
      setError(e.message)
    }
  }

  if (error) return <div className="err">{error}</div>
  if (!card) return <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>{card.name_en || card.name_zh || 'Carta'}</h1>
      <div className="card">
        {saved && <div className="ok">Cambios guardados ✓</div>}
        <div className="row">
          {card.image_path && (
            <img
              className="thumb"
              style={{ width: 120, height: 160 }}
              src={`/images/${card.image_path}`}
              alt=""
            />
          )}
          <div className="field" style={{ flex: 1 }}>
            <label>Nombre chino</label>
            <div>{card.name_zh || '—'}</div>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Nombre en inglés</label>
            <div className="row">
              <input
                value={nameEn}
                onChange={(e) => setNameEn(e.target.value)}
                style={{ width: 260 }}
              />
              <button className="secondary" onClick={saveName}>
                Guardar
              </button>
            </div>
          </div>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <span className="muted">Set: {card.set_code || '—'}</span>
          <span className="muted">Nº: {card.collector_number || '—'}</span>
          <span className="muted">Juego: {card.game || '—'}</span>
          {card.variant && <span className="muted">Variante: {card.variant}</span>}
          {card.language && <span className="muted">Idioma: {card.language}</span>}
          {card.foil && <span className="muted">Foil</span>}
          {card.promo && <span className="muted">Promo</span>}
        </div>
      </div>

      <div className="card">
        <h3>Compras</h3>
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Vendedor</th>
              <th>Qty</th>
              <th>Precio ¥</th>
              <th>Cond.</th>
            </tr>
          </thead>
          <tbody>
            {card.purchases.map((purchase) => (
              <tr key={purchase.id}>
                <td>{purchase.purchase_date || '—'}</td>
                <td>{purchase.seller || '—'}</td>
                <td>{purchase.quantity}</td>
                <td>{(purchase.unit_price_fen / 100).toFixed(2)}</td>
                <td className="muted">{purchase.condition || '—'}</td>
              </tr>
            ))}
            {card.purchases.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  Sin compras registradas.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Inventario</h3>
        <table>
          <thead>
            <tr>
              <th>Disponible</th>
              <th>Total</th>
              <th>Cond.</th>
            </tr>
          </thead>
          <tbody>
            {card.lots.map((lot) => (
              <tr key={lot.id}>
                <td>
                  <strong>{lot.available}</strong>
                </td>
                <td className="muted">{lot.quantity}</td>
                <td className="muted">{lot.condition || '—'}</td>
              </tr>
            ))}
            {card.lots.length === 0 && (
              <tr>
                <td colSpan={3} className="muted">
                  Sin stock.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
