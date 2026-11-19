// Spanish for the renter page (/p/<shop>). p.js and friends keep writing English; this file swaps
// each rendered text node, placeholder, aria-label and title for its Spanish line when Spanish is on.
// Text inside translate="no" (shop names, ride titles, the shop's own words) is never touched.
// Language: ?lang=es or ?lang=en, then the saved choice, then the phone's language.
(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMLang = api;
})(typeof self !== 'undefined' ? self : this, function (root) {
  const KEY = 'gcm_lang';
  const DICT = {
    'Golf cart adventures': 'Paseos en carrito de golf',
    'Golf cart adventures · Golf Cart Maps': 'Paseos en carrito de golf · Golf Cart Maps',
    'Your cart, the coast, and stops worth pulling over for.': 'Tu carrito, la costa y paradas que valen la pena.',
    'You’re in. Pick a ride and follow the stops.': 'Ya entraste. Elige un paseo y sigue las paradas.',
    'Loading the welcome mat…': 'Preparando la bienvenida…',
    'Rolling up…': 'Llegando…',
    'Full city map': 'Mapa completo de la ciudad',
    'The kind of day a cart is for': 'Un día perfecto para el carrito',
    '🌴 Beach loops': '🌴 Vueltas por la playa',
    '🌮 Taco runs': '🌮 Paradas de tacos',
    '🌅 Golden hour': '🌅 Hora dorada',
    '🦭 Seal spotting': '🦭 Ver focas',
    '🍦 Ice cream stops': '🍦 Paradas de helado',
    '🐚 Cove hopping': '🐚 De caleta en caleta',
    '🌊 Harbor breeze': '🌊 Brisa del puerto',
    '⭐ Shop perks': '⭐ Beneficios de la tienda',
    'Got a code from the shop?': '¿Te dieron un código en la tienda?',
    'Access code': 'Código de acceso',
    'Unlock': 'Desbloquear',
    'Ask your rental shop for a code. Experiences unlock after you pay the add-on at checkout.': 'Pide un código en tu tienda de renta. Las experiencias se desbloquean cuando pagas el extra al rentar.',
    'The city map is free to use.': 'El mapa de la ciudad es gratis.',
    'The shop is still packing the cooler. Ask the desk, or check back.': 'La tienda todavía está preparando todo. Pregunta en el mostrador o vuelve más tarde.',
    'experience waiting': 'experiencia lista', 'experiences waiting': 'experiencias listas',
    'partner offer': 'oferta de socio', 'partner offers': 'ofertas de socios',
    'You’re in': 'Ya entraste',
    'Code': 'El código',
    'Your rental': 'Tu renta',
    'Pickup': 'Recogida', 'Return': 'Devolución', 'Return by': 'Devolver antes de',
    'Shop phone': 'Teléfono de la tienda', 'Cart rules': 'Reglas del carrito', 'If the cart dies': 'Si el carrito se apaga',
    '⬇️ Download map for offline': '⬇️ Descargar mapa sin conexión',
    'Keeps roads, stops and directions working with no signal.': 'Las calles, paradas e indicaciones funcionan sin señal.',
    'Download failed. Check your connection and try again.': 'La descarga falló. Revisa tu conexión e inténtalo otra vez.',
    'Offline, map may be outdated. Reconnect to load the latest roads.': 'Sin conexión, el mapa puede estar desactualizado. Conéctate para cargar las calles más recientes.',
    '‹ Back to experiences': '‹ Volver a las experiencias',
    'Navigate somewhere else': 'Ir a otro lugar',
    '🧭 Navigate somewhere else': '🧭 Ir a otro lugar',
    'Search a place or street': 'Busca un lugar o una calle',
    'Where to?': '¿A dónde vas?',
    'Or tap the map to drop a pin.': 'O toca el mapa para poner un pin.',
    'Route mode': 'Tipo de ruta',
    '✅ Legal only': '✅ Solo legal', '⚠️ Risky': '⚠️ Arriesgada',
    '‹ All experiences': '‹ Todas las experiencias',
    'Experiences': 'Experiencias',
    'Tap one. Its stops light up on the map.': 'Toca una. Sus paradas se iluminan en el mapa.',
    'Show stops': 'Ver paradas', 'Stops on the map': 'Paradas en el mapa',
    'No rides pinned yet. Ask the shop. Partner offers may still be on the map.': 'Todavía no hay paseos. Pregunta en la tienda: puede haber ofertas de socios en el mapa.',
    'Partner offers': 'Ofertas de socios', 'Partner offer': 'Oferta de socio',
    'No partner offers yet.': 'Todavía no hay ofertas de socios.',
    'Coupon:': 'Cupón:',
    'Places to see': 'Lugares para ver',
    'Start experience': 'Empezar la experiencia', 'Starting…': 'Empezando…',
    'Start at my nearest stop': 'Empezar en la parada más cercana', 'Use shop order': 'Seguir el orden de la tienda',
    'Starting at your nearest stop': 'Empiezas en tu parada más cercana', 'Following the shop’s order.': 'Sigues el orden de la tienda.',
    'Finding you…': 'Buscando tu ubicación…', 'Routing…': 'Calculando la ruta…',
    'Route map': 'Mapa de la ruta',
    'Next': 'Siguiente', 'Next stop': 'Siguiente parada', 'More': 'Más',
    'All steps': 'Todos los pasos', 'Hide steps': 'Ocultar pasos',
    'Play story': 'Escuchar la historia', 'Park here': 'Estaciona aquí',
    'Voice is muted. Unmute to hear this stop.': 'La voz está silenciada. Actívala para escuchar esta parada.',
    'Mute voice directions': 'Silenciar las indicaciones de voz', 'Unmute voice directions': 'Activar las indicaciones de voz',
    'Rerouting on legal roads…': 'Recalculando por calles legales…',
    'No legal golf cart road from here': 'No hay calle legal para carrito desde aquí',
    'Back to experiences any time.': 'Vuelve a las experiencias cuando quieras.',
    'That was the last stop.': 'Esa fue la última parada.',
    'Open in the Golf Cart Maps app': 'Abrir en la app Golf Cart Maps',
    'Get it on the App Store': 'Descárgala en el App Store',
    'Missing shop': 'Falta la tienda', 'This link needs a shop name on the end.': 'A este enlace le falta el nombre de la tienda al final.',
    'Shop not found': 'No encontramos la tienda', 'That link doesn’t match a rental shop.': 'Ese enlace no es de una tienda de renta.',
    'Street-legal LSV rules: roads up to 35 mph.': 'Reglas para LSV legal en calle: calles de hasta 35 mph.',
    'Golf cart rules: roads up to 25 mph.': 'Reglas para carrito de golf: calles de hasta 25 mph.',
    'Head back now to make your return time.': 'Regresa ya para llegar a tiempo.',
    'You are due back at the shop.': 'Ya deberías estar de vuelta en la tienda.',
    'This cart has little range left for the ride back.': 'A este carrito le queda poca carga para el regreso.',
    'The ride back is longer than this cart’s range.': 'El regreso es más largo que la carga de este carrito.',
    'The ride back is close to this cart’s range. Head toward the shop.': 'El regreso está cerca del límite de carga. Ve hacia la tienda.',
    'Help': 'Ayuda', 'Call shop': 'Llamar a la tienda', 'Text my location': 'Enviar mi ubicación', 'Close': 'Cerrar',
    'Call or text the shop.': 'Llama o escribe a la tienda.',
    'The text includes where you are.': 'El mensaje incluye dónde estás.',
    'No location yet. The text says so.': 'Todavía no hay ubicación. El mensaje lo indica.',
    'Now': 'Ahora', 'Continue straight': 'Sigue derecho', 'Make a U-turn': 'Da vuelta en U', 'Arrive at the stop': 'Llegas a la parada',
    'One stop. Hit Start experience to route there from you.': 'Una parada. Toca Empezar la experiencia para ir desde donde estás.',
    'Roads didn’t load. The stops are still pinned.': 'Las calles no cargaron. Las paradas siguen marcadas.',
    'A short hop off the mapped roads.': 'Un tramo corto fuera de las calles del mapa.',
    ', then around the loop in the shop’s direction, the shorter way.': ', luego la vuelta en la dirección de la tienda, que es más corta.',
    ', then around the loop the other way, which is shorter from here.': ', luego la vuelta en sentido contrario, que es más corta desde aquí.',
    ', then the stops after it, then back for the earlier ones. That’s the shorter way.': ', luego las paradas siguientes y después las anteriores. Así es más corto.',
    ', then back through the earlier stops, then on to the later ones. That’s the shorter way.': ', luego las paradas anteriores y después las siguientes. Así es más corto.',
    'That was the last stop. Nice ride!': 'Esa fue la última parada. ¡Buen paseo!',
    'Finding a cart-friendly route…': 'Buscando una ruta para carrito…',
    'No way through, even with risky stretches.': 'No hay paso, ni siquiera con tramos arriesgados.',
    'No legal route there. Try ⚠️ Risky to see short-stretch options.': 'No hay ruta legal. Prueba ⚠️ Arriesgada para ver opciones con tramos cortos.',
    'This ride has no stops yet.': 'Este paseo todavía no tiene paradas.',
    'Location is off.': 'La ubicación está apagada.', 'Turn it on to start from you.': 'Actívala para empezar desde donde estás.',
    'This short hop starts from the middle of the map.': 'Este tramo corto empieza en el centro del mapa.',
    'This route starts from the middle of the map.': 'Esta ruta empieza en el centro del mapa.',
    'A short hop from you to the first stop.': 'Un tramo corto desde ti hasta la primera parada.',
    'Legal golf cart roads from you to the first stop.': 'Calles legales para carrito desde ti hasta la primera parada.',
    'Map couldn’t load. Your stops are still listed above.': 'El mapa no cargó. Tus paradas siguen en la lista de arriba.',
    'Map failed to load': 'El mapa no cargó', 'Could not unlock': 'No se pudo desbloquear', 'Could not open the app': 'No se pudo abrir la app',
    'No connection. Try again in a moment.': 'Sin conexión. Inténtalo otra vez en un momento.',
    'Dropped pin': 'Pin en el mapa', 'the stop': 'la parada',
    'Restaurant': 'Restaurante', 'Views': 'Vistas', 'Trivia': 'Curiosidades', 'Fun fact': 'Dato curioso', 'Other': 'Otro',
    'The search stopped before it finished.': 'La búsqueda se detuvo antes de terminar.',
    'Turn this off for a street-legal LSV.': 'Desactívalo si tienes un LSV legal en calle.',
    'Even short stretches of faster roads (up to 500 ft) don’t connect these points.': 'Ni con tramos cortos de calles más rápidas (hasta 500 ft) se conectan estos puntos.',
    'Try ⚠️ Risky to see short stretches of faster roads.': 'Prueba ⚠️ Arriesgada para ver tramos cortos de calles más rápidas.',
    'Every way there leaves the cart paths/designated roads.': 'Todos los caminos salen de las sendas o calles designadas para carritos.',
    'Plain golf carts aren\'t street-legal here, so only cart paths count.': 'Aquí los carritos de golf comunes no son legales en la calle, así que solo cuentan las sendas para carritos.',
    'Switch to 🚙 LSV if yours is street-legal.': 'Cambia a 🚙 LSV si el tuyo es legal en calle.',
    'Use caution.': 'Ten cuidado.',
    'Turn on location, or follow the pins.': 'Activa la ubicación o sigue los pines.',
    'Español': 'Español', 'English': 'English',
  };
  const TURN = { left: 'a la izquierda', right: 'a la derecha', 'slight left': 'ligeramente a la izquierda', 'slight right': 'ligeramente a la derecha', 'sharp left': 'fuerte a la izquierda', 'sharp right': 'fuerte a la derecha' };
  const DIR = { north: 'norte', northeast: 'noreste', east: 'este', southeast: 'sureste', south: 'sur', southwest: 'suroeste', west: 'oeste', northwest: 'noroeste' };
  const VEH = { 'golf cart': 'un carrito de golf', 'street-legal LSV': 'un LSV legal en calle' };
  const lower = s => s.charAt(0).toLowerCase() + s.slice(1);
  const name = s => (s === 'the stop' || s === 'Dropped pin' ? DICT[s] : s);
  const MODE = s => ({ 'Street-legal LSV': 'LSV legal en calle', 'Cart paths only': 'Solo sendas para carritos', 'Designated cart roads only': 'Solo calles designadas para carritos', 'Plain golf cart rules': 'Reglas para carrito de golf' })[s]
    || s.replace(/^Under (\d+) mph roads only$/, 'Solo calles de menos de $1 mph');
  const LIMIT = s => ({ 'only cart paths count': 'solo cuentan las sendas para carritos', 'only cart paths and designated roads': 'solo sendas y calles designadas para carritos' })[s]
    || s.replace(/^only roads posted (\d+) mph or under$/, 'solo calles con límite de $1 mph o menos');
  const PATTERNS = [
    [/^unlocked (.+)\. Pick a ride, then start from where you are\.$/, m => `desbloqueó ${m[1]}. Elige un paseo y empieza desde donde estás.`],
    [/^(\d+) stops?$/, m => `${m[1]} ${m[1] === '1' ? 'parada' : 'paradas'}`],
    [/^(\d+) partner offers?$/, m => `${m[1]} ${m[1] === '1' ? 'oferta de socio' : 'ofertas de socios'}`],
    [/^(\d+) (experience|experiences) waiting$/, m => `${m[1]} ${m[1] === '1' ? 'experiencia lista' : 'experiencias listas'}`],
    [/^Stop (\d+)\/(\d+): (.*)$/, m => `Parada ${m[1]}/${m[2]}: ${m[3] === 'Stop' ? 'Parada' : m[3]}`],
    [/^Follows legal (golf cart|street-legal LSV) roads\.$/, m => `Sigue calles legales para ${VEH[m[1]]}.`],
    [/^A hop off that network is left open\.$/, () => 'Un tramo fuera de esa red queda sin ruta.'],
    [/^The line follows legal (golf cart|street-legal LSV) roads\.$/, m => `La línea sigue calles legales para ${VEH[m[1]]}.`],
    [/^Tracing (golf cart|street-legal LSV) roads…$/, m => `Trazando calles para ${VEH[m[1]]}…`],
    [/^You’ve arrived at ((?:(?!\. ).)+)\.$/, m => `Llegaste a ${name(m[1])}.`],
    [/^Next stop: (.+)\.$/, m => `Siguiente parada: ${m[1]}.`],
    [/^(\S+) mi on legal golf cart roads\.$/, m => `${m[1]} mi por calles legales para carrito.`],
    [/^(\S+) mi · ⚠️ (\d+) risky stretch(?:es)? \(red dashes\)\.$/, m => `${m[1]} mi · ⚠️ ${m[2]} ${m[2] === '1' ? 'tramo arriesgado' : 'tramos arriesgados'} (rayas rojas).`],
    [/^Location is off, and there’s no legal (golf cart|street-legal LSV) road from the middle of the map to the first stop\.$/, m => `La ubicación está apagada y no hay calle legal para ${VEH[m[1]]} desde el centro del mapa hasta la primera parada.`],
    [/^Every way there uses a (\d+)\+ mph road\.$/, m => `Todos los caminos usan una calle de ${m[1]}+ mph.`],
    [/^(Street-legal LSV|Cart paths only|Designated cart roads only|Under \d+ mph roads only|Plain golf cart rules): (only cart paths count|only cart paths and designated roads|only roads posted \d+ mph or under)\.$/, m => `${MODE(m[1])}: ${LIMIT(m[2])}.`],
    [/^You’ve arrived at the stop$/, () => 'Llegaste a la parada'],
    [/^You’ve arrived at ((?:(?!\. ).)+)$/, m => `Llegaste a ${name(m[1])}`],
    [/^Next: stop (\d+), (.*)$/, m => `Siguiente: parada ${m[1]}, ${m[2]}`],
    [/^Go to stop (\d+)$/, m => `Ir a la parada ${m[1]}`],
    [/^Follow the pin to stop (\d+)\.$/, m => `Sigue el pin hasta la parada ${m[1]}.`],
    [/^Then (.+) in (\S+ (?:mi|ft|m|km))$/, m => `Luego, ${lower(t(m[1].charAt(0).toUpperCase() + m[1].slice(1)))} en ${m[2]}`],
    [/^Turn (slight left|slight right|sharp left|sharp right|left|right) onto (.+)$/, m => `Gira ${TURN[m[1]]} en ${m[2]}`],
    [/^Turn (slight left|slight right|sharp left|sharp right|left|right)$/, m => `Gira ${TURN[m[1]]}`],
    [/^Continue onto (.+)$/, m => `Continúa por ${m[1]}`],
    [/^Continue on (.+)$/, m => `Sigue por ${m[1]}`],
    [/^Head (north|northeast|east|southeast|south|southwest|west|northwest) on (.+)$/, m => `Ve hacia el ${DIR[m[1]]} por ${m[2]}`],
    [/^Head (north|northeast|east|southeast|south|southwest|west|northwest)$/, m => `Ve hacia el ${DIR[m[1]]}`],
    [/^Make a U-turn onto (.+)$/, m => `Da vuelta en U en ${m[1]}`],
    [/^Arrive at stop (\d+)$/, m => `Llegas a la parada ${m[1]}`],
    [/^In (\S+ (?:mi|ft)), (.+)$/, m => `En ${m[1]}, ${lower(t(m[2].charAt(0).toUpperCase() + m[2].slice(1)))}`],
    [/^Arrive at (.+)$/, m => `Llegas a ${name(m[1])}`],
    [/^Green roads are legal for a (golf cart|street-legal LSV)\. Red roads are off limits\. The blue line is your route\.$/, m => `Las calles verdes son legales para ${VEH[m[1]]}. Las rojas están prohibidas. La línea azul es tu ruta.`],
    [/^Numbered pins are stops\. Amber ★ pins are partner offers\.( Icon pins \((.+)\) are places to see\. Tap one to read about it\.)?$/, m => 'Los pines con número son paradas. Los pines ámbar ★ son ofertas de socios.' + (m[1] ? ` Los pines con ícono (${m[2]}) son lugares para ver. Toca uno para leer más.` : '')],
    [/^Head back in 1 minute\.$/, () => 'Regresa en 1 minuto.'],
    [/^Head back in (\d+) minutes\.$/, m => `Regresa en ${m[1]} minutos.`],
    [/^⬇️ Download map for offline \((.+)\)$/, m => `⬇️ Descargar mapa sin conexión (${m[1]})`],
    [/^⬇️ Downloading (\d+)% \((.+)\)$/, m => `⬇️ Descargando ${m[1]}% (${m[2]})`],
    [/^✅ (.+) saved for offline$/, m => `✅ ${m[1]} guardado sin conexión`],
    [/^Saved (.+) \((.+)\)\. Updates itself when you are online\. Tap to remove\.$/, m => `Guardado ${m[1]} (${m[2]}). Se actualiza cuando tienes conexión. Toca para borrarlo.`],
    [/^☀️ (.+) · hop in$/, m => `☀️ ${m[1]} · súbete`],
    [/^Farther away \(over (.+) mi\)$/, m => `Más lejos (a más de ${m[1]} mi)`],
    [/^Call or text (.+)\.$/, m => `Llama o escribe al ${m[1]}.`],
    [/^Call (.+)$/, m => `Llamar al ${m[1]}`],
    [/^Don’t have the app\?$/, () => '¿No tienes la app?'],
    [/^, then tap this button again\.$/, () => ' y vuelve a tocar este botón.'],
  ];
  const ES = new Set(Object.values(DICT));
  function one(p) {
    if (Object.prototype.hasOwnProperty.call(DICT, p)) return DICT[p];
    for (const [re, fn] of PATTERNS) { const r = re.exec(p); if (r) return fn(r); }
    return p;
  }
  /** English line to Spanish (unknown lines come back unchanged). */
  function t(s) {
    const src = String(s == null ? '' : s);
    const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(src);
    const core = m[2];
    if (!core) return src;
    if (Object.prototype.hasOwnProperty.call(DICT, core)) return m[1] + DICT[core] + m[3];
    for (const [re, fn] of PATTERNS) { const r = re.exec(core); if (r) return m[1] + fn(r) + m[3]; }
    // Lines built from several sentences (route notes, arrival callouts): translate each sentence.
    const parts = core.split(/(?<=[.!?…])\s+/);
    if (parts.length > 1) {
      const out = parts.map(p => one(p));
      if (out.some((o, i) => o !== parts[i])) return m[1] + out.join(' ') + m[3];
    }
    return src;
  }
  function pick(search, saved, nav) {
    const q = /[?&]lang=(es|en)\b/i.exec(search || '');
    if (q) return q[1].toLowerCase();
    if (saved === 'es' || saved === 'en') return saved;
    return /^es\b/i.test(nav || '') ? 'es' : 'en';
  }
  let cur = 'en';
  try { cur = pick(root.location && root.location.search, root.localStorage && root.localStorage.getItem(KEY), root.navigator && root.navigator.language); } catch (_) {}
  const ATTRS = ['placeholder', 'aria-label', 'title'];
  const texts = new Map(), attrs = new Map(); // node -> English source
  let obs = null, scope = null, busy = false;
  function skip(el) {
    for (let e = el; e && e.nodeType === 1; e = e.parentNode) {
      if (e.getAttribute('translate') === 'no' || e.tagName === 'SCRIPT' || e.tagName === 'STYLE' || e.tagName === 'TEXTAREA') return true;
    }
    return false;
  }
  function doText(n) {
    if (skip(n.parentNode)) return;
    const prev = texts.get(n);
    let src = n.nodeValue;
    if (prev && (src === prev.out)) src = prev.src;
    const out = cur === 'es' ? t(src) : src;
    if (out !== src || prev) texts.set(n, { src, out });
    if (n.nodeValue !== out) n.nodeValue = out;
  }
  function doAttrs(el) {
    if (skip(el)) return;
    let rec = attrs.get(el);
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (v == null) continue;
      rec = rec || {};
      const prev = rec[a];
      const src = prev && v === prev.out ? prev.src : v;
      const out = cur === 'es' ? t(src) : src;
      rec[a] = { src, out };
      if (v !== out) el.setAttribute(a, out);
    }
    if (rec) attrs.set(el, rec);
  }
  function walk(node) {
    if (!node) return;
    if (node.nodeType === 3) return doText(node);
    if (node.nodeType !== 1 && node.nodeType !== 9 && node.nodeType !== 11) return;
    if (node.nodeType === 1) doAttrs(node);
    const doc = node.ownerDocument || node;
    const w = doc.createTreeWalker(node, 5 /* elements + text */);
    for (let n = w.nextNode(); n; n = w.nextNode()) n.nodeType === 3 ? doText(n) : doAttrs(n);
  }
  function apply(el) {
    busy = true;
    try { walk(el || scope); } finally { busy = false; }
    if (obs) obs.takeRecords();
  }
  function start(el) {
    scope = el || (root.document && root.document.body);
    if (!scope) return;
    setDocLang();
    apply(scope);
    if (obs || typeof root.MutationObserver !== 'function') return;
    obs = new root.MutationObserver(recs => {
      if (busy) return;
      busy = true;
      try {
        for (const r of recs) {
          if (r.type === 'characterData') doText(r.target);
          else if (r.type === 'attributes') doAttrs(r.target);
          else r.addedNodes.forEach(walk);
        }
      } finally { busy = false; obs.takeRecords(); }
    });
    obs.observe(scope, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }
  function setDocLang() {
    const d = root.document;
    if (d && d.documentElement) d.documentElement.lang = cur;
    const b = d && d.getElementById('langBtn');
    if (b) {
      b.textContent = cur === 'es' ? 'English' : 'Español';
      b.setAttribute('lang', cur === 'es' ? 'en' : 'es');
      b.setAttribute('aria-label', cur === 'es' ? 'Switch to English' : 'Cambiar a español');
    }
    if (d && d.title) {
      const tt = d.__gcmTitle || (d.__gcmTitle = d.title);
      d.title = cur === 'es' ? t(tt) : tt;
    }
  }
  function set(l) {
    cur = l === 'es' ? 'es' : 'en';
    try { root.localStorage.setItem(KEY, cur); } catch (_) {}
    for (const n of [...texts.keys()]) if (!n.isConnected) texts.delete(n);
    for (const n of [...attrs.keys()]) if (!n.isConnected) attrs.delete(n);
    busy = true;
    try {
      setDocLang();
      if (scope) walk(scope);
    } finally { busy = false; if (obs) obs.takeRecords(); }
    try { root.dispatchEvent(new root.CustomEvent('gcm-lang', { detail: cur })); } catch (_) {}
    return cur;
  }
  return { lang: () => cur, set, t: s => (cur === 'es' ? t(s) : s), es: t, pick, start, apply, DICT, PATTERNS, SPANISH: ES };
});
