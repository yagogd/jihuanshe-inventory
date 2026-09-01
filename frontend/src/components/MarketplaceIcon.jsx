import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

let marketplaceCache = null
let marketplaceRequest = null

export default function MarketplaceIcon({ marketplace, iconPath, name }) {
  const [definition, setDefinition] = useState(() => marketplaceCache?.find((item) => item.code === marketplace))
  useEffect(() => {
    if (iconPath || definition || ['EBAY', 'WALLAPOP', 'CARDMARKET'].includes(marketplace)) return
    marketplaceRequest ||= api.listMarketplaces().then((rows) => { marketplaceCache = rows; return rows })
    marketplaceRequest.then((rows) => setDefinition(rows.find((item) => item.code === marketplace))).catch(() => {})
  }, [marketplace, iconPath, definition])
  const resolvedIcon = iconPath || definition?.icon_path
  const resolvedName = name || definition?.name || marketplace
  if (resolvedIcon) return <span className="market-logo custom" title={resolvedName} aria-label={resolvedName}><img src={`/images/${resolvedIcon}`} alt="" /></span>
  if (marketplace === 'EBAY') return (
    <span className="market-logo ebay" title="eBay" aria-label="eBay">
      <i>e</i><i>b</i><i>a</i><i>y</i>
    </span>
  )
  if (marketplace === 'WALLAPOP') return (
    <span className="market-logo wallapop" title="Wallapop" aria-label="Wallapop">∞</span>
  )
  if (marketplace === 'CARDMARKET') return (
    <span className="market-logo cardmarket" title="Cardmarket" aria-label="Cardmarket">
      <svg viewBox="0 0 34 24" role="img"><rect x="4" y="5" width="17" height="14" rx="2" /><rect x="12" y="2" width="17" height="14" rx="2" /></svg>
    </span>
  )
  return <span className="market-logo other" title={resolvedName}>{resolvedName || '?'}</span>
}
