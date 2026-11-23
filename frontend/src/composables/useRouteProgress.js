import { ref } from 'vue'

// B6 — one shared progress state driven by the router. `active` mounts the
// bar; `complete` takes the fill from 70% to 100% before it fades out.
const active = ref(false)
const complete = ref(false)
let installed = false
let fillTimer
let hideTimer

export function useRouteProgress() {
  return { active, complete }
}

export function installRouteProgress(router) {
  if (installed) return
  installed = true

  router.beforeEach((to, from) => {
    // Query-only changes (e.g. the ?np=1 overlay) do not swap the view.
    if (to.path === from.path) return
    clearTimeout(fillTimer)
    clearTimeout(hideTimer)
    complete.value = false
    active.value = true
  })

  router.afterEach((to, from) => {
    if (to.path === from.path) return
    clearTimeout(fillTimer)
    fillTimer = setTimeout(() => {
      complete.value = true
      hideTimer = setTimeout(() => {
        active.value = false
        complete.value = false
      }, 200)
    }, 60)
  })
}
