import React from 'react'

const SYMBOLS = { EUR: '€', CNY: '¥', USD: '$' }

function fmt(minor) {
  return (minor / 100).toFixed(2)
}

export default function Money({ eurCents, cnyFen, currency = 'EUR', fx = 0.13 }) {
  const minor = currency === 'CNY' ? (cnyFen != null ? cnyFen : Math.round(eurCents / fx)) : eurCents
  const symbol = SYMBOLS[currency] || '€'
  const secondary =
    currency === 'CNY'
      ? { value: eurCents, symbol: '€' }
      : cnyFen != null
        ? { value: cnyFen, symbol: '¥' }
        : null

  return (
    <span>
      <span>
        {fmt(minor)} {symbol}
      </span>
      {secondary && secondary.value != null && (
        <span className="muted" style={{ fontSize: 12, display: 'block' }}>
          {fmt(secondary.value)} {secondary.symbol}
        </span>
      )}
    </span>
  )
}
