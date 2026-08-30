import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'

function toForm(order) {
  return {
    jihuanshe_order_id: order.jihuanshe_order_id || '', seller: order.seller || '',
    purchase_date: order.purchase_date || '', express_company: order.express_company || '',
    express_tracking: order.express_tracking || '', domestic_shipping: fen2yuan(order.domestic_shipping_fen),
    alipay_fee: order.alipay_fee_fen == null ? '' : fen2yuan(order.alipay_fee_fen),
    total_paid: fen2yuan(order.total_paid_fen), fx_cny_eur: String(order.fx_cny_eur),
    items: order.items.map((item) => ({ ...item, unit_price: fen2yuan(item.unit_price_fen) })),
  }
}

export default function OrderDetailPage({ id }) {
  const [order, setOrder] = useState(null)
  const [form, setForm] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getOrder(id).then((data) => { setOrder(data); setForm(toForm(data)) }).catch((e) => setError(e.message))
  }, [id])

  function updateItem(index, patch) {
    setForm((current) => ({ ...current, items: current.items.map((item, i) => i === index ? { ...item, ...patch } : item) }))
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
        fx_cny_eur: parseFloat(form.fx_cny_eur) || 0,
        items: form.items.map((item, index) => ({
          raw_name: item.raw_name, normalized_name: item.normalized_name || item.raw_name,
          game: item.game, set_code: item.set_code || null, collector_number: item.collector_number || null,
          language: item.language, condition: item.condition, variant: item.variant || null,
          promo: !!item.promo, foil: !!item.foil, quantity: parseInt(item.quantity, 10) || 1,
          unit_price_fen: yuan2fen(item.unit_price), origin: item.origin,
          include_in_allocation: item.include_in_allocation, image_path: item.image_path, position: index,
        })),
      }
      const updated = await api.updateOrder(id, payload)
      setOrder(updated); setForm(toForm(updated)); setSaved(true)
    } catch (e) { setError(e.message) } finally { setSaving(false) }
  }

  if (!order || !form) return error ? <div className="err">{error}</div> : <div className="muted">Cargando…</div>

  return <div>
    <h1>Editar orden</h1>
    <div className="card">
      {error && <div className="err">{error}</div>}{saved && <div className="ok">Cambios guardados ✓</div>}
      <div className="row" style={{ marginTop: 12 }}>
        <Field label="Nº de pedido" value={form.jihuanshe_order_id} set={(value) => setForm({ ...form, jihuanshe_order_id: value })} />
        <Field label="Vendedor" value={form.seller} set={(value) => setForm({ ...form, seller: value })} />
        <Field label="Fecha" value={form.purchase_date} set={(value) => setForm({ ...form, purchase_date: value })} />
        <Field label="Transportista" value={form.express_company} set={(value) => setForm({ ...form, express_company: value })} />
        <Field label="Seguimiento" value={form.express_tracking} set={(value) => setForm({ ...form, express_tracking: value })} />
        <Field label="Envío doméstico ¥" value={form.domestic_shipping} set={(value) => setForm({ ...form, domestic_shipping: value })} />
        <Field label="Fee Alipay ¥" value={form.alipay_fee} set={(value) => setForm({ ...form, alipay_fee: value })} />
        <Field label="Total pagado ¥" value={form.total_paid} set={(value) => setForm({ ...form, total_paid: value })} />
        <Field label="FX CNY→EUR" value={form.fx_cny_eur} set={(value) => setForm({ ...form, fx_cny_eur: value })} />
      </div>
      <div className="muted" style={{ marginTop: 12 }}>Estado: {order.status} · ID: {order.id}</div>
    </div>
    <table><thead><tr><th></th><th>Nombre</th><th>Qty</th><th>Precio ¥</th><th>Set</th><th>Nº</th><th>Variante</th><th>Promo</th></tr></thead>
      <tbody>{form.items.map((item, index) => <tr key={item.id || index}>
        <td>{item.image_path && <img className="thumb" src={`/images/${item.image_path}`} alt="" />}</td>
        <td><input value={item.normalized_name} title={item.raw_name} onChange={(e) => updateItem(index, { normalized_name: e.target.value })} /></td>
        <td><input type="number" min="1" style={{ width: 60 }} value={item.quantity} onChange={(e) => updateItem(index, { quantity: e.target.value })} /></td>
        <td><input style={{ width: 75 }} value={item.unit_price} onChange={(e) => updateItem(index, { unit_price: e.target.value })} /></td>
        <td><input style={{ width: 75 }} value={item.set_code || ''} onChange={(e) => updateItem(index, { set_code: e.target.value })} /></td>
        <td><input style={{ width: 95 }} value={item.collector_number || ''} onChange={(e) => updateItem(index, { collector_number: e.target.value })} /></td>
        <td><input style={{ width: 90 }} value={item.variant || ''} onChange={(e) => updateItem(index, { variant: e.target.value })} /></td>
        <td><input type="checkbox" checked={!!item.promo} onChange={(e) => updateItem(index, { promo: e.target.checked })} /></td>
      </tr>)}</tbody>
    </table>
    <div className="row" style={{ marginTop: 16 }}><button onClick={save} disabled={saving}>{saving ? 'Guardando…' : 'Guardar cambios'}</button></div>
  </div>
}

function Field({ label, value, set }) {
  return <div className="field"><label>{label}</label><input value={value} onChange={(e) => set(e.target.value)} /></div>
}
