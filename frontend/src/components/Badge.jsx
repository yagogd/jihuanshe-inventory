import React from 'react'

const TONE = {
  ok: 'ok',
  warn: 'warn',
  err: 'err',
  neutral: 'neutral',
}

export default function Badge({ tone = 'neutral', children }) {
  return <span className={`badge ${TONE[tone] || 'neutral'}`}>{children}</span>
}
