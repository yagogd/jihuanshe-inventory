import React from 'react'

const LANGUAGE_COUNTRIES = {
  CN: 'cn', ZH: 'cn', 'ZH-CN': 'cn', CHINESE: 'cn',
  '\u7B80': 'cn', '\u4E2D': 'cn', '\u4E2D\u6587': 'cn', '\u7B80\u4F53\u4E2D\u6587': 'cn',
  TW: 'tw', 'ZH-TW': 'tw', '\u7E41': 'tw', '\u7E41\u9AD4\u4E2D\u6587': 'tw',
  EN: 'gb', ENG: 'gb', ENGLISH: 'gb',
  '\u82F1': 'gb', '\u82F1\u8BED': 'gb', '\u82F1\u8A9E': 'gb',
  JP: 'jp', JA: 'jp', JAPANESE: 'jp',
  '\u65E5': 'jp', '\u65E5\u672C\u8A9E': 'jp',
  KR: 'kr', KO: 'kr', KOREAN: 'kr',
  '\u97E9': 'kr', '\u97D3': 'kr', '\uD55C\uAD6D\uC5B4': 'kr',
  DE: 'de', GERMAN: 'de', FR: 'fr', FRENCH: 'fr',
  ES: 'es', SPANISH: 'es', IT: 'it', ITALIAN: 'it',
  PT: 'pt', PORTUGUESE: 'pt',
}

export default function LanguageFlag({ language }) {
  if (!language) return null
  const normalized = String(language).trim()
  const country = LANGUAGE_COUNTRIES[normalized.toUpperCase()]
  if (country === 'cn') {
    return (
      <img
        className="language-flag"
        src="/flags/cn.svg"
        alt="Bandera de China"
        title={normalized}
      />
    )
  }
  return (
    <svg
      className={`language-flag language-flag-${country || 'unknown'}`}
      viewBox="0 0 24 16"
      role="img"
      aria-label={`Idioma: ${normalized}`}
    >
      <title>{normalized}</title>
      <Flag country={country || 'unknown'} />
    </svg>
  )
}

function Flag({ country }) {
  if (country === 'cn') return <>
    <rect width="24" height="16" fill="#de2910" />
    <Star x="5" y="5" size="3.4" />
    <Star x="10" y="2.5" size="1.25" /><Star x="12" y="5.2" size="1.25" />
    <Star x="11.8" y="8.3" size="1.25" /><Star x="9.5" y="10.7" size="1.25" />
  </>
  if (country === 'gb') return <>
    <rect width="24" height="16" fill="#012169" />
    <path d="M0 0l24 16M24 0L0 16" stroke="#fff" strokeWidth="3.4" />
    <path d="M0 0l24 16M24 0L0 16" stroke="#c8102e" strokeWidth="1.4" />
    <path d="M12 0v16M0 8h24" stroke="#fff" strokeWidth="5" />
    <path d="M12 0v16M0 8h24" stroke="#c8102e" strokeWidth="2.8" />
  </>
  if (country === 'jp') return <><rect width="24" height="16" fill="#fff" /><circle cx="12" cy="8" r="4.2" fill="#bc002d" /></>
  if (country === 'kr') return <><rect width="24" height="16" fill="#fff" /><circle cx="12" cy="8" r="4" fill="#cd2e3a" /><path d="M8 8a4 4 0 018 0 2 2 0 01-4 0 2 2 0 00-4 0" fill="#0047a0" /></>
  if (country === 'de') return <><rect width="24" height="5.34" fill="#000" /><rect y="5.33" width="24" height="5.34" fill="#d00" /><rect y="10.66" width="24" height="5.34" fill="#ffce00" /></>
  if (country === 'fr') return <><rect width="8" height="16" fill="#0055a4" /><rect x="8" width="8" height="16" fill="#fff" /><rect x="16" width="8" height="16" fill="#ef4135" /></>
  if (country === 'it') return <><rect width="8" height="16" fill="#009246" /><rect x="8" width="8" height="16" fill="#fff" /><rect x="16" width="8" height="16" fill="#ce2b37" /></>
  if (country === 'es') return <><rect width="24" height="4" fill="#aa151b" /><rect y="4" width="24" height="8" fill="#f1bf00" /><rect y="12" width="24" height="4" fill="#aa151b" /></>
  if (country === 'pt') return <><rect width="9.6" height="16" fill="#046a38" /><rect x="9.6" width="14.4" height="16" fill="#da291c" /><circle cx="9.6" cy="8" r="2.6" fill="#ffcd00" /></>
  if (country === 'tw') return <><rect width="24" height="16" fill="#fe0000" /><rect width="12" height="8" fill="#000095" /><circle cx="6" cy="4" r="2.3" fill="#fff" /></>
  return <><rect width="24" height="16" fill="#e9e5db" /><circle cx="12" cy="8" r="5" fill="none" stroke="#8a8372" /><path d="M7 8h10M12 3a8 8 0 010 10M12 3a8 8 0 000 10" fill="none" stroke="#8a8372" strokeWidth=".8" /></>
}

function Star({ x, y, size }) {
  const points = Array.from({ length: 10 }, (_, index) => {
    const angle = -Math.PI / 2 + index * Math.PI / 5
    const radius = index % 2 === 0 ? size : size * 0.38
    return `${x + Math.cos(angle) * radius},${y + Math.sin(angle) * radius}`
  }).join(' ')
  return <polygon points={points} fill="#ffde00" />
}
