import { ref } from 'vue'

import API from '/src/model/api'
import { t } from '/src/i18n'
import { friendlyError } from '/src/lib/errors'

// Shape mirrors CookiesStore.status() in downtify/cookies.py.
const status = ref({
  configured: false,
  source: null,
  locked: false,
  path: null,
  size: null,
  updated_at: null,
})

const loading = ref(false)
const busy = ref(false)
const error = ref('')
const warnings = ref([])

function detailOf(err) {
  return friendlyError(t, err, 'errors.generic')
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const res = await API.getCookiesStatus()
    status.value = res.data
  } catch (err) {
    error.value = detailOf(err)
  } finally {
    loading.value = false
  }
}

async function upload(file) {
  busy.value = true
  error.value = ''
  warnings.value = []
  try {
    const res = await API.uploadCookies(file)
    const { warnings: uploadWarnings, ...rest } = res.data
    status.value = rest
    warnings.value = uploadWarnings || []
    return true
  } catch (err) {
    error.value = detailOf(err)
    return false
  } finally {
    busy.value = false
  }
}

async function remove() {
  busy.value = true
  error.value = ''
  warnings.value = []
  try {
    const res = await API.deleteCookies()
    const { deleted: _deleted, ...rest } = res.data
    status.value = rest
    return true
  } catch (err) {
    error.value = detailOf(err)
    return false
  } finally {
    busy.value = false
  }
}

export function useCookiesManager() {
  return { status, loading, busy, error, warnings, refresh, upload, remove }
}
