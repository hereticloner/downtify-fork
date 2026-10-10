// The "Select" / "Deselect" entry a track list adds to a row's context
// menu. Kept out of the component so the label switch and the action
// wiring can be unit-tested; the caller passes already-translated labels.
export function selectRowMenuItem({
  selected,
  selectLabel,
  deselectLabel,
  onToggle,
}) {
  return {
    label: selected ? deselectLabel : selectLabel,
    icon: 'check',
    action: onToggle,
  }
}
