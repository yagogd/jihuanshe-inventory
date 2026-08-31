const BASE = '/api'

async function request(path, options) {
  const response = await fetch(BASE + path, options)
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }
  return response.json()
}

export const api = {
  status: () => request('/import/status'),
  previewAuto: () => request('/import/preview?auto=true', { method: 'POST' }),
  listOrders: (status) => request('/orders' + (status ? '?status=' + encodeURIComponent(status) : '')),
  getOrder: (id) => request('/orders/' + id),
  getOrderLanded: (id) => request('/orders/' + id + '/landed'),
  setOrderStatus: (id, status) =>
    request('/orders/' + id + '/status', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    }),
  updateOrder: (id, body) =>
    request('/orders/' + id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  createOrder: (body) =>
    request('/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  getSettings: () => request('/settings'),
  updateSettings: (body) =>
    request('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listShipments: () => request('/shipments'),
  getShipment: (id) => request('/shipments/' + id),
  createShipment: (body) =>
    request('/shipments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  updateShipment: (id, body) =>
    request('/shipments/' + id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  receiveShipment: (id) => request('/shipments/' + id + '/receive', { method: 'POST' }),
  listInventory: (params) => {
    const qs = new URLSearchParams()
    for (const [key, value] of Object.entries(params || {})) {
      if (value !== undefined && value !== null && value !== '') qs.set(key, value)
    }
    const s = qs.toString()
    return request('/inventory' + (s ? '?' + s : ''))
  },
  splitLot: (id, quantity) =>
    request('/inventory/' + id + '/split', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity }),
    }),
  addLotMovement: (id, kind, quantity) =>
    request('/inventory/' + id + '/movements', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, quantity }),
    }),
  sellLot: (id, quantity, unitPriceCents, feesCents) =>
    request('/inventory/' + id + '/sell', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        quantity,
        unit_price_eur_cents: unitPriceCents,
        fees_eur_cents: feesCents || 0,
      }),
    }),
  listListings: () => request('/listings'),
  createListing: (body) =>
    request('/listings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  sellListing: (id, body) =>
    request('/listings/' + id + '/sell', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  removeListing: (id) => request('/listings/' + id + '/remove', { method: 'POST' }),
  listSales: () => request('/sales'),
  getOverview: () => request('/overview'),
  listCards: (params) => {
    const qs = new URLSearchParams()
    for (const [key, value] of Object.entries(params || {})) {
      if (value !== undefined && value !== null && value !== '') qs.set(key, value)
    }
    const s = qs.toString()
    return request('/cards' + (s ? '?' + s : ''))
  },
  getCard: (id) => request('/cards/' + id),
  updateCard: (id, body) =>
    request('/cards/' + id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listCostCategories: () => request('/cost-categories'),
  createCostCategory: (body) =>
    request('/cost-categories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
}

export const fen2yuan = (fen) => (fen / 100).toFixed(2)
export const yuan2fen = (yuan) => Math.round(parseFloat(yuan || '0') * 100)
