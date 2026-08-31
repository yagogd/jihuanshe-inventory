import React from 'react'

const TONE = {
  ok: 'ok',
  warn: 'warn',
  err: 'err',
  neutral: 'neutral',
}

export default function Badge({ tone = 'neutral', style, children }) {
  return <span className={`badge ${TONE[tone] || 'neutral'}`} style={style}>{children}</span>
}
