import React, { useEffect, useState } from 'react'
import { api, fen2yuan } from '../api.js'

export default function ShipmentsPage() {
  const [shipments, setShipments] = useState(null)
  const [error, setError] = useState(null)
  const [creating, setCreating] = useState(false)

  function load() {
    api
      .listShipments()
      .then(setShipments)
      .catch((e) => setError(e.message))
  }

  useEffect(load, [])

  async function create() {
    setCreating(true)
    setError(null)
    try {
      const shipment = await api.createShipment({ order_ids: [], costs: [], total_paid_eur_cents: 0 })
      window.location.hash = '#/shipments/' + shipment.id
    } catch (e) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  if (error) return <div className="err">{error}</div>
  if (!shipments) return <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Envíos CN→ES</h1>
      <div className="row" style={{ marginBottom: 16 }}>
        <button onClick={create} disabled={creating}>
          {creating ? 'Creando…' : 'Nuevo envío'}
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Estado</th>
            <th>Órdenes</th>
            <th>Costes €</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {shipments.map((shipment) => (
            <tr key={shipment.id}>
              <td>{shipment.status}</td>
              <td>{shipment.orders.length}</td>
              <td>{fen2yuan(shipment.total_paid_eur_cents)}</td>
              <td>
                <a href={`#/shipments/${shipment.id}`}>Ver</a>
              </td>
            </tr>
          ))}
          {shipments.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
                Sin envíos todavía.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
