import React from 'react'

const FLAGS = {
  简: '🇨🇳',
  中: '🇨🇳',
  中文: '🇨🇳',
  繁: '🇹🇼',
  英: '🇬🇧',
  EN: '🇬🇧',
  English: '🇬🇧',
  日: '🇯🇵',
  韩: '🇰🇷',
  德: '🇩🇪',
  法: '🇫🇷',
  西: '🇪🇸',
  意: '🇮🇹',
  葡: '🇵🇹',
}

export default function LanguageFlag({ language }) {
  if (!language) return null
  return (
    <span title={language} style={{ fontSize: 14, lineHeight: 1 }}>
      {FLAGS[language] || '🌐'}
    </span>
  )
}
