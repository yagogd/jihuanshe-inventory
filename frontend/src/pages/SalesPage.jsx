import React, { useEffect, useMemo, useState } from 'react'
import { api, fen2yuan, yuan2fen } from '../api.js'
import Modal from '../components/Modal.jsx'
import MarketplaceIcon from '../components/MarketplaceIcon.jsx'

const DEFAULT_MARKETPLACES = [
  { code: 'CARDMARKET', name: 'Cardmarket' },
  { code: 'EBAY', name: 'eBay' },
  { code: 'WALLAPOP', name: 'Wallapop' },
]

const emptyForm = () => ({
  lot_id: '', quantity: '1',
  markets: { CARDMARKET: true, EBAY: true, WALLAPOP: false },
  prices: { CARDMARKET: '', EBAY: '', WALLAPOP: '' },
})

export default function SalesPage() {
  const [lots, setLots] = useState([])
  const [listings, setListings] = useState(null)
  const [sales, setSales] = useState(null)
  const [error, setError] = useState(null)
  const [form, setForm] = useState(emptyForm())
  const [selling, setSelling] = useState(null)
  const [editing, setEditing] = useState(null)
  const [listingQuery, setListingQuery] = useState('')
  const [marketFilter, setMarketFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [listingSort, setListingSort] = useState({ field: 'created_at', direction: 'desc' })
  const [collectionFilter, setCollectionFilter] = useState('')
  const [unpublishedSort, setUnpublishedSort] = useState('cost_desc')
  const [unpublishedQuery, setUnpublishedQuery] = useState('')
  const [marketplaces, setMarketplaces] = useState(DEFAULT_MARKETPLACES)
  const [bundles, setBundles] = useState([])
  const [bundleQuery, setBundleQuery] = useState('')
  const [bundleForm, setBundleForm] = useState({ name: '', items: [], markets: { CARDMARKET: true }, prices: {} })
  const [sellingBundle, setSellingBundle] = useState(null)
  const [editingBundle, setEditingBundle] = useState(null)
  const [editingSale, setEditingSale] = useState(null)
  const [buildingBundle, setBuildingBundle] = useState(false)

  function load() {
    api.listInventory({ available_only: true }).then(setLots).catch((e) => setError(e.message))
    api.listListings().then(setListings).catch((e) => setError(e.message))
    api.listSales().then(setSales).catch((e) => setError(e.message))
    api.listMarketplaces().then(setMarketplaces).catch((e) => setError(e.message))
    api.listBundles().then(setBundles).catch((e) => setError(e.message))
  }

  useEffect(load, [])

  const publishedLotIds = useMemo(() => new Set(
    (listings || []).filter((listing) => ['ACTIVE', 'NEEDS_REMOVAL'].includes(listing.status))
      .map((listing) => listing.lot_id)
  ), [listings])
  const unpublishedLots = lots.filter((lot) => !publishedLotIds.has(lot.id))
  const collections = [...new Set(unpublishedLots.map((lot) => lot.set_code).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b), 'es', { numeric: true }))

  const matches = useMemo(() => {
    const query = unpublishedQuery.trim().toLowerCase()
    const filtered = unpublishedLots.filter((lot) => {
      const matchesCollection = !collectionFilter || lot.set_code === collectionFilter
      const matchesQuery = !query || [lot.name, lot.name_en, lot.set_code, lot.collector_number]
        .some((value) => String(value || '').toLowerCase().includes(query))
      return matchesCollection && matchesQuery
    })
    return filtered.sort((a, b) => {
      if (unpublishedSort === 'cost_desc') return (b.unit_cost_eur_cents ?? -1) - (a.unit_cost_eur_cents ?? -1)
      if (unpublishedSort === 'cost_asc') return (a.unit_cost_eur_cents ?? Infinity) - (b.unit_cost_eur_cents ?? Infinity)
      if (unpublishedSort === 'collector') {
        const numberA = parseInt(String(a.collector_number || '').match(/\d+/)?.[0] || '999999', 10)
        const numberB = parseInt(String(b.collector_number || '').match(/\d+/)?.[0] || '999999', 10)
        return numberA - numberB || String(a.collector_number || '').localeCompare(String(b.collector_number || ''), 'es', { numeric: true })
      }
      return String(a.name_en || a.name).localeCompare(String(b.name_en || b.name), 'es', { numeric: true })
    }).slice(0, 12)
  }, [unpublishedLots, collectionFilter, unpublishedSort, unpublishedQuery])

  const selectedLot = lots.find((lot) => lot.id === form.lot_id)
  const bundleSuggestions = lots.filter((lot) => {
    const query = unpublishedQuery.trim().toLowerCase()
    return !bundleForm.items.some((item) => item.lot_id === lot.id)
      && (!collectionFilter || lot.set_code === collectionFilter)
      && (!query || [lot.name, lot.name_en, lot.set_code, lot.collector_number].some((value) => String(value || '').toLowerCase().includes(query)))
  }).sort((a, b) => {
    if (unpublishedSort === 'cost_desc') return (b.unit_cost_eur_cents ?? -1) - (a.unit_cost_eur_cents ?? -1)
    if (unpublishedSort === 'cost_asc') return (a.unit_cost_eur_cents ?? Infinity) - (b.unit_cost_eur_cents ?? Infinity)
    if (unpublishedSort === 'collector') return String(a.collector_number || '').localeCompare(String(b.collector_number || ''), 'es', { numeric: true })
    return String(a.name_en || a.name).localeCompare(String(b.name_en || b.name), 'es', { numeric: true })
  }).slice(0, 12)
  const removalTasks = (listings || []).filter((listing) => listing.status === 'NEEDS_REMOVAL')
  const bundleRemovalTasks = bundles.flatMap((bundle) => bundle.listings
    .filter((listing) => listing.status === 'NEEDS_REMOVAL')
    .map((listing) => ({ bundle, listing })))
  const visibleListings = (listings || []).filter((listing) => ['ACTIVE', 'SOLD', 'NEEDS_REMOVAL'].includes(listing.status))
  const filteredListings = visibleListings.filter((listing) => {
    const query = listingQuery.trim().toLowerCase()
    const matchesQuery = !query || [listing.name, listing.name_en, listing.set_code, listing.collector_number]
      .some((value) => String(value || '').toLowerCase().includes(query))
    return matchesQuery && (!marketFilter || listing.marketplace === marketFilter)
      && (!statusFilter || listing.status === statusFilter)
  }).sort((a, b) => {
    const values = {
      name: (row) => row.name_en || row.name,
      marketplace: (row) => row.marketplace,
      quantity: (row) => row.quantity,
      price: (row) => row.unit_price_eur_cents,
      cost: (row) => row.purchase_cost_eur_cents ?? -1,
      status: (row) => row.status,
      created_at: (row) => row.created_at,
    }
    const left = values[listingSort.field](a)
    const right = values[listingSort.field](b)
    const result = typeof left === 'number' ? left - right : String(left).localeCompare(String(right), 'es', { numeric: true })
    return listingSort.direction === 'asc' ? result : -result
  })

  function changeListingSort(field) {
    setListingSort((current) => ({ field, direction: current.field === field && current.direction === 'asc' ? 'desc' : 'asc' }))
  }

  async function createListings() {
    setError(null)
    const selectedMarkets = marketplaces.filter((market) => form.markets[market.code])
    if (!form.lot_id) return setError('Selecciona una carta.')
    if (!selectedMarkets.length) return setError('Selecciona al menos un marketplace.')
    if (selectedMarkets.some((market) => !form.prices[market.code])) {
      return setError('Indica el precio de cada marketplace seleccionado.')
    }
    try {
      for (const market of selectedMarkets) {
        await api.createListing({
          lot_id: form.lot_id,
          quantity: parseInt(form.quantity, 10) || 1,
          unit_price_eur_cents: yuan2fen(form.prices[market.code]),
          marketplace: market.code,
        })
      }
      setForm(emptyForm())
      load()
    } catch (e) { setError(e.message) }
  }

  async function confirmSell() {
    const quantity = parseInt(selling.quantity, 10)
    if (!quantity) return
    setError(null)
    try {
      await api.sellListing(selling.listing.id, {
        quantity,
        unit_price_eur_cents: yuan2fen(selling.price),
        fees_eur_cents: yuan2fen(selling.fees || '0'),
      })
      setSelling(null)
      load()
    } catch (e) { setError(e.message) }
  }

  async function deleteListing(listing) {
    setError(null)
    try { await api.deleteListing(listing.id); load() } catch (e) { setError(e.message) }
  }

  async function confirmEdit() {
    const quantity = parseInt(editing.quantity, 10)
    if (!quantity || !editing.price) return setError('Indica una cantidad y un precio válidos.')
    setError(null)
    try {
      await api.updateListing(editing.listing.id, {
        quantity,
        unit_price_eur_cents: yuan2fen(editing.price),
        marketplace: editing.marketplace,
      })
      setEditing(null)
      load()
    } catch (e) { setError(e.message) }
  }

  function addBundleLot(lot) {
    if (bundleForm.items.some((item) => item.lot_id === lot.id)) return
    setBundleForm({ ...bundleForm, items: [...bundleForm.items, { lot_id: lot.id, quantity: 1 }] })
  }

  function startBundle(lot) {
    setBundleForm({ name: '', items: [{ lot_id: lot.id, quantity: 1 }], markets: { CARDMARKET: true }, prices: {} })
    setBuildingBundle(true)
    setForm(emptyForm())
  }

  async function createBundleOffer() {
    const selectedMarkets = marketplaces.filter((market) => bundleForm.markets[market.code])
    if (!bundleForm.name.trim()) return setError('Ponle un nombre al bundle.')
    if (bundleForm.items.length < 2) return setError('Añade al menos dos cartas al bundle.')
    if (!selectedMarkets.length || selectedMarkets.some((market) => !bundleForm.prices[market.code])) return setError('Selecciona un marketplace e indica su precio.')
    setError(null)
    try {
      await api.createBundle({
        name: bundleForm.name,
        items: bundleForm.items.map((item) => ({ lot_id: item.lot_id, quantity: parseInt(item.quantity, 10) || 1 })),
        listings: selectedMarkets.map((market) => ({ marketplace: market.code, unit_price_eur_cents: yuan2fen(bundleForm.prices[market.code]) })),
      })
      setBundleForm({ name: '', items: [], markets: { CARDMARKET: true }, prices: {} }); setBuildingBundle(false); load()
    } catch (e) { setError(e.message) }
  }

  async function confirmBundleSale() {
    setError(null)
    try { await api.sellBundleListing(sellingBundle.listing.id, { quantity: 1, unit_price_eur_cents: yuan2fen(sellingBundle.price), fees_eur_cents: yuan2fen(sellingBundle.fees || '0') }); setSellingBundle(null); load() }
    catch (e) { setError(e.message) }
  }

  async function saveBundleListing() {
    setError(null)
    try { await api.updateBundleListing(editingBundle.listing.id, { marketplace: editingBundle.marketplace, unit_price_eur_cents: yuan2fen(editingBundle.price) }); setEditingBundle(null); load() }
    catch (e) { setError(e.message) }
  }

  async function deleteBundleListing(listing) {
    setError(null)
    try { await api.deleteBundleListing(listing.id); load() } catch (e) { setError(e.message) }
  }

  async function saveSale() {
    const quantity = parseInt(editingSale.quantity, 10)
    if (!quantity || !editingSale.price) return setError('Indica una cantidad y un precio válidos.')
    setError(null)
    try {
      await api.updateSale(editingSale.sale.id, { quantity, unit_price_eur_cents: yuan2fen(editingSale.price), fees_eur_cents: yuan2fen(editingSale.fees || '0') })
      setEditingSale(null)
      load()
    } catch (e) { setError(e.message) }
  }

  async function deleteSale(sale) {
    const message = sale.bundle_id
      ? '¿Eliminar esta venta del bundle? Se eliminará la transacción completa y se devolverán todas sus cartas al inventario.'
      : '¿Eliminar esta venta? Las unidades vendidas volverán al inventario.'
    if (!window.confirm(message)) return
    setError(null)
    try { await api.deleteSale(sale.id); load() } catch (e) { setError(e.message) }
  }

  return <div>
    <h1>Ventas</h1>
    {error && <div className="err">{error}</div>}

    {(removalTasks.length + bundleRemovalTasks.length) > 0 && <div className="card removal-tasks">
      <div className="removal-heading"><span className="removal-alert">!</span><div><h3>Pendiente de retirar ({removalTasks.length + bundleRemovalTasks.length})</h3><p>Acción necesaria para evitar una doble venta</p></div></div>
      <p className="muted">Cada fila es una publicación distinta. Si una carta o bundle está anunciado en varios marketplaces, debes retirar cada oferta por separado.</p>
      {removalTasks.map((listing) => <div className="removal-task" key={listing.id}>
        {listing.image_path && <img className="thumb" src={`/images/${listing.image_path}`} alt="" />}
        <MarketplaceIcon marketplace={listing.marketplace} {...marketIconProps(marketplaces, listing.marketplace)} />
        <div><span className="offer-type-badge card-badge">Carta</span> <strong>{listing.name_en || listing.name}</strong><div className="muted">{listing.set_code}·{listing.collector_number}</div></div>
        <span>{fen2yuan(listing.unit_price_eur_cents)} €</span>
        <div className="removal-actions">{listing.available > 0 && <button className="secondary" onClick={() => setEditing({ listing, quantity: String(Math.min(listing.quantity, listing.available)), price: fen2yuan(listing.unit_price_eur_cents), marketplace: listing.marketplace })}>Ajustar cantidad</button>}<button onClick={() => deleteListing(listing)}>Retirar anuncio</button></div>
      </div>)}
      {bundleRemovalTasks.map(({ bundle, listing }) => <div className="removal-task" key={`bundle-${listing.id}`}>
        <div className="bundle-mini-thumbs">{bundle.items.slice(0, 3).map((item) => item.image_path && <img key={item.lot_id} src={`/images/${item.image_path}`} alt="" />)}</div>
        <MarketplaceIcon marketplace={listing.marketplace} {...marketIconProps(marketplaces, listing.marketplace)} />
        <div><span className="offer-type-badge">Bundle</span> <strong>{bundle.name}</strong><div className="muted">{bundle.items.reduce((sum, item) => sum + item.quantity, 0)} cartas</div></div>
        <span>{fen2yuan(listing.unit_price_eur_cents)} €</span>
        <div className="removal-actions"><button onClick={() => deleteBundleListing(listing)}>Retirar anuncio</button></div>
      </div>)}
    </div>}

    <div className="card">
      <h3>Cartas por listar</h3>
      <p className="muted">Cartas disponibles que todavía no tienen anuncios activos.</p>
      <div className="field sales-card-search">
        <label>Buscar carta</label>
        <input value={unpublishedQuery} onChange={(e) => setUnpublishedQuery(e.target.value)} placeholder="Nombre, traducción, set o número…" />
      </div>
      <div className="unpublished-controls">
        <div className="field"><label>Colección</label><select value={collectionFilter} onChange={(e) => setCollectionFilter(e.target.value)}><option value="">Todas</option>{collections.map((set) => <option key={set} value={set}>{set}</option>)}</select></div>
        <div className="field"><label>Ordenar</label><select value={unpublishedSort} onChange={(e) => setUnpublishedSort(e.target.value)}><option value="cost_desc">Coste: mayor primero</option><option value="cost_asc">Coste: menor primero</option><option value="collector">Número de colección</option><option value="name">Nombre</option></select></div>
      </div>
      {!selectedLot && !buildingBundle && <div className="sales-card-results">
        {matches.map((lot) => <button className="sales-card-option" key={lot.id} onClick={() => setForm({ ...form, lot_id: lot.id })}>
          {lot.image_path ? <img src={`/images/${lot.image_path}`} alt="" /> : <span className="sales-card-no-image" />}
          <span><strong>{lot.name_en || lot.name}</strong><small>{lot.name_en ? lot.name : ''}</small><small>{lot.set_code}·{lot.collector_number} · {lot.available} disponibles</small><small className="purchase-cost-hint">Coste: {lot.unit_cost_eur_cents == null ? '—' : `${fen2yuan(lot.unit_cost_eur_cents)} €`}</small></span>
        </button>)}
        {matches.length === 0 && <span className="muted">No hay cartas disponibles que coincidan.</span>}
      </div>}
      {selectedLot && <div className="selected-sale-card">
        {selectedLot.image_path && <img src={`/images/${selectedLot.image_path}`} alt="" />}
        <div><strong>{selectedLot.name_en || selectedLot.name}</strong><div>{selectedLot.set_code}·{selectedLot.collector_number}</div><span className="muted">{selectedLot.available} disponibles</span><div className="purchase-cost-hint">Coste aterrizado: {selectedLot.unit_cost_eur_cents == null ? '—' : `${fen2yuan(selectedLot.unit_cost_eur_cents)} €`}</div></div>
        <div className="selected-sale-actions"><button className="secondary" onClick={() => setForm({ ...form, lot_id: '' })}>Cambiar carta</button><button className="secondary" onClick={() => startBundle(selectedLot)}>Añadir otra carta</button></div>
      </div>}
      {selectedLot && <>
        <div className="field" style={{ marginTop: 14 }}><label>Cantidad ofrecida</label><input type="number" min="1" max={selectedLot.available} value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} style={{ width: 85 }} /></div>
        <div className="marketplace-picker">
          {marketplaces.map((market) => <label className={`marketplace-choice${form.markets[market.code] ? ' selected' : ''}`} key={market.code}>
            <input type="checkbox" checked={Boolean(form.markets[market.code])} onChange={(e) => setForm({ ...form, markets: { ...form.markets, [market.code]: e.target.checked } })} />
            <MarketplaceIcon marketplace={market.code} iconPath={market.icon_path} name={market.name} />
            {form.markets[market.code] && <span className="market-price"><input value={form.prices[market.code] || ''} onChange={(e) => setForm({ ...form, prices: { ...form.prices, [market.code]: e.target.value } })} placeholder="0,00" /> €</span>}
          </label>)}
        </div>
        <button onClick={createListings}>Publicar anuncios</button>
      </>}
      {buildingBundle && <div className="integrated-bundle-builder">
        <div className="integrated-bundle-heading"><div><h3>Crear una oferta conjunta</h3><p className="muted">Añade otra carta para convertir la selección en un bundle.</p></div><button className="secondary" onClick={() => { setBuildingBundle(false); setBundleForm({ name: '', items: [], markets: { CARDMARKET: true }, prices: {} }) }}>Cancelar</button></div>
        <div className="bundle-selected-items">{bundleForm.items.map((item) => { const lot = lots.find((row) => row.id === item.lot_id); return lot && <div className="bundle-selected-item" key={item.lot_id}>{lot.image_path && <img src={`/images/${lot.image_path}`} alt="" />}<div><strong>{lot.name_en || lot.name}</strong><small>{lot.set_code}·{lot.collector_number}</small></div><label>Cant. <input type="number" min="1" max={lot.available} value={item.quantity} onChange={(e) => setBundleForm({ ...bundleForm, items: bundleForm.items.map((row) => row.lot_id === item.lot_id ? { ...row, quantity: e.target.value } : row) })} /></label>{bundleForm.items.length > 1 && <button className="secondary danger-button" onClick={() => setBundleForm({ ...bundleForm, items: bundleForm.items.filter((row) => row.lot_id !== item.lot_id) })}>Quitar</button>}</div> })}</div>
        <div className="bundle-results-heading"><strong>Cartas para añadir</strong><span className="muted">Usa el buscador, la colección y la ordenación de arriba.</span></div>
        <div className="bundle-suggestions">{bundleSuggestions.map((lot) => <button className="sales-card-option" key={lot.id} onClick={() => addBundleLot(lot)}>{lot.image_path ? <img src={`/images/${lot.image_path}`} alt="" /> : <span className="sales-card-no-image" />}<span><strong>{lot.name_en || lot.name}</strong><small>{lot.set_code}·{lot.collector_number} · {lot.available} disponibles</small><small className="purchase-cost-hint">Coste: {lot.unit_cost_eur_cents == null ? '—' : `${fen2yuan(lot.unit_cost_eur_cents)} €`}</small></span></button>)}{bundleSuggestions.length === 0 && <span className="muted">No hay más cartas que coincidan.</span>}</div>
        {bundleForm.items.length >= 2 && <><div className="field"><label>Nombre del bundle</label><input value={bundleForm.name} onChange={(e) => setBundleForm({ ...bundleForm, name: e.target.value })} placeholder="Por ejemplo, Pack de 4 cartas FND" /></div><div className="marketplace-picker">{marketplaces.map((market) => <label className={`marketplace-choice${bundleForm.markets[market.code] ? ' selected' : ''}`} key={market.code}><input type="checkbox" checked={Boolean(bundleForm.markets[market.code])} onChange={(e) => setBundleForm({ ...bundleForm, markets: { ...bundleForm.markets, [market.code]: e.target.checked } })} /><MarketplaceIcon marketplace={market.code} iconPath={market.icon_path} name={market.name} />{bundleForm.markets[market.code] && <span className="market-price"><input value={bundleForm.prices[market.code] || ''} onChange={(e) => setBundleForm({ ...bundleForm, prices: { ...bundleForm.prices, [market.code]: e.target.value } })} placeholder="0,00" /> €</span>}</label>)}</div><button onClick={createBundleOffer}>Publicar bundle</button></>}
      </div>}
    </div>

    <div className="card"><h3>Anuncios</h3>
      <div className="listing-filters">
        <input value={listingQuery} onChange={(e) => setListingQuery(e.target.value)} placeholder="Buscar nombre, set o número…" />
        <select value={marketFilter} onChange={(e) => setMarketFilter(e.target.value)}><option value="">Todos los marketplaces</option>{marketplaces.map((market) => <option key={market.code} value={market.code}>{market.name}</option>)}</select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="">Todos los estados</option><option value="ACTIVE">Activos</option><option value="NEEDS_REMOVAL">Pendientes de retirar</option><option value="SOLD">Vendidos</option></select>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}><option value="">Cartas y bundles</option><option value="CARD">Solo cartas</option><option value="BUNDLE">Solo bundles</option></select>
      </div>
      <table><thead><tr><th></th><SalesSortHeader label="Carta" field="name" sort={listingSort} onSort={changeListingSort} /><SalesSortHeader label="Marketplace" field="marketplace" sort={listingSort} onSort={changeListingSort} /><SalesSortHeader label="Cant." field="quantity" sort={listingSort} onSort={changeListingSort} /><SalesSortHeader label="Precio" field="price" sort={listingSort} onSort={changeListingSort} /><SalesSortHeader label="Coste compra" field="cost" sort={listingSort} onSort={changeListingSort} /><SalesSortHeader label="Estado" field="status" sort={listingSort} onSort={changeListingSort} /><th></th></tr></thead>
      <tbody>{typeFilter !== 'BUNDLE' && filteredListings.map((listing) => <tr className={listing.status === 'NEEDS_REMOVAL' ? 'listing-needs-removal' : ''} key={listing.id}>
        <td>{listing.image_path && <img className="thumb" src={`/images/${listing.image_path}`} alt="" />}</td>
        <td><span className="offer-type-badge card-badge">Carta</span> {listing.card_id ? <a href={`#/cards/${listing.card_id}`}>{listing.name_en || listing.name}</a> : <strong>{listing.name_en || listing.name}</strong>}<div className="muted">{listing.set_code}·{listing.collector_number}</div></td>
        <td><MarketplaceIcon marketplace={listing.marketplace} {...marketIconProps(marketplaces, listing.marketplace)} /></td><td>{listing.quantity}</td><td>{fen2yuan(listing.unit_price_eur_cents)} €</td><td className="purchase-cost-hint">{listing.purchase_cost_eur_cents == null ? '—' : `${fen2yuan(listing.purchase_cost_eur_cents)} €`}</td><td>{listingStatusLabel(listing.status)}</td>
        <td>{listing.status === 'ACTIVE' && <><button className="secondary" onClick={() => setEditing({ listing, quantity: String(listing.quantity), price: fen2yuan(listing.unit_price_eur_cents), marketplace: listing.marketplace })}>Editar</button>{' '}<button className="secondary" onClick={() => setSelling({ listing, quantity: String(listing.quantity), price: fen2yuan(listing.unit_price_eur_cents), fees: '0' })}>Vender</button>{' '}</>}<button className="secondary danger-button" onClick={() => deleteListing(listing)}>Retirar anuncio</button></td>
      </tr>)}{typeFilter !== 'CARD' && bundles.map((bundle) => bundle.listings.filter((listing) => ['ACTIVE', 'SOLD', 'NEEDS_REMOVAL'].includes(listing.status) && (!marketFilter || listing.marketplace === marketFilter) && (!statusFilter || listing.status === statusFilter) && (!listingQuery.trim() || [bundle.name, ...bundle.items.flatMap((item) => [item.name, item.name_en, item.set_code, item.collector_number])].some((value) => String(value || '').toLowerCase().includes(listingQuery.trim().toLowerCase())))).map((listing) => <BundleListingRows key={listing.id} bundle={bundle} listing={listing} cardListings={listings || []} marketplaces={marketplaces} onEdit={() => setEditingBundle({ bundle, listing, marketplace: listing.marketplace, price: fen2yuan(listing.unit_price_eur_cents) })} onSell={() => setSellingBundle({ bundle, listing, price: fen2yuan(listing.unit_price_eur_cents), fees: '0' })} onDelete={() => deleteBundleListing(listing)} />))}</tbody></table>
    </div>

    <div className="card"><h3>Ventas realizadas</h3><table><thead><tr><th></th><th>Carta</th><th>Cant.</th><th>Venta</th><th>Coste</th><th>Beneficio</th><th>ROI</th><th></th></tr></thead>
      <tbody>{(sales || []).map((sale) => <tr key={sale.id}><td>{sale.bundle_image_paths?.length ? <div className="sale-bundle-thumbs">{sale.bundle_image_paths.slice(0, 4).map((path, index) => <img key={`${path}-${index}`} src={`/images/${path}`} alt="" />)}</div> : sale.image_path && <img className="thumb" src={`/images/${sale.image_path}`} alt="" />}</td><td>{sale.bundle_name && <div><span className="offer-type-badge">Bundle</span> <strong>{sale.bundle_name}</strong></div>}{sale.card_id ? <a href={`#/cards/${sale.card_id}`}>{sale.name_en || sale.name}</a> : (sale.name_en || sale.name)}<div className="muted">{sale.set_code}·{sale.collector_number}</div></td><td>{sale.quantity}</td><td>{fen2yuan(sale.revenue_eur_cents)} €</td><td>{fen2yuan(sale.cost_eur_cents)} €</td><td className={sale.profit_eur_cents >= 0 ? 'ok' : 'err'}>{fen2yuan(sale.profit_eur_cents)} €</td><td>{sale.roi_pct}%</td><td><button className="secondary" onClick={() => setEditingSale({ sale, quantity: String(sale.quantity), price: fen2yuan(sale.unit_price_eur_cents), fees: fen2yuan(sale.fees_eur_cents) })}>Editar</button>{' '}<button className="secondary danger-button" onClick={() => deleteSale(sale)}>Eliminar</button></td></tr>)}{(sales || []).length === 0 && <tr><td colSpan={8} className="muted">Sin ventas todavía.</td></tr>}</tbody></table></div>

    {selling && <Modal title={`Vender · ${selling.listing.name_en || selling.listing.name}`} onClose={() => setSelling(null)} actions={<><button className="secondary" onClick={() => setSelling(null)}>Cancelar</button><button onClick={confirmSell}>Confirmar venta</button></>}>
      <div className="field"><label>Cantidad</label><input type="number" min="1" value={selling.quantity} onChange={(e) => setSelling({ ...selling, quantity: e.target.value })} /></div>
      <div className="field" style={{ marginTop: 10 }}><label>Precio real por unidad (€)</label><input value={selling.price} onChange={(e) => setSelling({ ...selling, price: e.target.value })} /></div>
      <div className="field" style={{ marginTop: 10 }}><label>Comisiones totales (€)</label><input value={selling.fees} onChange={(e) => setSelling({ ...selling, fees: e.target.value })} /></div>
    </Modal>}
    {editing && <Modal title={`Editar anuncio · ${editing.listing.name_en || editing.listing.name}`} onClose={() => setEditing(null)} actions={<><button className="secondary" onClick={() => setEditing(null)}>Cancelar</button><button onClick={confirmEdit}>Guardar cambios</button></>}>
      <div className="field"><label>Marketplace</label><select value={editing.marketplace} onChange={(e) => setEditing({ ...editing, marketplace: e.target.value })}>{marketplaces.map((market) => <option key={market.code} value={market.code}>{market.name}</option>)}</select></div>
      <div className="field" style={{ marginTop: 10 }}><label>Cantidad publicada</label><input type="number" min="1" max={editing.listing.available} value={editing.quantity} onChange={(e) => setEditing({ ...editing, quantity: e.target.value })} /></div>
      <div className="field" style={{ marginTop: 10 }}><label>Precio por unidad (€)</label><input value={editing.price} onChange={(e) => setEditing({ ...editing, price: e.target.value })} /></div>
    </Modal>}
    {sellingBundle && <Modal title={`Vender bundle · ${sellingBundle.bundle.name}`} onClose={() => setSellingBundle(null)} actions={<><button className="secondary" onClick={() => setSellingBundle(null)}>Cancelar</button><button onClick={confirmBundleSale}>Confirmar venta</button></>}><p className="muted">Se descontarán todas las cartas del bundle y se señalarán los anuncios incompatibles.</p><div className="field"><label>Precio real del bundle (€)</label><input value={sellingBundle.price} onChange={(e) => setSellingBundle({ ...sellingBundle, price: e.target.value })} /></div><div className="field" style={{ marginTop: 10 }}><label>Comisiones totales (€)</label><input value={sellingBundle.fees} onChange={(e) => setSellingBundle({ ...sellingBundle, fees: e.target.value })} /></div></Modal>}
    {editingBundle && <Modal title={`Editar anuncio · ${editingBundle.bundle.name}`} onClose={() => setEditingBundle(null)} actions={<><button className="secondary" onClick={() => setEditingBundle(null)}>Cancelar</button><button onClick={saveBundleListing}>Guardar cambios</button></>}><div className="field"><label>Marketplace</label><select value={editingBundle.marketplace} onChange={(e) => setEditingBundle({ ...editingBundle, marketplace: e.target.value })}>{marketplaces.map((market) => <option key={market.code} value={market.code}>{market.name}</option>)}</select></div><div className="field" style={{ marginTop: 10 }}><label>Precio del bundle (€)</label><input value={editingBundle.price} onChange={(e) => setEditingBundle({ ...editingBundle, price: e.target.value })} /></div></Modal>}
    {editingSale && <Modal title={`Editar venta · ${editingSale.sale.name_en || editingSale.sale.name}`} onClose={() => setEditingSale(null)} actions={<><button className="secondary" onClick={() => setEditingSale(null)}>Cancelar</button><button onClick={saveSale}>Guardar cambios</button></>}><p className="muted">Si cambias la cantidad, el inventario se ajustará automáticamente.</p><div className="field"><label>Cantidad vendida</label><input type="number" min="1" value={editingSale.quantity} onChange={(e) => setEditingSale({ ...editingSale, quantity: e.target.value })} /></div><div className="field" style={{ marginTop: 10 }}><label>Precio real por unidad (€)</label><input value={editingSale.price} onChange={(e) => setEditingSale({ ...editingSale, price: e.target.value })} /></div><div className="field" style={{ marginTop: 10 }}><label>Comisiones totales (€)</label><input value={editingSale.fees} onChange={(e) => setEditingSale({ ...editingSale, fees: e.target.value })} /></div></Modal>}
  </div>
}

