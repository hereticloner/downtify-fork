export function queuePlaylistFiles(tracks = []) {
  return (tracks || [])
    .map((track) => track?.file)
    .filter((file) => typeof file === 'string' && file)
}
