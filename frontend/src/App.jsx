import React, { useEffect, useState } from 'react'
import ImportPage from './pages/ImportPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import OrderDetailPage from './pages/OrderDetailPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import ShipmentsPage from './pages/ShipmentsPage.jsx'
import ShipmentDetailPage from './pages/ShipmentDetailPage.jsx'

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
  let view = <ImportPage />
  if (hash.startsWith('#/shipments/')) {
    view = <ShipmentDetailPage id={hash.slice('#/shipments/'.length)} />
  } else if (hash === '#/shipments') {
    view = <ShipmentsPage />
  } else if (hash.startsWith('#/orders/')) {
    view = <OrderDetailPage id={hash.slice('#/orders/'.length)} />
  } else if (hash === '#/orders') {
    view = <OrdersPage />
  } else if (hash === '#/settings') {
    view = <SettingsPage />
  }
  return (
    <div className="app">
      <nav>
        <a href="#/">Importar</a>
        <a href="#/orders">Órdenes</a>
        <a href="#/shipments">Envíos</a>
        <a href="#/settings">Ajustes</a>
      </nav>
      {view}
    </div>
  )
}
