import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'

const STATUSES = ['PURCHASED', 'IN_TRANSIT_TO_WAREHOUSE', 'AT_WAREHOUSE']
const METHODS = ['BY_VALUE', 'BY_QUANTITY', 'MANUAL']

function newItem() {
  return {
    raw_name: '',
    normalized_name: '',
    game: '',
    set_code: '',
    collector_number: '',
    language: '',
    condition: '',
    variant: '',
    promo: false,
    foil: false,
    quantity: 1,
    unit_price: '0',
    origin: 'MANUAL',
    include_in_allocation: true,
    image_path: null,
  }
}

function toForm(order) {
  return {
    jihuanshe_order_id: order.jihuanshe_order_id || '', seller: order.seller || '',
    purchase_date: order.purchase_date || '', express_company: order.express_company || '',
    express_tracking: order.express_tracking || '', domestic_shipping: fen2yuan(order.domestic_shipping_fen),
    alipay_fee: order.alipay_fee_fen == null ? '' : fen2yuan(order.alipay_fee_fen),
    total_paid: fen2yuan(order.total_paid_fen),
    card_charged: order.card_charged_eur_cents == null ? '' : fen2yuan(order.card_charged_eur_cents),
    cost_method: order.cost_method || 'BY_VALUE',
    items: order.items.map((item) => ({ ...item, unit_price: fen2yuan(item.unit_price_fen) })),
  }
}

