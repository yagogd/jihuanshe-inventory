import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

const SORTABLE = {
  name_en: 'Nombre',
  set_code: 'Set',
  collector_number: 'Nº',
  game: 'Juego',
  stock_qty: 'Stock',
  avg_price: 'Precio medio',
}

export default function CardsPage() {
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)
  const [q, setQ] = useState('')
  const [sort, setSort] = useState('name_en')
  const [order, setOrder] = useState('asc')

  useEffect(() => {
    api
      .listCards({ q, sort, order })
      .then(setCards)
      .catch((e) => setError(e.message))
  }, [q, sort, order])

  function toggleSort(key) {
    if (sort === key) {
      setOrder(order === 'asc' ? 'desc' : 'asc')
    } else {
      setSort(key)
      setOrder('asc')
    }
  }

  if (error) return <div className="err">{error}</div>
  if (!cards) return <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Cartas</h1>
      <div className="row" style={{ marginBottom: 16 }}>
        <div className="field">
          <label>Buscar</label>
          <input
            style={{ width: 260 }}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Nombre, set, número…"
          />
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th></th>
            {Object.entries(SORTABLE).map(([key, label]) => (
              <th key={key}>
                <button className="link" onClick={() => toggleSort(key)}>
                  {label}
                  {sort === key ? (order === 'asc' ? ' ↑' : ' ↓') : ''}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cards.map((card) => (
            <tr key={card.id}>
              <td>
                {card.image_path && (
                  <img className="thumb" src={`/images/${card.image_path}`} alt="" />
                )}
              </td>
              <td>
                <a href={`#/cards/${card.id}`}>{card.name_en || card.name_zh || '—'}</a>
                {card.name_en && card.name_zh && (
                  <div className="muted" style={{ fontSize: 12 }}>{card.name_zh}</div>
                )}
              </td>
              <td className="muted">{card.set_code || '—'}</td>
              <td className="muted">{card.collector_number || '—'}</td>
              <td className="muted">{card.game || '—'}</td>
              <td>
                <strong>{card.stock_qty}</strong>
              </td>
              <td className="muted">
                {card.avg_price_eur_cents == null
                  ? '—'
                  : `€${(card.avg_price_eur_cents / 100).toFixed(2)}`}
              </td>
            </tr>
          ))}
          {cards.length === 0 && (
            <tr>
              <td colSpan={7} className="muted">
                No hay cartas que coincidan.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
