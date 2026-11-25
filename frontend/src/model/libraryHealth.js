import API from '/src/model/api'

export async function scanLibraryHealth() {
  const response = await API.getLibraryHealth()
  return response.data
}

export async function exportLibraryHealth() {
  const response = await API.exportLibraryHealth({ responseType: 'blob' })
  return response.data
}
