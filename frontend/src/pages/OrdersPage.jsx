import React, { useEffect, useState } from 'react'
import { api, fen2yuan } from '../api.js'

const STATUSES = ['PURCHASED', 'IN_TRANSIT_TO_WAREHOUSE', 'AT_WAREHOUSE']

export default function OrdersPage() {
  const [orders, setOrders] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState(null)

  useEffect(() => {
    api
      .listOrders(filter)
      .then(setOrders)
      .catch((e) => setError(e.message))
  }, [filter])

  async function changeStatus(order, status) {
    try {
      const updated = await api.setOrderStatus(order.id, status)
      setOrders((current) =>
        current.map((o) => (o.id === updated.id ? updated : o))
      )
    } catch (e) {
      setError(e.message)
    }
  }

  if (error) return <div className="err">{error}</div>
  if (!orders) return <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Órdenes</h1>
      <div className="row" style={{ marginBottom: 16 }}>
        <button className={filter === null ? undefined : 'secondary'} onClick={() => setFilter(null)}>
          Todas
        </button>
        {STATUSES.map((status) => (
          <button
            key={status}
            className={filter === status ? undefined : 'secondary'}
            onClick={() => setFilter(status)}
          >
            {status}
          </button>
        ))}
      </div>
      <table>
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Fecha</th>
            <th>Vendedor</th>
            <th>Artículos</th>
            <th>Total ¥</th>
            <th>Estado</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id}>
              <td>{order.display_name || (order.seller || '—')}</td>
              <td>{order.purchase_date || '—'}</td>
              <td>{order.seller || '—'}</td>
              <td>{order.items.reduce((n, item) => n + item.quantity, 0)}</td>
              <td>{fen2yuan(order.total_paid_fen)}</td>
              <td>
                <select value={order.status} onChange={(e) => changeStatus(order, e.target.value)}>
                  {STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <a href={`#/orders/${order.id}`}>Ver</a>
              </td>
            </tr>
          ))}
          {orders.length === 0 && (
            <tr>
              <td colSpan={7} className="muted">
                Sin órdenes en este estado.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
