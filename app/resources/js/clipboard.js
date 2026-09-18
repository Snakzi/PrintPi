/**
 * Copies text to the clipboard. The async Clipboard API only exists in a secure context,
 * which a PrintPi reached over plain http://printpi.local is not, so a hidden textarea
 * with the legacy copy command is the fallback there.
 */
export async function copyText(text) {
  if (window.isSecureContext && navigator.clipboard) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement('textarea');
  area.value = text;
  area.setAttribute('readonly', '');
  area.style.position = 'fixed';
  area.style.opacity = '0';
  document.body.appendChild(area);
  area.select();
  try {
    if (!document.execCommand('copy')) throw new Error('Copy failed');
  } finally {
    area.remove();
  }
}
