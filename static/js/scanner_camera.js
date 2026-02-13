(function(){
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const statusEl = document.getElementById('status');
  const hitsEl = document.getElementById('hits');
  const startBtn = document.getElementById('start');
  const stopBtn = document.getElementById('stop');
  const apiKeyInput = document.getElementById('api_key');
  const localIdInput = document.getElementById('local_id');
  const nomInput = document.getElementById('nom');

  let stream = null;
  let scanning = false;
  let barcodeDetector = null;
  let quaggaLoaded = false;
  let rafId = null;

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function logStatus(text) { statusEl.textContent = text }
  function addHit(code, source) {
    const li = document.createElement('li');
    li.textContent = `${new Date().toLocaleTimeString()} — ${code} (${source})`;
    hitsEl.insertBefore(li, hitsEl.firstChild);
  }

  async function initDetector() {
    if ('BarcodeDetector' in window) {
      try {
        barcodeDetector = new BarcodeDetector({formats: ['ean_13','ean_8','code_128','code_39','qr_code']});
        return 'native';
      } catch (e) {
        console.warn('BarcodeDetector init failed', e);
      }
    }
    return null;
  }

  async function loadQuagga() {
    if (quaggaLoaded) return 'quagga';
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js';
      s.onload = () => {
        quaggaLoaded = true;
        resolve('quagga');
      };
      s.onerror = (e) => reject(e);
      document.head.appendChild(s);
    });
  }

  async function startCamera() {
    if (!window.isSecureContext && !['localhost', '127.0.0.1'].includes(window.location.hostname)) {
      logStatus('Caméra requiert HTTPS sur mobile');
      return false;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      logStatus('Caméra indisponible sur cet appareil');
      return false;
    }
    try {
      logStatus('Demande d\'accès à la caméra...');
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
      video.srcObject = stream;
      await video.play();
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      return true;
    } catch (e) {
      console.error('Camera error', e);
      logStatus('Permission caméra refusée ou indisponible');
      return false;
    }
  }

  async function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    if (rafId) cancelAnimationFrame(rafId);
    scanning = false;
    logStatus('Arrêté');
  }

  async function scanFrameNative() {
    if (!barcodeDetector) return;
    try {
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const bitmap = await createImageBitmap(canvas);
      const results = await barcodeDetector.detect(bitmap);
      if (results && results.length) {
        for (const r of results) {
          const code = r.rawValue || r.rawData || (r.boundingBox && JSON.stringify(r.boundingBox));
          handleDetected(code, 'native');
        }
      }
    } catch (e) {
      console.debug('Native detect error', e);
    }
  }

  function initQuaggaAndStart() {
    if (!window.Quagga) {
      console.error('Quagga not available');
      return;
    }
    const config = {
      inputStream: {
        name: 'Live',
        type: 'LiveStream',
        target: video,
        constraints: { facingMode: 'environment' }
      },
      decoder: {
        readers: ['ean_reader','ean_8_reader','code_128_reader','code_39_reader']
      },
      locate: true
    };
    window.Quagga.init(config, function(err) {
      if (err) {
        console.error(err);
        logStatus('Erreur Quagga: ' + err.message);
        return;
      }
      window.Quagga.start();
      window.Quagga.onDetected(function(data) {
        if (data && data.codeResult && data.codeResult.code) {
          handleDetected(data.codeResult.code, 'quagga');
        }
      });
    });
  }

  let lastSent = 0;
  async function handleDetected(code, source) {
    // Debounce detections
    const now = Date.now();
    if (now - lastSent < 1500) return;
    lastSent = now;
    addHit(code, source);
    logStatus('Code détecté: ' + code + ' — envoi en cours...');

    const apiKey = apiKeyInput.value.trim();
    const localId = parseInt(localIdInput.value || 0, 10);
    const nom = nomInput.value.trim();

    if (!apiKey) {
      logStatus('Erreur: clé API requise');
      return;
    }
    const safeLocalId = (!localId || isNaN(localId) || localId <= 0) ? null : localId;
    if (!safeLocalId) {
      logStatus('Info: local_id non renseigné (ok si le matériel existe déjà).');
    }

    const payload = {
      code_barre: String(code),
      numero_serie: String(code),
      local_id: safeLocalId,
      nom: nom || null,
      quantite: 1
    };

    try {
      const csrfToken = getCsrfToken();
      const headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': apiKey
      };
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }
      const res = await fetch('/api/scan_material', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.success) {
        logStatus('Enregistré: ' + (data.action || 'ok'));
      } else {
        logStatus('Erreur API: ' + (data.message || res.statusText));
      }
    } catch (e) {
      console.error('Envoi échoué', e);
      logStatus('Erreur envoi: ' + (e.message || e));
    }
  }

  async function loop() {
    if (!scanning) return;
    if (barcodeDetector) {
      await scanFrameNative();
      rafId = requestAnimationFrame(loop);
    } else if (quaggaLoaded && window.Quagga) {
      // Quagga runs internally
    } else {
      rafId = requestAnimationFrame(loop);
    }
  }

  startBtn.addEventListener('click', async function(){
    if (scanning) return;
    const ok = await startCamera();
    if (!ok) return;
    const detected = await initDetector();
    if (detected === 'native') {
      logStatus('Scanner natif activé');
    } else {
      logStatus('Scanner natif non disponible — chargement de Quagga...');
      try {
        await loadQuagga();
        initQuaggaAndStart();
        logStatus('Quagga activé');
      } catch (e) {
        console.error('Quagga load error', e);
        logStatus('Impossible d\'initialiser le scanner');
      }
    }
    scanning = true;
    loop();
  });

  stopBtn.addEventListener('click', async function(){
    await stopCamera();
  });

  // Stop on page unload
  window.addEventListener('beforeunload', stopCamera);

})();
