// Artist profile edits that aren't part of the photo/banner picker.
import API from '/src/model/api'

/** Clear only the saved bio text; photo, banner and social links stay. */
export async function clearArtistBio(name) {
  const res = await API.deleteArtistBio(name)
  return res.data
}
