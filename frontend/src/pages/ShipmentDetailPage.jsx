import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'

const STATUSES = ['PREPARING', 'SHIPPED', 'RECEIVED']
const METHODS = ['BY_VALUE', 'BY_QUANTITY']
const CURRENCIES = ['EUR', 'CNY', 'USD']

function newLine() {
  return { category_id: '', amount: '0', currency: 'EUR', method: 'BY_VALUE', insured_amount: '', insured_currency: 'EUR' }
}

function toLines(costs) {
  if (!costs.length) return [newLine()]
  return costs.map((cost) => ({
    category_id: cost.category_id,
    amount: fen2yuan(cost.amount),
    currency: cost.currency,
    method: cost.method,
    insured_amount: cost.insured_amount == null ? '' : fen2yuan(cost.insured_amount),
    insured_currency: cost.insured_currency || 'EUR',
  }))
}

function lineEurCents(line, fx) {
  const amount = yuan2fen(line.amount)
  if (line.currency === 'EUR') return amount
  return Math.round(amount * fx)
}

export default function ShipmentDetailPage({ id }) {
  const [shipment, setShipment] = useState(null)
  const [orders, setOrders] = useState([])
  const [categories, setCategories] = useState([])
  const [total, setTotal] = useState('0')
  const [fx, setFx] = useState('0.13')
  const [lines, setLines] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [newCategory, setNewCategory] = useState('')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getShipment(id).then((data) => {
      setShipment(data)
      setTotal(fen2yuan(data.total_paid_eur_cents))
      setFx(String(data.fx_cny_eur))
      setLines(toLines(data.costs))
      setSelected(new Set(data.orders.map((o) => o.id)))
    }).catch((e) => setError(e.message))
    api.listOrders().then(setOrders).catch((e) => setError(e.message))
    api.listCostCategories().then(setCategories).catch((e) => setError(e.message))
  }, [id])

  const sum = lines.reduce((acc, line) => acc + lineEurCents(line, parseFloat(fx) || 0), 0)
  const totalCents = yuan2fen(total)
  const matches = sum === totalCents

  function updateLine(index, patch) {
    setLines((current) => current.map((line, i) => (i === index ? { ...line, ...patch } : line)))
  }

  function addLine() {
    setLines((current) => [...current, newLine()])
  }

  function removeLine(index) {
    setLines((current) => current.filter((_, i) => i !== index))
  }

  function fitFx() {
    const eurLines = lines.filter((l) => l.currency === 'EUR').reduce((a, l) => a + yuan2fen(l.amount), 0)
    const cnyFen = lines.filter((l) => l.currency === 'CNY').reduce((a, l) => a + yuan2fen(l.amount), 0)
    if (cnyFen <= 0) return
    setFx(String(((totalCents - eurLines) / cnyFen).toFixed(6)))
  }

  async function createCategory() {
    const name = newCategory.trim()
    if (!name) return
    setError(null)
    try {
      const created = await api.createCostCategory({ name, kind: 'custom' })
      setCategories((current) => [...current, created])
      setNewCategory('')
    } catch (e) {
      setError(e.message)
    }
  }

  async function save() {
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      const payload = {
        status: shipment.status,
        order_ids: [...selected],
        total_paid_eur_cents: totalCents,
        fx_cny_eur: parseFloat(fx) || 0,
        costs: lines
          .filter((line) => line.category_id)
          .map((line) => ({
            category_id: line.category_id,
            amount: yuan2fen(line.amount),
            currency: line.currency,
            method: line.method,
            insured_amount: line.insured_amount === '' ? null : yuan2fen(line.insured_amount),
            insured_currency: line.insured_amount === '' ? null : line.insured_currency,
          })),
      }
      const updated = await api.updateShipment(id, payload)
      setShipment(updated)
      setTotal(fen2yuan(updated.total_paid_eur_cents))
      setFx(String(updated.fx_cny_eur))
      setLines(toLines(updated.costs))
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

  if (!shipment || !lines.length) return error ? <div className="err">{error}</div> : <div className="muted">Cargando…</div>

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
        <h3>Coste total del envío</h3>
        <div className="row" style={{ alignItems: 'flex-end' }}>
          <div className="field">
            <label>Total pagado (€)</label>
            <input
              style={{ width: 140, fontSize: 18 }}
              value={total}
              onChange={(e) => setTotal(e.target.value)}
            />
          </div>
          <div className="field">
            <label>FX CNY→EUR del envío</label>
            <div className="row">
              <input
                style={{ width: 110 }}
                value={fx}
                onChange={(e) => setFx(e.target.value)}
              />
              <button className="secondary" onClick={fitFx}>
                Cuadrar FX al total
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Desglose</h3>
        <table>
          <thead>
            <tr>
              <th>Categoría</th>
              <th>Importe</th>
              <th>Moneda</th>
              <th>Reparto</th>
              <th>Seguro (cobertura)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => {
              const category = categories.find((c) => c.id === line.category_id)
              return (
                <tr key={index}>
                  <td>
                    <select
                      value={line.category_id}
                      onChange={(e) => updateLine(index, { category_id: e.target.value })}
                    >
                      <option value="">—</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      style={{ width: 90 }}
                      value={line.amount}
                      onChange={(e) => updateLine(index, { amount: e.target.value })}
                    />
                  </td>
                  <td>
                    <select
                      value={line.currency}
                      onChange={(e) => updateLine(index, { currency: e.target.value })}
                    >
                      {CURRENCIES.map((currency) => (
                        <option key={currency} value={currency}>
                          {currency}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      value={line.method}
                      onChange={(e) => updateLine(index, { method: e.target.value })}
                    >
                      {METHODS.map((method) => (
                        <option key={method} value={method}>
                          {method}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    {category && category.kind === 'insurance' ? (
                      <div className="row">
                        <input
                          style={{ width: 90 }}
                          placeholder="Importe"
                          value={line.insured_amount}
                          onChange={(e) => updateLine(index, { insured_amount: e.target.value })}
                        />
                        <select
                          value={line.insured_currency}
                          onChange={(e) => updateLine(index, { insured_currency: e.target.value })}
                        >
                          {CURRENCIES.map((currency) => (
                            <option key={currency} value={currency}>
                              {currency}
                            </option>
                          ))}
                        </select>
                      </div>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>
                    <button className="secondary" onClick={() => removeLine(index)} title="Quitar línea">
                      ×
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="secondary" onClick={addLine}>
            Añadir línea
          </button>
          <div className="field">
            <label>Nueva categoría</label>
            <div className="row">
              <input
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                placeholder="p. ej. Protección esquinas"
              />
              <button className="secondary" onClick={createCategory}>
                Crear
              </button>
            </div>
          </div>
        </div>
        <div className="totals">
          <div>
            Suma del desglose: <strong>{fen2yuan(sum)} €</strong>
          </div>
          <div>
            Total del envío: <strong>{fen2yuan(totalCents)} €</strong>
          </div>
          {!matches && (
            <div className="err">
              No coincide. El desglose debe sumar exactamente el total.
            </div>
          )}
        </div>
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
        <button onClick={save} disabled={saving || !matches}>
          {saving ? 'Guardando…' : 'Guardar envío'}
        </button>
      </div>
    </div>
  )
}
