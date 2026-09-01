import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import Condition from '../components/Condition.jsx'
import LanguageFlag from '../components/LanguageFlag.jsx'
import Money from '../components/Money.jsx'
import MarketplaceIcon from '../components/MarketplaceIcon.jsx'

export default function CardDetailPage({ id }) {
  const [card, setCard] = useState(null)
  const [error, setError] = useState(null)
  const [nameEn, setNameEn] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api
      .getCard(id)
      .then((data) => {
        setCard(data)
        setNameEn(data.name_en || '')
      })
      .catch((e) => setError(e.message))
  }, [id])

  async function saveName() {
    setError(null)
    setSaved(false)
    try {
      const updated = await api.updateCard(id, { name_en: nameEn })
      setCard(updated)
      setSaved(true)
    } catch (e) {
      setError(e.message)
    }
  }

  async function translate() {
    setError(null)
    setSaved(false)
    try {
      const updated = await api.translateCard(id)
      setCard(updated)
      setNameEn(updated.name_en || '')
      setSaved(true)
    } catch (e) {
      setError(e.message)
    }
  }

  if (error) return <div className="err">{error}</div>
  if (!card) return <div className="muted">Cargando…</div>

  const lotsByItem = Object.fromEntries(
    card.lots.filter((lot) => lot.order_item_id).map((lot) => [lot.order_item_id, lot])
  )
  const manualLots = card.lots.filter((lot) => !lot.order_item_id)
  const landedTotal = card.purchases.reduce((sum, purchase) => sum + purchase.landed_eur_cents, 0)
  const purchasedUnits = card.purchases.reduce((sum, purchase) => sum + purchase.quantity, 0)
  const landedUnit = purchasedUnits ? Math.round(landedTotal / purchasedUnits) : null
  const landedUnitCny = purchasedUnits
    ? Math.round(card.purchases.reduce((sum, purchase) => (
        sum + (purchase.fx_cny_eur > 0 ? purchase.landed_eur_cents / purchase.fx_cny_eur : 0)
      ), 0) / purchasedUnits)
    : null

  return (
    <div>
      <h1>{card.name_en || card.name_zh || 'Carta'}</h1>
      <div className="card">
        {saved && <div className="ok">Cambios guardados ✓</div>}
        <div className="row">
          {card.image_path && (
            <img
              className="thumb"
              style={{ width: 120, height: 160 }}
              src={`/images/${card.image_path}`}
              alt=""
            />
          )}
          <div className="field" style={{ flex: 1 }}>
            <label>Nombre chino</label>
            <div>{card.name_zh || '—'}</div>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Nombre en inglés</label>
            <div className="row">
              <input
                value={nameEn}
                onChange={(e) => setNameEn(e.target.value)}
                style={{ width: 260 }}
              />
              <button className="secondary" onClick={saveName}>
                Guardar
              </button>
              <button className="secondary" onClick={translate}>
                Traducir
              </button>
            </div>
          </div>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <span className="muted">Set: {card.set_code || '—'}</span>
          <span className="muted">Nº: {card.collector_number || '—'}</span>
          <span className="muted">Juego: {card.game || '—'}</span>
          {card.variant && <span className="muted">Variante: {card.variant}</span>}
          {card.language && <LanguageFlag language={card.language} />}
          {card.foil && <span className="muted">Foil</span>}
          {card.promo && <span className="muted">Promo</span>}
        </div>
      </div>

      <div className="card-detail-summary">
        <Summary label="Compradas" value={card.total_qty} />
        <Summary label="Disponibles" value={card.stock_qty} />
        <Summary
          label="Coste unitario aterrizado"
          value={landedUnit == null
            ? '—'
            : <Money eurCents={landedUnit} cnyFen={landedUnitCny} currency="CNY" />}
        />
      </div>

      <div className="card">
        <h3>Procedencia y costes</h3>
        <p className="muted card-detail-cost-note">
          El envío doméstico y Alipay son importes totales de la orden repartidos entre
          sus cartas. El criterio aplicado aparece en cada compra.
        </p>
        <div className="purchase-cost-list">
          {card.purchases.map((purchase) => {
              const lot = lotsByItem[purchase.id]
              const chinaCosts = purchase.domestic_cny_fen + purchase.alipay_cny_fen
              const totalCnyFen = purchase.fx_cny_eur > 0
                ? Math.round(purchase.landed_eur_cents / purchase.fx_cny_eur)
                : 0
              const unitCnyFen = purchase.fx_cny_eur > 0
                ? Math.round(purchase.unit_landed_eur_cents / purchase.fx_cny_eur)
                : 0
              const purchaseEur = Math.round(purchase.purchase_cny_fen * purchase.fx_cny_eur)
              const chinaEur = Math.round(chinaCosts * purchase.fx_cny_eur)
              const internationalCny = purchase.fx_cny_eur > 0
                ? Math.round(purchase.shipment_eur_cents / purchase.fx_cny_eur)
                : 0
              return <div className="purchase-cost-card" key={purchase.id}>
                <div className="purchase-origin">
                  <div>
                    <span className="muted card-detail-meta">Comprado en</span><br />
                  <a href={`#/orders/${purchase.order_id}`}>
                    {purchase.order_name || purchase.seller || 'Ver orden'}
                  </a>
                  <div className="muted card-detail-meta">{purchase.purchase_date || 'Sin fecha'}</div>
                  {purchase.seller && purchase.order_name && (
                    <div className="muted card-detail-meta">{purchase.seller}</div>
                  )}
                  {purchase.express_tracking && (
                    <div className="muted card-detail-meta">
                      {purchase.express_company || 'Seguimiento'}: {purchase.express_tracking}
                    </div>
                  )}
                  {purchase.shipment_id && (
                    <a className="card-detail-sub-link" href={`#/shipments/${purchase.shipment_id}`}>
                      Ver envío internacional
                    </a>
                  )}
                  </div>
                  <div className="purchase-origin-status">
                    <Condition value={purchase.condition} />
                    <span>{lot ? lot.available : 0} disponibles de {lot ? lot.quantity : purchase.quantity}</span>
                  </div>
                </div>
                <div className="cost-equation">
                  <CostBlock label="Compra" cnyFen={purchase.purchase_cny_fen} eurCents={purchaseEur}>
                    {purchase.quantity} × {(purchase.unit_price_fen / 100).toFixed(2)} ¥
                  </CostBlock>
                  <span className="cost-operator">+</span>
                  <CostBlock label="Gastos en China" cnyFen={chinaCosts} eurCents={chinaEur}>
                    {!!purchase.domestic_cny_fen && <CostLine label="Envío doméstico" cnyFen={purchase.domestic_cny_fen} fx={purchase.fx_cny_eur} />}
                    {!!purchase.alipay_cny_fen && <CostLine label="Alipay repartido" cnyFen={purchase.alipay_cny_fen} fx={purchase.fx_cny_eur} />}
                    <AllocationDetail
                      cnyFen={chinaCosts}
                      eurCents={chinaEur}
                      quantity={purchase.quantity}
                      method={purchase.allocation_method}
                    />
                  </CostBlock>
                  <span className="cost-operator">+</span>
                  <CostBlock label="Envío internacional" cnyFen={internationalCny} eurCents={purchase.shipment_eur_cents}>
                    {Object.entries(purchase.shipment_alloc_cents).map(([name, cents]) => (
                      <CostLine key={name} label={name} eurCents={cents} fx={purchase.fx_cny_eur} />
                    ))}
                    <AllocationDetail
                      cnyFen={internationalCny}
                      eurCents={purchase.shipment_eur_cents}
                      quantity={purchase.quantity}
                      method={purchase.shipment_allocation_method}
                    />
                  </CostBlock>
                  <span className="cost-operator">=</span>
                  <CostBlock label="Coste aterrizado" cnyFen={totalCnyFen} eurCents={purchase.landed_eur_cents} total>
                    {purchase.quantity > 1 && (
                      <span>Por unidad: <Money eurCents={purchase.unit_landed_eur_cents} cnyFen={unitCnyFen} currency="CNY" /></span>
                    )}
                  </CostBlock>
                </div>
              </div>
            })}
          {card.purchases.length === 0 && <div className="muted">Sin compras registradas.</div>}
        </div>
      </div>

      <div className="card">
        <h3>Anuncios actuales</h3>
        <table>
          <thead><tr><th>Marketplace</th><th>Cantidad</th><th>Precio</th><th>Coste</th><th>Estado</th></tr></thead>
          <tbody>
            {card.listings.filter((listing) => ['ACTIVE', 'NEEDS_REMOVAL'].includes(listing.status)).map((listing) => (
              <tr key={listing.id}>
                <td><MarketplaceIcon marketplace={listing.marketplace} /></td>
                <td>{listing.quantity}</td>
                <td>{(listing.unit_price_eur_cents / 100).toFixed(2)} €</td>
                <td>{listing.purchase_cost_eur_cents == null ? '—' : `${(listing.purchase_cost_eur_cents / 100).toFixed(2)} €`}</td>
                <td>{listing.status === 'NEEDS_REMOVAL' ? 'Pendiente de retirar' : 'Activo'}</td>
              </tr>
            ))}
            {card.listings.filter((listing) => ['ACTIVE', 'NEEDS_REMOVAL'].includes(listing.status)).length === 0 && (
              <tr><td colSpan={5} className="muted">Esta carta no tiene anuncios activos.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Ventas realizadas</h3>
        <table>
          <thead><tr><th>Fecha</th><th>Cantidad</th><th>Venta</th><th>Coste</th><th>Beneficio</th><th>ROI</th></tr></thead>
          <tbody>
            {card.sales.map((sale) => <tr key={sale.id}>
              <td>{new Date(sale.sold_at).toLocaleDateString('es-ES')}</td>
              <td>{sale.quantity}</td>
              <td>{(sale.revenue_eur_cents / 100).toFixed(2)} €</td>
              <td>{(sale.cost_eur_cents / 100).toFixed(2)} €</td>
              <td className={sale.profit_eur_cents >= 0 ? 'ok' : 'err'}>{(sale.profit_eur_cents / 100).toFixed(2)} €</td>
              <td>{sale.roi_pct}%</td>
            </tr>)}
            {card.sales.length === 0 && <tr><td colSpan={6} className="muted">Esta carta todavía no tiene ventas.</td></tr>}
          </tbody>
        </table>
      </div>

      {manualLots.length > 0 && <div className="card">
        <h3>Stock añadido manualmente</h3>
        <p className="muted card-detail-cost-note">Unidades registradas sin una orden de compra asociada.</p>
        <table>
          <thead>
            <tr>
              <th>Disponible</th>
              <th>Total</th>
              <th>Cond.</th>
            </tr>
          </thead>
          <tbody>
            {manualLots.map((lot) => (
              <tr key={lot.id}>
                <td>
                  <strong>{lot.available}</strong>
                </td>
                <td className="muted">{lot.quantity}</td>
                <td><Condition value={lot.condition} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>}
    </div>
  )
}

function Summary({ label, value }) {
  return <div className="card summary-item"><span className="muted">{label}</span><strong>{value}</strong></div>
}

function CostBlock({ label, cnyFen, eurCents, total = false, children }) {
  return <div className={`cost-block${total ? ' cost-block-total' : ''}`}>
    <span className="cost-block-label">{label}</span>
    <strong><Money eurCents={eurCents} cnyFen={cnyFen} currency="CNY" /></strong>
    {children && <div className="cost-block-detail">{children}</div>}
  </div>
}

function CostLine({ label, cnyFen, eurCents, fx }) {
  const euros = eurCents ?? Math.round(cnyFen * fx)
  const yuan = cnyFen ?? (fx > 0 ? Math.round(eurCents / fx) : 0)
  return <span>{label}: {(yuan / 100).toFixed(2)} ¥ / {(euros / 100).toFixed(2)} €</span>
}

function AllocationDetail({ cnyFen, eurCents, quantity, method }) {
  const units = quantity || 1
  const unitCny = cnyFen / units
  const unitEur = eurCents / units
  const criterion = method === 'BY_QUANTITY'
    ? 'El coste total se divide entre el número de cartas.'
    : 'Las cartas más caras absorben una parte mayor del coste.'
  return (
    <span className="allocation-detail">
      <span className="allocation-criterion">Criterio: {criterion}</span>
      {(cnyFen / 100).toFixed(2)} ¥ / {units} ud
      {' = '}{(unitCny / 100).toFixed(2)} ¥/ud
      {' · '}{(eurCents / 100).toFixed(2)} € / {units} ud
      {' = '}{(unitEur / 100).toFixed(2)} €/ud
    </span>
  )
}
