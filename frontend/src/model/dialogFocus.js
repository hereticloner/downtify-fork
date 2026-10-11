// Shared keyboard/focus behaviour for modal dialogs: Escape closes,
// Tab is trapped inside the dialog, focus moves into it on open and
// returns to whatever opened it on close.
//
// UiModal is the canonical dialog component, but the pure helpers here
// are reused by every sheet that acts as a dialog, so all of them trap
// focus and restore it the same way.
import { nextTick, onBeforeUnmount, watch } from 'vue'
import { useUi } from '/src/model/ui'

export const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * What a keydown inside the dialog should do, or `null` when the key is
 * not ours. Kept free of the DOM so it can be unit-tested as a table.
 *
 * @returns {'close'|'focus-first'|'focus-last'|null}
 */
export function resolveDialogKey(event, { count = 0, activeIndex = -1 } = {}) {
  if (event.key === 'Escape') return 'close'
  if (event.key !== 'Tab' || count <= 0) return null
  if (event.shiftKey) return activeIndex === 0 ? 'focus-last' : null
  return activeIndex === count - 1 ? 'focus-first' : null
}

/** The focusable, visible elements inside `panel`. */
export function focusableIn(panel) {
  if (!panel?.querySelectorAll) return []
  return [...panel.querySelectorAll(FOCUSABLE_SELECTOR)].filter(
    (el) => el.offsetParent !== null
  )
}

/**
 * Builds the dialog's `keydown` handler from a way to read the
 * panel's focusables and a close callback. DOM-free by default so the
 * Escape / Tab-cycle rules can be tested without a component.
 */
export function createDialogKeyHandler({
  getFocusables,
  onClose,
  activeElement = () => document.activeElement,
}) {
  return function onDialogKeydown(event) {
    const elements = getFocusables()
    const activeIndex = elements.indexOf(activeElement())
    const intent = resolveDialogKey(event, {
      count: elements.length,
      activeIndex,
    })
    if (!intent) return false
    event.preventDefault?.()
    event.stopPropagation?.()
    if (intent === 'close') {
      onClose?.()
    } else if (intent === 'focus-first') {
      elements[0]?.focus()
    } else {
      elements.at(-1)?.focus()
    }
    return true
  }
}

/**
 * Wire a dialog's open state to the shared behaviour.
 *
 * @param {object} options
 * @param {import('vue').Ref<boolean>|(() => boolean)} options.open
 * @param {import('vue').Ref<HTMLElement|null>} options.panel The dialog element.
 * @param {() => void} options.onClose
 * @param {(panel: HTMLElement|null, items: HTMLElement[]) => HTMLElement|null}
 *   [options.initialFocus] Where focus lands on open. Defaults to the first
 *   focusable element, or the panel itself when there is none.
 * @returns {{ onKeydown: (event: KeyboardEvent) => boolean }}
 */
export function useDialogFocus({ open, panel, onClose, initialFocus }) {
  const ui = useUi()
  let modalId = null
  let returnFocus = null

  const onKeydown = createDialogKeyHandler({
    getFocusables: () => focusableIn(panel.value),
    onClose: () => onClose?.(),
  })

  function release() {
    if (modalId === null) return
    ui.popModal(modalId)
    modalId = null
    document.documentElement.style.overflow = ''
    returnFocus?.focus?.()
    returnFocus = null
  }

  watch(
    open,
    async (isOpen) => {
      if (!isOpen) {
        release()
        return
      }
      // Remember who opened us so focus goes back there on close.
      returnFocus = document.activeElement
      modalId = ui.pushModal(() => onClose?.())
      document.documentElement.style.overflow = 'hidden'
      await nextTick()
      const items = focusableIn(panel.value)
      const target = initialFocus
        ? initialFocus(panel.value, items)
        : items[0] || panel.value
      target?.focus?.()
    },
    { immediate: true }
  )

  onBeforeUnmount(release)

  return { onKeydown }
}
