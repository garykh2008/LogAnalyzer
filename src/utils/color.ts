// Smart color adjustment for theme contrast (matches Python adjust_color_for_theme)

function hexToRgb(hexStr: string): [number, number, number] {
  let cleanHex = hexStr.replace('#', '').trim();
  if (cleanHex.length === 3) {
    cleanHex = cleanHex.split('').map(c => c + c).join('');
  }
  const num = parseInt(cleanHex, 16);
  if (isNaN(num)) return [0, 0, 0];
  return [
    (num >> 16) & 255,
    (num >> 8) & 255,
    num & 255,
  ];
}

export function adjustColorForTheme(hexColor: string, isBackground: boolean, isDarkMode: boolean): string {
  if (!hexColor) return hexColor;
  let cleanColor = hexColor.trim().toLowerCase();
  if (!cleanColor.startsWith('#')) {
    cleanColor = '#' + cleanColor;
  }

  if (!isDarkMode) {
    return cleanColor;
  }

  // 1. Defaults adjustment
  if (isBackground && (cleanColor === '#ffffff' || cleanColor === '#fff')) {
    return '#1e1e1e';
  }
  if (!isBackground && (cleanColor === '#000000' || cleanColor === '#000')) {
    return '#d4d4d4';
  }

  // 2. Luminance checks
  const rgb = hexToRgb(cleanColor);
  const lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0;

  if (isBackground && lum > 0.4) {
    // Dim the color for dark mode background
    const r = Math.floor(rgb[0] * 0.25);
    const g = Math.floor(rgb[1] * 0.25);
    const b = Math.floor(rgb[2] * 0.25);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }
  if (!isBackground && lum < 0.5) {
    // Lighten the text for readability
    const r = Math.floor(rgb[0] + (255 - rgb[0]) * 0.6);
    const g = Math.floor(rgb[1] + (255 - rgb[1]) * 0.6);
    const b = Math.floor(rgb[2] + (255 - rgb[2]) * 0.6);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }

  return cleanColor;
}
