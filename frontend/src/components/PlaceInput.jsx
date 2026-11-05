import { useEffect, useRef, useState } from 'react'
import { searchPlaces } from '../lib/api.js'

// Text box with debounced place suggestions. Value is {label, lat?, lon?};
// typing clears the coordinates so the backend geocodes free text.
export default function PlaceInput({ id, label, value, onChange, placeholder }) {
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const typed = useRef(false)
  const inputRef = useRef(null)

  useEffect(() => {
    const q = value.label.trim()
    if (!typed.current || q.length < 3 || value.lat != null) return
    const ctrl = new AbortController()
    const timer = setTimeout(() => {
      searchPlaces(q, ctrl.signal)
        .then((r) => {
          setResults(r)
          // Only show suggestions if the user is still in this field.
          setOpen(r.length > 0 && document.activeElement === inputRef.current)
          setActive(-1)
        })
        .catch(() => {})
    }, 300)
    return () => {
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [value])

  const pick = (r) => {
    typed.current = false
    onChange(r)
    setOpen(false)
  }

  const onKeyDown = (e) => {
    if (!open) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => Math.min(results.length - 1, a + 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(0, a - 1))
    } else if (e.key === 'Enter' && active >= 0) {
      e.preventDefault()
      pick(results[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="field place">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        ref={inputRef}
        value={value.label}
        placeholder={placeholder}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        onChange={(e) => {
          typed.current = true
          onChange({ label: e.target.value })
        }}
        onKeyDown={onKeyDown}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        required
      />
      {open && (
        <ul className="suggestions" id={`${id}-list`} role="listbox">
          {results.map((r, i) => (
            <li
              key={`${r.lat},${r.lon}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'active' : ''}
              onMouseDown={() => pick(r)}
            >
              {r.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
