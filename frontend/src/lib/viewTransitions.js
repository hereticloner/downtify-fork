import { nextTick } from 'vue'

// B7 — genuine snapshot transitions, feature-detected. No polyfill: when
// the API is missing (or motion is reduced) AppShell keeps its `page`
// Transition exactly as it was.
export function supportsViewTransitions() {
  return (
    typeof document !== 'undefined' &&
    typeof document.startViewTransition === 'function'
  )
}

export function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

export function installViewTransitions(router) {
  if (!supportsViewTransitions() || prefersReducedMotion()) return

  let transitioning = false

  router.beforeResolve((to, from) => {
    // No view swap for query/hash-only changes, and no overlapping snapshots.
    if (to.path === from.path || transitioning) return true

    transitioning = true
    return new Promise((resolve) => {
      document.startViewTransition(() => {
        // The browser waits for this promise before capturing the new state.
        // Let the navigation proceed, then settle after Vue has flushed the
        // DOM for the new route.
        return new Promise((settle) => {
          const remove = router.afterEach(() => {
            remove()
            transitioning = false
            nextTick(settle)
          })
          resolve(true)
        })
      })
    })
  })
}
