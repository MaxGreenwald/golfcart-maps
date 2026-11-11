// Shrink a shop logo or stop photo in the browser, then hand back base64 for the partner API.
// JPEG, PNG, and WebP only. Anything larger than 1.5 MB is scaled down before upload.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMPhoto = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const MAX = 1500000;

  function bytesToB64(bytes) {
    let s = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      s += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + chunk, bytes.length)));
    }
    return btoa(s);
  }

  function shrink(file) {
    if (typeof createImageBitmap !== 'function' || typeof document === 'undefined') {
      return Promise.reject(new Error('Use a JPEG, PNG, or WebP under 1.5 MB.'));
    }
    return createImageBitmap(file).then(bmp => new Promise((resolve, reject) => {
      const edge = 1600;
      const scale = Math.min(1, edge / Math.max(bmp.width, bmp.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(bmp.width * scale));
      canvas.height = Math.max(1, Math.round(bmp.height * scale));
      canvas.getContext('2d').drawImage(bmp, 0, 0, canvas.width, canvas.height);
      if (bmp.close) bmp.close();
      const tryQuality = (q) => {
        canvas.toBlob(blob => {
          if (!blob) { reject(new Error('Could not read that image.')); return; }
          if (blob.size <= MAX || q <= 0.45) {
            blob.arrayBuffer().then(buf => {
              const bytes = new Uint8Array(buf);
              if (bytes.length > MAX) reject(new Error('Image must be 1.5 MB or smaller.'));
              else resolve(bytes);
            }, reject);
            return;
          }
          tryQuality(q - 0.2);
        }, 'image/jpeg', q);
      };
      tryQuality(0.82);
    }));
  }

  async function prepare(file) {
    if (!file) throw new Error('Choose an image.');
    if (file.size > 30 * 1024 * 1024) throw new Error('That photo is too big (over 30 MB).');
    const typed = /^image\/(jpeg|png|webp)$/i.test(file.type || '');
    if (file.type && !typed) throw new Error('Use a JPEG, PNG, or WebP image.');
    let bytes = new Uint8Array(await file.arrayBuffer());
    if (!typed || bytes.length > MAX) bytes = await shrink(file);
    if (bytes.length > MAX) throw new Error('Image must be 1.5 MB or smaller.');
    return { data_base64: bytesToB64(bytes) };
  }

  return { MAX, bytesToB64, prepare };
});