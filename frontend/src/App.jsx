import React, { useEffect, useState } from 'react'
import ImportPage from './pages/ImportPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import OrderDetailPage from './pages/OrderDetailPage.jsx'

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
  if (hash.startsWith('#/orders/')) {
    view = <OrderDetailPage id={hash.slice('#/orders/'.length)} />
  } else if (hash === '#/orders') {
    view = <OrdersPage />
  }
  return (
    <div className="app">
      <nav>
        <a href="#/">Importar</a>
        <a href="#/orders">Órdenes</a>
      </nav>
      {view}
    </div>
  )
}
