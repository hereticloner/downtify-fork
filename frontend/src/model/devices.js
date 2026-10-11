// Paired apps (see downtify/auth.py). Kept in one place so the settings
// page's rename/revoke flows can be tested without a browser DOM.
import API from '/src/model/api'

/** Rename a paired app; the server returns the updated device. */
export async function renameDevice(id, name) {
  const res = await API.renameDevice(id, name)
  return res.data
}

/** Unpair an app; it stops working right away. */
export async function revokeDevice(id) {
  const res = await API.revokeDevice(id)
  return res.data
}
