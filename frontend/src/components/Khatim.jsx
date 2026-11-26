import React from 'react'

// Quiet Arabic ornaments drawn as inline SVG (no images, no fonts): an eight-pointed star (khatim),
// the Poetry Vision mark (an arched window holding a crescent), and a rule with a central star.

export default function Khatim({ className = '' }) {
  return (
    <svg className={'khatim ' + className} viewBox="0 0 40 40" aria-hidden="true" focusable="false">
      <rect x="9" y="9" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <rect x="9" y="9" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.4" transform="rotate(45 20 20)" />
      <circle cx="20" cy="20" r="5.2" fill="none" stroke="currentColor" strokeWidth="1.1" />
      <circle cx="20" cy="20" r="2" fill="currentColor" />
    </svg>
  )
}

export function Logo({ className = '' }) {
  return (
    <svg className={'logo-mark ' + className} viewBox="0 0 48 60" aria-hidden="true" focusable="false">
      <path d="M5 58V26C5 13 13 5 24 2c11 3 19 11 19 24v32z" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M10 58V27C10 17 16 10 24 7.5 32 10 38 17 38 27v31" fill="none" stroke="currentColor" strokeWidth=".9" opacity=".7" />
      <path d="M27.5 22.5a8 8 0 1 1-6.2-9.2 6.4 6.4 0 1 0 6.2 9.2z" fill="currentColor" />
      <path d="M31 13.2l.9 2 2.1.3-1.5 1.5.4 2.1-1.9-1-1.9 1 .4-2.1-1.5-1.5 2.1-.3z" fill="currentColor" />
      <path d="M10 46c5-3 9-3 14 0s9 3 14 0" fill="none" stroke="currentColor" strokeWidth="1.3" />
      <path d="M10 51.5c5-3 9-3 14 0s9 3 14 0" fill="none" stroke="currentColor" strokeWidth="1" opacity=".6" />
    </svg>
  )
}

export function Rule({ className = '' }) {
  return (
    <div className={'orn-rule ' + className} aria-hidden="true">
      <span className="orn-line" />
      <svg viewBox="0 0 64 16" className="orn-center" focusable="false">
        <path d="M2 8h18M44 8h18" stroke="currentColor" strokeWidth="1" />
        <path d="M32 1l3 4 4.9-.9L39 9l3 3.6-4.6 1.2L32 15l-5.4-1.2L22 12.6 25 9l-.9-4.9L29 5z" fill="none" stroke="currentColor" strokeWidth="1" />
        <circle cx="32" cy="8" r="2" fill="currentColor" />
        <circle cx="21" cy="8" r="1.2" fill="currentColor" />
        <circle cx="43" cy="8" r="1.2" fill="currentColor" />
      </svg>
      <span className="orn-line" />
    </div>
  )
}
