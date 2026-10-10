// Touch/pen long-press detection, used by the track list so a phone can
// enter bulk selection without hunting for a checkbox. The checkbox, the
// row menu and this gesture all end up in the same selection state.
//
// Mouse pointers are ignored: desktops already show the checkbox and the
// context menu, and holding the left button shouldn't select anything. A
// press that moves past `threshold` pixels (a scroll or a drag) or lifts
// before `delay` is cancelled, so scrolling a list never selects a row.
// Once the timer fires `consumeFired()` reports it so the tap that ends
// the press is swallowed and the row doesn't also start playing.
export function createLongPress({
  onLongPress,
  delay = 500,
  threshold = 10,
} = {}) {
  let timer = null
  let origin = null
  let fired = false

  function reset() {
    if (timer) clearTimeout(timer)
    timer = null
    origin = null
  }

  function down(event, payload) {
    // Every new press clears the previous gesture's flag, whatever the
    // pointer type — a stale flag must never eat a later context menu.
    fired = false
    if (event.pointerType === 'mouse') return
    // A press that starts on a control (menu, heart, checkbox) belongs to
    // that control, not to the row.
    if (event.target?.closest?.('button, a, [role="button"]')) return
    reset()
    origin = { x: event.clientX, y: event.clientY }
    timer = setTimeout(() => {
      timer = null
      fired = true
      onLongPress?.(payload)
    }, delay)
  }

  function move(event) {
    if (!timer || !origin) return
    const dx = event.clientX - origin.x
    const dy = event.clientY - origin.y
    if (Math.hypot(dx, dy) > threshold) reset()
  }

  function up() {
    reset()
  }

  // True for as long as the press is still down after a long-press fired,
  // so a context-menu event raised by the same gesture can be ignored.
  function wasFired() {
    return fired
  }

  // Consumes the flag exactly once, so the click that follows a long-press
  // is ignored but the next real tap isn't.
  function consumeFired() {
    if (!fired) return false
    fired = false
    return true
  }

  return { down, move, up, cancel: reset, wasFired, consumeFired }
}