function SalesSortHeader({ label, field, sort, onSort }) {
  const active = sort.field === field
  return <th aria-sort={active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}><button className="sales-sort-button" onClick={() => onSort(field)}>{label}{active ? (sort.direction === 'asc' ? ' ↑' : ' ↓') : ''}</button></th>
}

function BundleListingRows({ bundle, listing, cardListings, marketplaces, onEdit, onSell, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const totalQuantity = bundle.items.reduce((sum, item) => sum + item.quantity, 0)
  return <>
    <tr className={`bundle-table-row${listing.status === 'NEEDS_REMOVAL' ? ' listing-needs-removal' : ''}`}>
      <td><div className="bundle-mini-thumbs">{bundle.items.slice(0, 3).map((item) => item.image_path && <img key={item.lot_id} src={`/images/${item.image_path}`} alt="" />)}</div></td>
      <td><span className="offer-type-badge">Bundle</span> <strong>{bundle.name}</strong><div className="muted">{totalQuantity} cartas · <button className="bundle-detail-toggle" onClick={() => setExpanded(!expanded)}>{expanded ? 'Ocultar ofertas sueltas' : 'Ver ofertas de las cartas'}</button></div></td>
      <td><MarketplaceIcon marketplace={listing.marketplace} {...marketIconProps(marketplaces, listing.marketplace)} /></td><td>1</td><td>{fen2yuan(listing.unit_price_eur_cents)} €</td><td className="purchase-cost-hint">{fen2yuan(bundle.total_cost_eur_cents)} €</td><td>{listingStatusLabel(listing.status)}</td>
      <td>{listing.status === 'ACTIVE' && <><button className="secondary" onClick={onEdit}>Editar</button>{' '}<button className="secondary" onClick={onSell}>Vender</button>{' '}</>}<button className="secondary danger-button" onClick={onDelete}>Retirar anuncio</button></td>
    </tr>
    {expanded && <tr className="bundle-price-detail"><td></td><td colSpan={7}><div className="bundle-price-grid">{bundle.items.map((item) => {
      const individualOffers = cardListings.filter((offer) => offer.lot_id === item.lot_id && ['ACTIVE', 'NEEDS_REMOVAL'].includes(offer.status))
      return <div className="bundle-card-offers" key={item.lot_id}>{item.image_path && <img src={`/images/${item.image_path}`} alt="" />}<span><strong>{item.quantity} × {item.name_en || item.name} <span className="bundle-card-original-cost">Coste: {item.unit_cost_eur_cents == null ? '—' : `${fen2yuan(item.unit_cost_eur_cents)} €`}</span></strong>{individualOffers.length > 0 ? individualOffers.map((offer) => <small key={offer.id}><MarketplaceIcon marketplace={offer.marketplace} {...marketIconProps(marketplaces, offer.marketplace)} /> <b>{fen2yuan(offer.unit_price_eur_cents)} €</b> · {offer.quantity} ud.{offer.status === 'NEEDS_REMOVAL' && <em> · Pendiente de retirar</em>}</small>) : <small>Sin oferta individual activa</small>}</span></div>
    })}</div><p className="bundle-allocation-note">Estas son las ofertas individuales publicadas para los mismos lotes de cartas.</p></td></tr>}
  </>
}

function marketIconProps(marketplaces, code) {
  const market = marketplaces.find((item) => item.code === code)
  return { iconPath: market?.icon_path, name: market?.name }
}

function listingStatusLabel(status) {
  return status === 'ACTIVE' ? 'Activo' : status === 'SOLD' ? 'Vendido' : status === 'NEEDS_REMOVAL' ? 'Pendiente de retirar' : status
}