export default function OrderDetailPage({ id }) {
  const [order, setOrder] = useState(null)
  const [form, setForm] = useState(null)
  const [landed, setLanded] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getOrder(id).then((data) => { setOrder(data); setForm(toForm(data)) }).catch((e) => setError(e.message))
    api.getOrderLanded(id).then(setLanded).catch(() => {})
  }, [id])

  function updateItem(index, patch) {
    setForm((current) => ({ ...current, items: current.items.map((item, i) => i === index ? { ...item, ...patch } : item) }))
  }

  function addItem() {
    setForm((current) => ({ ...current, items: [...current.items, newItem()] }))
  }

  function removeItem(index) {
    setForm((current) => ({ ...current, items: current.items.filter((_, i) => i !== index) }))
  }

  async function save() {
    setSaving(true); setSaved(false); setError(null)
    try {
      const payload = {
        jihuanshe_order_id: form.jihuanshe_order_id || null, seller: form.seller || null,
        purchase_date: form.purchase_date || null, express_company: form.express_company || null,
        express_tracking: form.express_tracking || null,
        domestic_shipping_fen: yuan2fen(form.domestic_shipping),
        alipay_fee_fen: form.alipay_fee === '' ? null : yuan2fen(form.alipay_fee),
        total_paid_fen: form.total_paid === '' ? null : yuan2fen(form.total_paid),
        card_charged_eur_cents: form.card_charged === '' ? null : yuan2fen(form.card_charged),
        cost_method: form.cost_method,
        items: form.items.map((item, index) => ({
          raw_name: item.raw_name || item.normalized_name, normalized_name: item.normalized_name || item.raw_name,
          game: item.game, set_code: item.set_code || null, collector_number: item.collector_number || null,
          language: item.language, condition: item.condition, variant: item.variant || null,
          promo: !!item.promo, foil: !!item.foil, quantity: parseInt(item.quantity, 10) || 1,
          unit_price_fen: yuan2fen(item.unit_price), origin: item.origin,
          include_in_allocation: item.include_in_allocation, image_path: item.image_path, position: index,
        })),
      }
      const updated = await api.updateOrder(id, payload)
      setOrder(updated); setForm(toForm(updated)); setSaved(true)
      api.getOrderLanded(id).then(setLanded).catch(() => {})
    } catch (e) { setError(e.message) } finally { setSaving(false) }
  }

  async function changeStatus(status) {
    setError(null)
    try {
      const updated = await api.setOrderStatus(id, status)
      setOrder(updated); setForm(toForm(updated))
    } catch (e) { setError(e.message) }
  }

  if (!order || !form) return error ? <div className="err">{error}</div> : <div className="muted">Cargando…</div>

  return <div>
    <h1>Editar orden</h1>
    <div className="card">
      {error && <div className="err">{error}</div>}{saved && <div className="ok">Cambios guardados ✓</div>}
      {order.has_sales && (
        <div className="warn" style={{ marginTop: 8 }}>
          Esta orden tiene ventas registradas. Los cambios aquí no alteran el beneficio ya
          calculado de ventas pasadas.
        </div>
      )}
      <div className="row" style={{ marginTop: 12 }}>
        <Field label="Nº de pedido" value={form.jihuanshe_order_id} set={(value) => setForm({ ...form, jihuanshe_order_id: value })} />
        <Field label="Vendedor" value={form.seller} set={(value) => setForm({ ...form, seller: value })} />
        <Field label="Fecha" value={form.purchase_date} set={(value) => setForm({ ...form, purchase_date: value })} />
        <Field label="Transportista" value={form.express_company} set={(value) => setForm({ ...form, express_company: value })} />
        <Field label="Seguimiento" value={form.express_tracking} set={(value) => setForm({ ...form, express_tracking: value })} />
        <Field label="Envío doméstico ¥" value={form.domestic_shipping} set={(value) => setForm({ ...form, domestic_shipping: value })} />
        <Field label="Fee Alipay ¥" value={form.alipay_fee} set={(value) => setForm({ ...form, alipay_fee: value })} />
        <Field label="Total pagado ¥" value={form.total_paid} set={(value) => setForm({ ...form, total_paid: value })} />
        <Field label="Cargo en tarjeta €" value={form.card_charged} set={(value) => setForm({ ...form, card_charged: value })} />
        <div className="field">
          <label>FX CNY→EUR</label>
          <span>
            {order.fx_cny_eur}
            <span className={order.card_charged_eur_cents != null ? 'ok' : 'warn'} style={{ marginLeft: 6 }}>
              {order.card_charged_eur_cents != null ? 'confirmado' : 'estimado'}
            </span>
          </span>
        </div>
      </div>
      <div className="row" style={{ marginTop: 12 }}>
        <div className="field">
          <label>Estado</label>
          <select value={order.status} onChange={(e) => changeStatus(e.target.value)}>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Reparto de costes</label>
          <select
            value={form.cost_method}
            onChange={(e) => setForm({ ...form, cost_method: e.target.value })}
          >
            {METHODS.map((method) => (
              <option key={method} value={method}>
                {method}
              </option>
            ))}
          </select>
        </div>
        <span className="muted">ID: {order.id}</span>
      </div>
    </div>
    <table><thead><tr><th></th><th>Nombre</th><th>Qty</th><th>Precio ¥</th><th>Set</th><th>Nº</th><th>Variante</th><th>Promo</th><th></th></tr></thead>
      <tbody>{form.items.map((item, index) => <tr key={item.id || index}>
        <td>{item.image_path && <img className="thumb" src={`/images/${item.image_path}`} alt="" />}</td>
        <td><input value={item.normalized_name} title={item.raw_name} onChange={(e) => updateItem(index, { normalized_name: e.target.value })} /></td>
        <td><input type="number" min="1" style={{ width: 60 }} value={item.quantity} onChange={(e) => updateItem(index, { quantity: e.target.value })} /></td>
        <td><input style={{ width: 75 }} value={item.unit_price} onChange={(e) => updateItem(index, { unit_price: e.target.value })} /></td>
        <td><input style={{ width: 75 }} value={item.set_code || ''} onChange={(e) => updateItem(index, { set_code: e.target.value })} /></td>
        <td><input style={{ width: 95 }} value={item.collector_number || ''} onChange={(e) => updateItem(index, { collector_number: e.target.value })} /></td>
        <td><input style={{ width: 90 }} value={item.variant || ''} onChange={(e) => updateItem(index, { variant: e.target.value })} /></td>
        <td><input type="checkbox" checked={!!item.promo} onChange={(e) => updateItem(index, { promo: e.target.checked })} /></td>
        <td><button className="secondary" onClick={() => removeItem(index)} title="Quitar ítem">×</button></td>
      </tr>)}</tbody>
    </table>
    <div className="row" style={{ marginTop: 12 }}>
      <button className="secondary" onClick={addItem}>Añadir ítem</button>
    </div>
    <div className="row" style={{ marginTop: 16 }}><button onClick={save} disabled={saving}>{saving ? 'Guardando…' : 'Guardar cambios'}</button></div>

    {landed && (
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Coste aterrizado (FX {landed.fx_cny_eur})</h3>
        <table>
          <thead>
            <tr>
              <th>Ítem</th>
              <th>Compra €</th>
              <th>Envío €</th>
              <th>Total €</th>
              <th>Unitario €</th>
            </tr>
          </thead>
          <tbody>
            {landed.items.map((item) => (
              <tr key={item.item_id}>
                <td>{item.name}</td>
                <td>{fen2yuan(item.cny_eur_cents)}</td>
                <td>{fen2yuan(item.shipment_eur_cents)}</td>
                <td>{fen2yuan(item.landed_eur_cents)}</td>
                <td>{fen2yuan(Math.round(item.landed_eur_cents / item.quantity))}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="totals">
          Total aterrizado: <strong>{fen2yuan(landed.total_landed_eur_cents)} €</strong>
        </div>
      </div>
    )}
  </div>
}

function Field({ label, value, set }) {
  return <div className="field"><label>{label}</label><input value={value} onChange={(e) => set(e.target.value)} /></div>
}
