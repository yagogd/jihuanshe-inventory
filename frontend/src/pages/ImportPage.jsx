import React, { useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'

export default function ImportPage() {
  const [status, setStatus] = useState(null)
  const [preview, setPreview] = useState(null)
  const [form, setForm] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(null)

  async function detect() {
    setError(null)
    setBusy(true)
    try {
      setStatus(await api.status())
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  function applyPreview(data) {
    setPreview(data)
    setForm({
      seller: data.seller || '',
      jihuanshe_order_id: data.jihuanshe_order_id || '',
      purchase_date: data.purchase_date || '',
      express_company: data.express_company || '',
      express_tracking: data.express_tracking || '',
      domestic_shipping: data.domestic_shipping_fen != null ? fen2yuan(data.domestic_shipping_fen) : '0',
      fx_cny_eur: '0.13',
      total_paid:
        data.declared_total_paid_fen != null ? fen2yuan(data.declared_total_paid_fen) : '',
      items: data.items.map((item) => ({
        ...item,
        unit_price: fen2yuan(item.unit_price_fen),
      })),
    })
  }

  async function doAutoPreview() {
    setError(null)
    setSaved(null)
    setBusy(true)
    try {
      const data = await api.previewAuto()
      if (!data.detected) {
        setError(data.error || 'No se detectó una orden')
        return
      }
      applyPreview(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  function updateItem(index, patch) {
    setForm((prev) => ({
      ...prev,
      items: prev.items.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    }))
  }

  async function save() {
    setError(null)
    setBusy(true)
    try {
      const payload = {
        seller: form.seller || null,
        jihuanshe_order_id: form.jihuanshe_order_id || null,
        purchase_date: form.purchase_date || null,
        express_company: form.express_company || null,
        express_tracking: form.express_tracking || null,
        domestic_shipping_fen: yuan2fen(form.domestic_shipping),
        fx_cny_eur: parseFloat(form.fx_cny_eur) || 0,
        total_paid_fen: form.total_paid ? yuan2fen(form.total_paid) : null,
        items: form.items.map((item, index) => ({
          raw_name: item.raw_name,
          normalized_name: item.normalized_name || item.raw_name,
          game: item.game,
          set_code: item.set_code,
          collector_number: item.collector_number,
          language: item.language,
          condition: item.condition,
          variant: item.variant,
          promo: item.promo,
          foil: item.foil,
          quantity: item.quantity,
          unit_price_fen: yuan2fen(item.unit_price),
          origin: item.origin,
          include_in_allocation: item.include_in_allocation,
          image_path: item.image_path,
          position: index,
        })),
        session_id: preview.session_id,
        raw_dumps: preview.raw_dumps,
        warnings: preview.warnings,
        declared_item_count: preview.declared_item_count,
      }
      const created = await api.createOrder(payload)
      setSaved(created)
      setPreview(null)
      setForm(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1>Importar orden</h1>

      <div className="card">
        <div className="row">
          <button onClick={detect} disabled={busy}>
            Detectar pantalla
          </button>
          <button onClick={doAutoPreview} disabled={busy}>
            {busy ? 'Capturando…' : 'Capturar orden automáticamente'}
          </button>
        </div>
        {status && (
          <div style={{ marginTop: 10 }}>
            {status.available ? (
              <span className={status.detected ? 'ok' : 'muted'}>
                {status.detected
                  ? `Orden detectada (${status.declared_item_count ?? '?'} artículos)`
                  : 'Sin orden detectada en pantalla'}
              </span>
            ) : (
              <span className="warn">
                ADB no disponible. Conecta el móvil y abre la orden en Jihuanshe.
              </span>
            )}
          </div>
        )}
        {error && <div className="err" style={{ marginTop: 10 }}>{error}</div>}
      </div>

      {saved && (
        <div className="card">
          <span className="ok">Orden guardada: {saved.id}</span>{' '}
          <a href={`#/orders/${saved.id}`}>Ver detalle</a>
        </div>
      )}

      {preview && form && (
        <div className="card">
          <h3>Revisión de la orden</h3>
          {preview.warnings.length > 0 && (
            <div className="warn">
              Avisos: {preview.warnings.join(' · ')}
            </div>
          )}

          <div className="row" style={{ marginBottom: 16 }}>
            <div className="field">
              <label>Nº de pedido</label>
              <input
                value={form.jihuanshe_order_id}
                onChange={(e) => setForm({ ...form, jihuanshe_order_id: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Vendedor</label>
              <input
                value={form.seller}
                onChange={(e) => setForm({ ...form, seller: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Fecha de compra</label>
              <input
                value={form.purchase_date}
                onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Envío doméstico (¥)</label>
              <input
                value={form.domestic_shipping}
                onChange={(e) => setForm({ ...form, domestic_shipping: e.target.value })}
              />
            </div>
            <div className="field">
              <label>FX CNY→EUR</label>
              <input
                value={form.fx_cny_eur}
                onChange={(e) => setForm({ ...form, fx_cny_eur: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Total pagado (¥) — vacío = auto</label>
              <input
                value={form.total_paid}
                onChange={(e) => setForm({ ...form, total_paid: e.target.value })}
              />
            </div>
          </div>

          {(form.express_company || form.express_tracking) && (
            <div className="muted" style={{ marginBottom: 12 }}>
              Envío doméstico: {form.express_company} {form.express_tracking}
            </div>
          )}

          <table>
            <thead>
              <tr>
                <th></th>
                <th>Nombre</th>
                <th>Qty</th>
                <th>Precio ¥</th>
                <th>Set/Nº</th>
                <th>Variante</th>
                <th>Promo</th>
              </tr>
            </thead>
            <tbody>
              {form.items.map((item, index) => (
                <tr key={index}>
                  <td>
                    {item.image_path && (
                      <img className="thumb" src={`/images/${item.image_path}`} alt="" />
                    )}
                  </td>
                  <td>
                    <input
                      value={item.normalized_name}
                      onChange={(e) => updateItem(index, { normalized_name: e.target.value })}
                      title={item.raw_name}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="1"
                      style={{ width: 60 }}
                      value={item.quantity}
                      onChange={(e) =>
                        updateItem(index, { quantity: parseInt(e.target.value, 10) || 1 })
                      }
                    />
                  </td>
                  <td>
                    <input
                      style={{ width: 70 }}
                      value={item.unit_price}
                      onChange={(e) => updateItem(index, { unit_price: e.target.value })}
                    />
                  </td>
                  <td className="muted">
                    {item.set_code}·{item.collector_number}
                  </td>
                  <td>
                    <input
                      style={{ width: 90 }}
                      value={item.variant || ''}
                      onChange={(e) => updateItem(index, { variant: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={!!item.promo}
                      onChange={(e) => updateItem(index, { promo: e.target.checked })}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="totals">
            <div>
              Subtotal (suma ítems): <strong>{fen2yuan(preview.subtotal_fen)} ¥</strong>
            </div>
            {preview.declared_subtotal_fen != null && (
              <div className="muted">
                Subtotal (Jihuanshe 商品总价): {fen2yuan(preview.declared_subtotal_fen)} ¥
              </div>
            )}
            <div>
              Envío doméstico: <strong>{form.domestic_shipping} ¥</strong>
            </div>
            {preview.declared_total_paid_fen != null && (
              <div className="muted">
                Total Jihuanshe (实付款): {fen2yuan(preview.declared_total_paid_fen)} ¥
              </div>
            )}
            <div>
              Fee Alipay sugerido: <strong>{fen2yuan(preview.suggested_alipay_fee_fen)} ¥</strong>
            </div>
          </div>

          <div className="row" style={{ marginTop: 16 }}>
            <button onClick={save} disabled={busy}>
              Guardar orden
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
