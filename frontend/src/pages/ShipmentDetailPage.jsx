import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'

const STATUSES = ['PREPARING', 'SHIPPED', 'RECEIVED']
const COST_TYPES = ['INTERNATIONAL', 'INSURANCE', 'CUSTOMS', 'OTHER']
const METHODS = ['BY_VALUE', 'BY_QUANTITY', 'MANUAL']

function toCosts(costs) {
  const map = Object.fromEntries(
    COST_TYPES.map((type) => [type, { amount: '0', method: 'BY_VALUE' }])
  )
  for (const cost of costs) {
    map[cost.type] = { amount: fen2yuan(cost.amount_eur_cents), method: cost.method }
  }
  return map
}

export default function ShipmentDetailPage({ id }) {
  const [shipment, setShipment] = useState(null)
  const [orders, setOrders] = useState([])
  const [costs, setCosts] = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api
      .getShipment(id)
      .then((data) => {
        setShipment(data)
        setCosts(toCosts(data.costs))
        setSelected(new Set(data.orders.map((o) => o.id)))
      })
      .catch((e) => setError(e.message))
    api
      .listOrders()
      .then(setOrders)
      .catch((e) => setError(e.message))
  }, [id])

  async function save() {
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      const payload = {
        status: shipment.status,
        order_ids: [...selected],
        costs: COST_TYPES.map((type) => ({
          type,
          amount_eur_cents: yuan2fen(costs[type].amount),
          method: costs[type].method,
        })),
      }
      const updated = await api.updateShipment(id, payload)
      setShipment(updated)
      setCosts(toCosts(updated.costs))
      setSelected(new Set(updated.orders.map((o) => o.id)))
      setSaved(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  function toggleOrder(orderId) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(orderId)) next.delete(orderId)
      else next.add(orderId)
      return next
    })
  }

  async function receive() {
    setError(null)
    setSaved(false)
    try {
      const updated = await api.receiveShipment(id)
      setShipment(updated)
    } catch (e) {
      setError(e.message)
    }
  }

  if (!shipment || !costs) return error ? <div className="err">{error}</div> : <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Envío {shipment.id.slice(0, 8)}</h1>
      <div className="card">
        {error && <div className="err">{error}</div>}
        {saved && <div className="ok">Cambios guardados ✓</div>}
        {shipment.has_sales && (
          <div className="warn" style={{ marginTop: 8 }}>
            Este envío tiene ventas registradas. Recalcular sus costes no altera el beneficio
            ya calculado de ventas pasadas.
          </div>
        )}
        <div className="row" style={{ marginTop: 12 }}>
          <div className="field">
            <label>Estado</label>
            <select
              value={shipment.status}
              onChange={(e) => setShipment({ ...shipment, status: e.target.value })}
            >
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>
          {shipment.status !== 'RECEIVED' && (
            <button onClick={receive}>Recibir envío (genera inventario)</button>
          )}
        </div>
      </div>

      <div className="card">
        <h3>Costes del envío (EUR)</h3>
        <table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Importe €</th>
              <th>Reparto</th>
            </tr>
          </thead>
          <tbody>
            {COST_TYPES.map((type) => (
              <tr key={type}>
                <td>{type}</td>
                <td>
                  <input
                    style={{ width: 90 }}
                    value={costs[type].amount}
                    onChange={(e) =>
                      setCosts({ ...costs, [type]: { ...costs[type], amount: e.target.value } })
                    }
                  />
                </td>
                <td>
                  <select
                    value={costs[type].method}
                    onChange={(e) =>
                      setCosts({ ...costs, [type]: { ...costs[type], method: e.target.value } })
                    }
                  >
                    {METHODS.map((method) => (
                      <option key={method} value={method}>
                        {method}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Órdenes incluidas</h3>
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Fecha</th>
              <th>Vendedor</th>
              <th>Total ¥</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(order.id)}
                    onChange={() => toggleOrder(order.id)}
                  />
                </td>
                <td>{order.purchase_date || '—'}</td>
                <td>{order.seller || '—'}</td>
                <td>{fen2yuan(order.total_paid_fen)}</td>
                <td>{order.status}</td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No hay órdenes.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="row" style={{ marginTop: 16 }}>
        <button onClick={save} disabled={saving}>
          {saving ? 'Guardando…' : 'Guardar envío'}
        </button>
      </div>
    </div>
  )
}
