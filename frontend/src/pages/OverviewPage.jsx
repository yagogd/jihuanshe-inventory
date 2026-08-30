import React, { useEffect, useState } from 'react'
import { api, fen2yuan } from '../api.js'

export default function OverviewPage() {
  const [overview, setOverview] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getOverview().then(setOverview).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="err">{error}</div>
  if (!overview) return <div className="muted">Cargando…</div>

  const cards = [
    { label: 'Órdenes', value: overview.orders_count, suffix: '' },
    { label: 'Invertido', value: fen2yuan(overview.invested_eur_cents), suffix: '€' },
    { label: 'Inventario (unidades)', value: overview.inventory_units, suffix: '' },
    { label: 'Valor inventario', value: fen2yuan(overview.inventory_value_eur_cents), suffix: '€' },
    { label: 'Unidades vendidas', value: overview.sold_units, suffix: '' },
    { label: 'Ingresos', value: fen2yuan(overview.revenue_eur_cents), suffix: '€' },
    { label: 'Coste vendido', value: fen2yuan(overview.cost_eur_cents), suffix: '€' },
    {
      label: 'Beneficio',
      value: fen2yuan(overview.profit_eur_cents),
      suffix: '€',
      tone: overview.profit_eur_cents >= 0 ? 'ok' : 'err',
    },
    { label: 'ROI', value: overview.roi_pct, suffix: '%' },
  ]

  return (
    <div>
      <h1>Resumen</h1>
      <div className="row">
        {cards.map((card) => (
          <div className="card" key={card.label} style={{ minWidth: 150, flex: 1 }}>
            <div className="muted" style={{ fontSize: 12 }}>
              {card.label}
            </div>
            <div className={card.tone || undefined} style={{ fontSize: 22, fontWeight: 700 }}>
              {card.value}
              {card.suffix}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
