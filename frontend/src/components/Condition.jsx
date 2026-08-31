import React from 'react'

const STYLES = {
  M: { background: '#dbe9ff', color: '#1c4a8a', label: 'Mint' },
  NM: { background: '#d9f2e0', color: '#1e6b3a', label: 'Near Mint' },
  EX: { background: '#eaf5d3', color: '#4d7a1c', label: 'Excellent' },
  GD: { background: '#fdf0c0', color: '#8a6a00', label: 'Good' },
  LP: { background: '#fde3bf', color: '#9a5a00', label: 'Light Played' },
  PL: { background: '#fbd2c2', color: '#9a3a1c', label: 'Played' },
  PO: { background: '#f5c9c9', color: '#8a1c1c', label: 'Poor' },
}

function normalize(value) {
  if (!value) return 'NM'
  const code = String(value).trim().toUpperCase()
  if (code === '流通品相') return 'NM'
  return STYLES[code] ? code : 'NM'
}

export default function Condition({ value }) {
  const code = normalize(value)
  const style = STYLES[code]
  return (
    <span
      className="badge"
      title={style.label}
      style={{ background: style.background, color: style.color }}
    >
      {code}
    </span>
  )
}
