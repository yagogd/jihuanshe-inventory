import React, { useEffect, useState } from 'react'
import ImportPage from './pages/ImportPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import OrderDetailPage from './pages/OrderDetailPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import ShipmentsPage from './pages/ShipmentsPage.jsx'
import ShipmentDetailPage from './pages/ShipmentDetailPage.jsx'
import InventoryPage from './pages/InventoryPage.jsx'
import SalesPage from './pages/SalesPage.jsx'
import CardDetailPage from './pages/CardDetailPage.jsx'

function useHash() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash
}

export default function App() {
  const hash = useHash()
  let view = <InventoryPage />
  if (hash.startsWith('#/shipments/')) {
    view = <ShipmentDetailPage id={hash.slice('#/shipments/'.length)} />
  } else if (hash === '#/shipments') {
    view = <ShipmentsPage />
  } else if (hash.startsWith('#/cards/')) {
    view = <CardDetailPage id={hash.slice('#/cards/'.length)} />
  } else if (hash === '#/inventory') {
    view = <InventoryPage />
  } else if (hash === '#/sales') {
    view = <SalesPage />
  } else if (hash === '#/orders/import') {
    view = <ImportPage />
  } else if (hash === '#/orders/new') {
    view = <ImportPage manual />
  } else if (hash.startsWith('#/orders/')) {
    view = <OrderDetailPage id={hash.slice('#/orders/'.length)} />
  } else if (hash === '#/orders') {
    view = <OrdersPage />
  } else if (hash === '#/settings') {
    view = <SettingsPage />
  }

  const links = [
    ['#/inventory', 'Inventario'],
    ['#/orders', 'Órdenes'],
    ['#/shipments', 'Envíos'],
    ['#/sales', 'Ventas'],
  ]

  const isActive = (href) => {
    if (href === '#/inventory') return hash === '' || hash === '#/' || hash === '#' || hash === href
    return hash === href || hash.startsWith(href + '/')
  }

  return (
    <div className="app">
      <header className="app-header">
        <a className="brand" href="#/inventory">
          <span className="logo">J</span>
          Jihuanshe Tracker
        </a>
        <a className="settings-button" href="#/settings" aria-label="Ajustes" title="Ajustes">
          ⚙ Ajustes
        </a>
      </header>
      <nav>
        {links.map(([href, label]) => (
          <a key={href} href={href} className={isActive(href) ? 'active' : ''}>
            {label}
          </a>
        ))}
      </nav>
      {view}
    </div>
  )
}
