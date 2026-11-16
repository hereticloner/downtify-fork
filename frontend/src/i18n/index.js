import { ref } from 'vue'
import en from './locales/en.js'

// Only the fallback language is in the initial bundle. The other seven
// locales load as separate chunks when (and if) the user picks them;
// `t()` falls back to English until a chunk arrives and re-renders once
// it does, so callers never need to await a translation.
const LOADERS = {
  en: () => Promise.resolve(en),
  es: () => import('./locales/es.js'),
  'pt-BR': () => import('./locales/pt-BR.js'),
  el: () => import('./locales/el.js'),
  fr: () => import('./locales/fr.js'),
  tr: () => import('./locales/tr.js'),
  hu: () => import('./locales/hu.js'),
  bg: () => import('./locales/bg.js'),
}

// Registry of available locales. To add a new language:
//   1. Create ./locales/<code>.js exporting the same key shape as en.js
//   2. Add a loader above and an entry below — `code` is the value stored in
//      localStorage, `name` is the label shown in the language picker.
export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', load: LOADERS.en },
  { code: 'es', name: 'Español', load: LOADERS.es },
  { code: 'pt-BR', name: 'Português (BR)', load: LOADERS['pt-BR'] },
  { code: 'el', name: 'Ελληνικά', load: LOADERS.el },
  { code: 'fr', name: 'Français', load: LOADERS.fr },
  { code: 'tr', name: 'Türkçe', load: LOADERS.tr },
  { code: 'hu', name: 'Magyar', load: LOADERS.hu },
  { code: 'bg', name: 'Български', load: LOADERS.bg },
]

const DEFAULT_LOCALE = 'en'
const STORAGE_KEY = 'downtify-locale'

const stored = (() => {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
})()

const initial = AVAILABLE_LOCALES.find((l) => l.code === stored)
  ? stored
  : DEFAULT_LOCALE

export const currentLocale = ref(initial)

// Reactive message cache. Reading it inside `t()` makes every translated
// view re-render when a lazily loaded locale arrives.
const loaded = ref({ en })
const loading = new Map()

function localeEntry(code) {
  return AVAILABLE_LOCALES.find((l) => l.code === code) || AVAILABLE_LOCALES[0]
}

export function loadLocale(code) {
  if (loaded.value[code]) return Promise.resolve(loaded.value[code])
  if (!loading.has(code)) {
    loading.set(
      code,
      localeEntry(code)
        .load()
        .then((mod) => {
          const messages = mod.default || mod
          loaded.value = { ...loaded.value, [code]: messages }
          return messages
        })
        .finally(() => loading.delete(code))
    )
  }
  return loading.get(code)
}

// A locale saved from an earlier session needs its chunk on boot; en is
// already in the bundle, so the common case does no network work.
if (initial !== DEFAULT_LOCALE) void loadLocale(initial)

const PLURAL_FORMS = ['zero', 'one', 'two', 'few', 'many', 'other']

/** `{ one: '…', other: '…' }` — a message with plural forms. */
function isPlural(value) {
  return (
    value !== null &&
    typeof value === 'object' &&
    typeof value.other === 'string' &&
    Object.keys(value).every((form) => PLURAL_FORMS.includes(form))
  )
}

function lookup(messages, key) {
  if (!messages) return undefined
  const parts = key.split('.')
  let cur = messages
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object') return undefined
    cur = cur[p]
  }
  return typeof cur === 'string' || isPlural(cur) ? cur : undefined
}

const numberFormats = new Map()
const pluralRules = new Map()

function cached(map, code, make) {
  if (!map.has(code)) map.set(code, make(code))
  return map.get(code)
}

function format(template, params, code) {
  if (!params) return template
  const numbers = cached(numberFormats, code, (c) => new Intl.NumberFormat(c))
  return template.replace(/\{(\w+)\}/g, (_, name) => {
    const value = params[name]
    if (value === undefined || value === null) return `{${name}}`
    return typeof value === 'number' ? numbers.format(value) : String(value)
  })
}

export function t(key, params) {
  const code = currentLocale.value
  // Reading the reactive cache tracks every translated view: when a
  // lazily loaded locale arrives, Vue re-renders with the new messages.
  const messages = loaded.value[code] || loaded.value[DEFAULT_LOCALE]
  let msg = lookup(messages, key)
  let msgCode = code
  if (msg === undefined && code !== DEFAULT_LOCALE) {
    msg = lookup(loaded.value[DEFAULT_LOCALE], key)
    msgCode = DEFAULT_LOCALE
  }
  if (msg === undefined) return key
  if (isPlural(msg)) {
    const rules = cached(pluralRules, msgCode, (c) => new Intl.PluralRules(c))
    const count = Number(params?.count ?? 0)
    msg = msg[rules.select(count)] ?? msg.other
  }
  return format(msg, params, code)
}

export function setLocale(code) {
  if (!AVAILABLE_LOCALES.find((l) => l.code === code)) return Promise.resolve()
  currentLocale.value = code
  try {
    localStorage.setItem(STORAGE_KEY, code)
  } catch {
    // ignore storage errors (private mode, etc.)
  }
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', code)
  }
  return loadLocale(code)
}

export function useI18n() {
  return {
    t,
    locale: currentLocale,
    setLocale,
    locales: AVAILABLE_LOCALES,
  }
}

// Apply on initial load
if (typeof document !== 'undefined') {
  document.documentElement.setAttribute('lang', currentLocale.value)
}
