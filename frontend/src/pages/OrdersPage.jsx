import React, { useEffect, useState } from 'react'
import { api, fen2yuan } from '../api.js'

export default function OrdersPage() {
  const [orders, setOrders] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .listOrders()
      .then(setOrders)
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="err">{error}</div>
  if (!orders) return <div className="muted">Cargando…</div>

  return (
    <div>
      <h1>Órdenes</h1>
      <table>
        <thead>
          <tr>
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
              <td>{order.purchase_date || '—'}</td>
              <td>{order.seller || '—'}</td>
              <td>{order.items.reduce((n, item) => n + item.quantity, 0)}</td>
              <td>{fen2yuan(order.total_paid_fen)}</td>
              <td>{order.status}</td>
              <td>
                <a href={`#/orders/${order.id}`}>Ver</a>
              </td>
            </tr>
          ))}
          {orders.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                Sin órdenes todavía.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
