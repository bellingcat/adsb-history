const baseColors = [
  '#26DE81', '#B33771', '#FF4757', '#0652DD', '#F39C12',
  '#70A1FF', '#E84393', '#00D8D6', '#C0392B', '#A742FA',
  '#FD7E14', '#1ABC9C', '#6C5CE7', '#FF9F43', '#009432',
  '#74B9FF', '#D63384', '#EE5A24', '#3498DB', '#A55EEA',
  '#CD6133', '#2980B9', '#FF6B35', '#20C997', '#6F42C1',
  '#FFDA79', '#833471', '#0D6EFD', '#E67E22', '#1DD1A1',
  '#FC427B', '#40407A', '#F1C40F', '#00A8CC', '#DC3545',
  '#A5B1C2', '#3742FA', '#218C74', '#FFA502', '#8E44AD',
  '#FF5E5B', '#006BA6', '#2ED573', '#10AC84', '#6610F2',
  '#FDCB6E', '#7158E2', '#0ABDE3', '#C44569', '#27AE60',
  '#FF3838', '#5758BB', '#16A085', '#FEA47F', '#9B59B6',
  '#F8B500', '#00CEC9', '#D35400', '#1289A7', '#FFDD59',
  '#006266', '#4834D4', '#00D2D3', '#E74C3C', '#198754',
  '#FD79A8', '#00B894', '#FF6348'
];

/**
 * Deterministic color from a string key using djb2 hash.
 * Returns a visually distinct color from a curated palette.
 */
export function getConsistentColor(key) {
  if (!key) return '#000000';

  let hash = 5381;
  for (let i = key.length - 1; i >= 0; i--) {
    const char = key.charCodeAt(i);
    hash = ((hash << 5) + hash) + char;
  }

  hash = Math.abs(hash);
  return baseColors[hash % baseColors.length];
}
