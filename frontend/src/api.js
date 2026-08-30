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
}

export const fen2yuan = (fen) => (fen / 100).toFixed(2)
export const yuan2fen = (yuan) => Math.round(parseFloat(yuan || '0') * 100)
