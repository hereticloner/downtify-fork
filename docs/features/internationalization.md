---
icon: lucide/languages
---

# Internationalization

Downtify's UI is fully translatable. The default language is **English**, with seven other languages included out of the box.

## Switching language

Go to **Settings → Language** and pick your preferred language. The choice is saved in the browser's `localStorage` and applied instantly without a page reload. The page also tells the server (the `ui_language` entry of `settings.json`, see [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)), on every load and whenever you change it, so work that runs without a browser knows your language - an artist's bio, fetched in the background when one of their tracks finishes downloading, comes in it (see [When a download finishes](artist-images.md#when-a-download-finishes)). Nothing to do on your side: if you chose a language before this existed, it is picked up the next time you open Downtify. With several browsers set to different languages, the last one that loaded or changed it wins.

## Available languages

| Code | Language |
|------|---------|
| `en` | English (default) |
| `es` | Español |
| `pt-BR` | Português (Brasil) |
| `fr` | Français |
| `tr` | Türkçe |
| `el` | Ελληνικά |
| `hu` | Magyar |
| `bg` | Български |

## Adding a new language

Adding a translation is a three-step process:

### 1. Copy the English locale file

Locale files live in `frontend/src/i18n/locales/`. Each file exports a single object whose keys match the structure of `en.js`. Use an [IETF language tag](https://en.wikipedia.org/wiki/IETF_language_tag) for the file name.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/de.js
```

### 2. Translate the values

Keep keys, placeholder tokens (e.g. `{count}`, `{name}`, `{file}`) and the overall shape unchanged — only the strings on the right-hand side should change. Set `language.name` to the **native** name of the language (`"Français"`, `"Deutsch"`, …) — this is the label shown in the language picker.

### 3. Register the locale

Add an import and an entry to `AVAILABLE_LOCALES` in `frontend/src/i18n/index.js`:

```js
import de from './locales/de.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  { code: 'pt-BR', name: 'Português (BR)', messages: ptBR },
  { code: 'fr', name: 'Français', messages: fr },
  { code: 'tr', name: 'Türkçe', messages: tr },
  { code: 'el', name: 'Ελληνικά', messages: el },
  { code: 'hu', name: 'Magyar', messages: hu },
  { code: 'bg', name: 'Български', messages: bg },
  { code: 'de', name: 'Deutsch', messages: de }, // new
]
```

Rebuild the frontend and your language will appear in **Settings → Language** automatically:

```bash
cd frontend && npm run build
```

## Error messages

Error text shown in the UI is localized too. A failed request is answered with a stable, machine-readable `code` next to its English `detail` (raised as `downtify.errors.ApiError`, serialized by the exception handler in `main.py`). The web app translates the code, so the user never sees a raw `"Network Error"`, a stack-trace fragment or the backend's English `detail`.

A wrong password, for example, answers:

```json
{ "detail": "Wrong username or password", "code": "auth.invalid_credentials" }
```

`detail` is kept unchanged for API clients and logs — only the UI reads `code`. The helper `frontend/src/lib/errors.js` (`friendlyError`) maps the code to an `errors.*` translation key. A response without a code (or with one no language knows) falls back to a generic, localized message, and a request that never reached the server (offline, DNS, CORS) shows `errors.network`. Every error raised by a route carries a code, even when its raise site predates this — a plain `HTTPException` or body-validation failure gets one from its status (`downtify/errors.py`, `STATUS_CODES`). The sign-in middleware's own 401/403 refusals are handled by the app's interceptor before any text is shown.

| Key group | Covers |
|-----------|--------|
| `errors.network` | The server could not be reached |
| `errors.generic`, `errors.unknown` | Last-resort fallbacks |
| `errors.request.*` | Invalid URL/body, missing field, conflict, too large |
| `errors.auth.*` | Wrong credentials, rate limit, sign-in required, disabled |
| `errors.resource.not_found` | A missing resource |
| `errors.server.*` | Starting up, port locked or in use, internal error |
| `errors.download.*` | Downloader not ready, failed, no songs |
| `errors.spotify.*`, `errors.podcast.*` | Feature-specific failures |

Any new language must define the same `errors.*` keys as English: `frontend/src/__tests__/i18n.test.js` enforces the parity, and `frontend/src/__tests__/errors.test.js` covers the code mapping.

## Tips for translators

- Missing keys fall back to English, so partial translations work fine — submit a PR with what you have.
- Strings that depend on a number are objects with plural forms, e.g. `tracks: { one: '{count} track', other: '{count} tracks' }`. The form is chosen with the browser's [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) for your language, so add the forms your language uses (`zero`, `one`, `two`, `few`, `many`, `other`) — `other` is required. Numbers are formatted for the language automatically.
- Placeholder tokens like `{count}` or `{file}` must be left unchanged; they are substituted at runtime.
- Keep strings concise — the UI is laid out tightly and very long translations may wrap awkwardly.
- After translating, run `npm run dev` from `frontend/` and navigate every page in your language to spot anything that overflows or reads oddly in context.

Pull requests with new translations are very welcome — open a PR against `main`.
