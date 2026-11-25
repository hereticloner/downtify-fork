import API from '/src/model/api'

export async function scanLyricsHealth() {
  const response = await API.getLyricsHealth()
  return response.data
}

export async function fillLyricsHealth(files) {
  const response = await API.fillLyricsHealth({ files })
  return response.data
}
