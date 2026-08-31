import React, { useEffect, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'
import Modal from '../components/Modal.jsx'

export default function SalesPage() {
  const [lots, setLots] = useState([])
  const [listings, setListings] = useState(null)
  const [sales, setSales] = useState(null)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ lot_id: '', quantity: '1', price: '' })
  const [selling, setSelling] = useState(null)

  function load() {
    api.listInventory({ available_only: true }).then(setLots).catch((e) => setError(e.message))
    api.listListings().then(setListings).catch((e) => setError(e.message))
    api.listSales().then(setSales).catch((e) => setError(e.message))
  }

  useEffect(load, [])

  async function createListing() {
    setError(null)
    try {
      await api.createListing({
        lot_id: form.lot_id,
        quantity: parseInt(form.quantity, 10) || 1,
        unit_price_eur_cents: yuan2fen(form.price),
      })
      setForm({ lot_id: '', quantity: '1', price: '' })
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function confirmSell() {
    const quantity = parseInt(selling.quantity, 10)
    if (!quantity) return
    setError(null)
    try {
      await api.sellListing(selling.listing.id, {
        quantity,
        unit_price_eur_cents: selling.listing.unit_price_eur_cents,
        fees_eur_cents: 0,
      })
      setSelling(null)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function removeListing(listing) {
    setError(null)
    try {
      await api.removeListing(listing.id)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h1>Ventas</h1>
      {error && <div className="err">{error}</div>}

      <div className="card">
        <h3>Nuevo listado</h3>
        <div className="row">
          <div className="field">
            <label>Carta</label>
            <select value={form.lot_id} onChange={(e) => setForm({ ...form, lot_id: e.target.value })}>
              <option value="">Selecciona…</option>
              {lots.map((lot) => (
                <option key={lot.id} value={lot.id}>
                  {lot.name} ({lot.available})
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Cantidad</label>
            <input
              type="number"
              min="1"
              style={{ width: 70 }}
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Precio €</label>
            <input
              style={{ width: 80 }}
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
            />
          </div>
          <button onClick={createListing}>Crear listado</button>
        </div>
      </div>

      <div className="card">
        <h3>Listados</h3>
        <table>
          <thead>
            <tr>
              <th>Carta</th>
              <th>Set/Nº</th>
              <th>Cant.</th>
              <th>Precio €</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(listings || []).map((listing) => (
              <tr key={listing.id}>
                <td>
                  {listing.name}
                  {listing.name_en && (
                    <div className="muted" style={{ fontSize: 12 }}>{listing.name_en}</div>
                  )}
                </td>
                <td className="muted">
                  {listing.set_code}·{listing.collector_number}
                </td>
                <td>{listing.quantity}</td>
                <td>{fen2yuan(listing.unit_price_eur_cents)}</td>
                <td className="muted">{listing.status}</td>
                <td>
                  {listing.status === 'ACTIVE' && (
                    <>
                      <button
                        className="secondary"
                        onClick={() => setSelling({ listing, quantity: String(listing.quantity) })}
                      >
                        Vender
                      </button>{' '}
                      <button className="secondary" onClick={() => removeListing(listing)}>
                        Quitar
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {(listings || []).length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  Sin listados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Ventas realizadas</h3>
        <table>
          <thead>
            <tr>
              <th>Carta</th>
              <th>Set/Nº</th>
              <th>Cant.</th>
              <th>Precio €</th>
              <th>Coste €</th>
              <th>Beneficio €</th>
              <th>ROI %</th>
            </tr>
          </thead>
          <tbody>
            {(sales || []).map((sale) => (
              <tr key={sale.id}>
                <td>
                  {sale.name}
                  {sale.name_en && (
                    <div className="muted" style={{ fontSize: 12 }}>{sale.name_en}</div>
                  )}
                </td>
                <td className="muted">
                  {sale.set_code}·{sale.collector_number}
                </td>
                <td>{sale.quantity}</td>
                <td>{fen2yuan(sale.revenue_eur_cents)}</td>
                <td>{fen2yuan(sale.cost_eur_cents)}</td>
                <td className={sale.profit_eur_cents >= 0 ? 'ok' : 'err'}>
                  {fen2yuan(sale.profit_eur_cents)}
                </td>
                <td>{sale.roi_pct}</td>
              </tr>
            ))}
            {(sales || []).length === 0 && (
              <tr>
                <td colSpan={7} className="muted">
                  Sin ventas todavía.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selling && (
        <Modal
          title={`Vender · ${selling.listing.name}`}
          onClose={() => setSelling(null)}
          actions={
            <>
              <button className="secondary" onClick={() => setSelling(null)}>
                Cancelar
              </button>
              <button onClick={confirmSell}>Confirmar</button>
            </>
          }
        >
          <div className="field">
            <label>Cantidad (disponible: {selling.listing.quantity})</label>
            <input
              type="number"
              min="1"
              value={selling.quantity}
              onChange={(e) => setSelling({ ...selling, quantity: e.target.value })}
            />
          </div>
        </Modal>
      )}
    </div>
  )
}
