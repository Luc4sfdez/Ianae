"""
Dashboard en vivo para IANAE — HTML+JS inline servido desde FastAPI.

Muestra ciclos de vida, eventos SSE, consciencia, memoria y diario
en tiempo real. Sin frameworks, solo Tailwind CDN + vanilla JS.
"""


def dashboard_html() -> str:
    """Retorna el HTML completo del dashboard de vida de IANAE."""
    return '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IANAE — Vida en Tiempo Real</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes pulse-glow {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        .pulse-glow { animation: pulse-glow 2s ease-in-out infinite; }
        @keyframes fade-in {
            from { opacity: 0; transform: translateY(-8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .fade-in { animation: fade-in 0.3s ease-out; }
        body { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace; }
        .bar-fill { transition: width 0.6s ease-out; }
        #stream-box::-webkit-scrollbar { width: 6px; }
        #stream-box::-webkit-scrollbar-track { background: #1e293b; }
        #stream-box::-webkit-scrollbar-thumb { background: #475569; border-radius: 3px; }
    </style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen">

    <!-- ====== HEADER ====== -->
    <header class="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
            <div class="flex items-center space-x-4">
                <span id="hdr-pulso" class="text-3xl pulse-glow">&#x1F49A;</span>
                <div>
                    <h1 class="text-xl font-bold text-emerald-400">IANAE <span class="text-gray-500 text-sm font-normal">vida en tiempo real</span></h1>
                    <p class="text-xs text-gray-500">
                        Ciclo <span id="hdr-ciclo" class="text-gray-300">0</span>
                        &middot; Gen <span id="hdr-gen" class="text-gray-300">0</span>
                        &middot; Edad <span id="hdr-edad" class="text-gray-300">0s</span>
                    </p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <div id="sse-indicator" class="flex items-center space-x-1">
                    <div id="sse-dot" class="w-2 h-2 bg-red-500 rounded-full"></div>
                    <span id="sse-label" class="text-xs text-gray-500">SSE: desconectado</span>
                </div>
            </div>
        </div>
    </header>

    <!-- ====== CONTROLES ====== -->
    <div class="max-w-7xl mx-auto px-6 py-3 flex items-center space-x-3">
        <button onclick="vivirCiclos(1)" id="btn-vivir1"
            class="bg-emerald-700 hover:bg-emerald-600 text-white text-sm px-4 py-2 rounded font-medium transition-colors">
            &#x25B6; Vivir 1 ciclo
        </button>
        <button onclick="vivirCiclos(5)" id="btn-vivir5"
            class="bg-emerald-800 hover:bg-emerald-700 text-white text-sm px-4 py-2 rounded font-medium transition-colors">
            &#x25B6;&#x25B6; Vivir 5 ciclos
        </button>
        <button onclick="detener()" id="btn-detener"
            class="bg-red-800 hover:bg-red-700 text-white text-sm px-4 py-2 rounded font-medium transition-colors hidden">
            &#x25A0; Detener
        </button>
        <span id="vivir-status" class="text-xs text-gray-500"></span>
    </div>

    <!-- ====== GRID PRINCIPAL ====== -->
    <div class="max-w-7xl mx-auto px-6 pb-8 grid grid-cols-1 lg:grid-cols-3 gap-4">

        <!-- COL 1: Stream en Vivo -->
        <div class="lg:col-span-2 space-y-4">
            <!-- Stream -->
            <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
                <div class="flex items-center justify-between mb-3">
                    <h2 class="text-sm font-semibold text-gray-400">STREAM EN VIVO</h2>
                    <span id="stream-count" class="text-xs text-gray-600">0 eventos</span>
                </div>
                <div id="stream-box" class="space-y-1 max-h-96 overflow-y-auto text-xs font-mono"></div>
                <div id="stream-empty" class="text-xs text-gray-600 text-center py-6">
                    Esperando eventos... Pulsa &quot;Vivir&quot; para empezar
                </div>
            </div>

            <!-- Organismo Cards -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div class="bg-gray-900 rounded-lg border border-gray-800 p-3">
                    <div class="text-xs text-gray-500 mb-1">Conceptos</div>
                    <div id="card-conceptos" class="text-2xl font-bold text-blue-400">--</div>
                </div>
                <div class="bg-gray-900 rounded-lg border border-gray-800 p-3">
                    <div class="text-xs text-gray-500 mb-1">Relaciones</div>
                    <div id="card-relaciones" class="text-2xl font-bold text-green-400">--</div>
                </div>
                <div class="bg-gray-900 rounded-lg border border-gray-800 p-3">
                    <div class="text-xs text-gray-500 mb-1">Superficie</div>
                    <div id="card-superficie" class="text-2xl font-bold text-purple-400">--</div>
                </div>
                <div class="bg-gray-900 rounded-lg border border-gray-800 p-3">
                    <div class="text-xs text-gray-500 mb-1">Generacion</div>
                    <div id="card-generacion" class="text-2xl font-bold text-yellow-400">--</div>
                </div>
            </div>

            <!-- Diario -->
            <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
                <h2 class="text-sm font-semibold text-gray-400 mb-3">DIARIO DE VIDA</h2>
                <div id="diario-box" class="space-y-2">
                    <div class="text-xs text-gray-600 text-center py-4">Cargando diario...</div>
                </div>
            </div>
        </div>

        <!-- COL 2: Consciencia + Memoria -->
        <div class="space-y-4">
            <!-- Consciencia -->
            <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
                <h2 class="text-sm font-semibold text-gray-400 mb-3">CONSCIENCIA</h2>
                <div class="space-y-3">
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-gray-500">Energia</span>
                            <span id="con-energia" class="text-emerald-400">--</span>
                        </div>
                        <div class="w-full bg-gray-800 rounded-full h-2">
                            <div id="con-energia-bar" class="bg-emerald-500 h-2 rounded-full bar-fill" style="width:0%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-gray-500">Coherencia</span>
                            <span id="con-coherencia" class="text-blue-400">--</span>
                        </div>
                        <div class="w-full bg-gray-800 rounded-full h-2">
                            <div id="con-coherencia-bar" class="bg-blue-500 h-2 rounded-full bar-fill" style="width:0%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-gray-500">Curiosidad</span>
                            <span id="con-curiosidad" class="text-yellow-400">--</span>
                        </div>
                        <div class="w-full bg-gray-800 rounded-full h-2">
                            <div id="con-curiosidad-bar" class="bg-yellow-500 h-2 rounded-full bar-fill" style="width:0%"></div>
                        </div>
                    </div>
                    <div class="pt-2 border-t border-gray-800">
                        <div class="text-xs text-gray-500 mb-1">Corrientes</div>
                        <div id="con-corrientes" class="text-xs text-gray-400">--</div>
                    </div>
                    <div class="pt-2 border-t border-gray-800">
                        <div class="text-xs text-gray-500 mb-1">Narrativa</div>
                        <div id="con-narrativa" class="text-xs text-gray-300 italic leading-relaxed">--</div>
                    </div>
                </div>
            </div>

            <!-- Memoria Viva -->
            <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
                <h2 class="text-sm font-semibold text-gray-400 mb-3">MEMORIA VIVA</h2>
                <div class="space-y-3">
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-gray-500">Episodica</span>
                            <span id="mem-episodica" class="text-pink-400">0</span>
                        </div>
                        <div class="w-full bg-gray-800 rounded-full h-2">
                            <div id="mem-episodica-bar" class="bg-pink-500 h-2 rounded-full bar-fill" style="width:0%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-gray-500">Semantica</span>
                            <span id="mem-semantica" class="text-cyan-400">0</span>
                        </div>
                        <div class="w-full bg-gray-800 rounded-full h-2">
                            <div id="mem-semantica-bar" class="bg-cyan-500 h-2 rounded-full bar-fill" style="width:0%"></div>
                        </div>
                    </div>
                    <div class="pt-2 border-t border-gray-800">
                        <div class="flex justify-between text-xs">
                            <span class="text-gray-500">Total activas</span>
                            <span id="mem-total" class="text-gray-300 font-bold">0</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sesgos -->
            <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
                <h2 class="text-sm font-semibold text-gray-400 mb-3">SESGOS DETECTADOS</h2>
                <div id="sesgos-box" class="space-y-1">
                    <div class="text-xs text-gray-600">--</div>
                </div>
            </div>
        </div>
    </div>

<script>
// ===== CONFIG =====
const EVENT_COLORS = {
    ciclo_inicio:           { color: 'text-blue-400',    bg: 'bg-blue-900/30',    icon: '>>' },
    curiosidad_elegida:     { color: 'text-yellow-400',  bg: 'bg-yellow-900/30',  icon: '?' },
    exploracion_completa:   { color: 'text-green-400',   bg: 'bg-green-900/30',   icon: '*' },
    reflexion:              { color: 'text-purple-400',  bg: 'bg-purple-900/30',  icon: '~' },
    integracion:            { color: 'text-cyan-400',    bg: 'bg-cyan-900/30',    icon: '+' },
    simbolico_arbol:        { color: 'text-pink-400',    bg: 'bg-pink-900/30',    icon: '#' },
    sueno:                  { color: 'text-indigo-400',  bg: 'bg-indigo-900/30',  icon: 'z' },
    evolucion:              { color: 'text-orange-400',  bg: 'bg-orange-900/30',  icon: '^' },
    memoria_consolidacion:  { color: 'text-gray-400',    bg: 'bg-gray-800/50',    icon: 'm' },
};
const MAX_EVENTS = 100;
let eventCount = 0;
let abortCtrl = null;

// ===== SSE =====
let es = null;
function connectSSE() {
    if (es) es.close();
    es = new EventSource('/api/v1/stream?desde_id=0');

    es.onopen = () => {
        document.getElementById('sse-dot').className = 'w-2 h-2 bg-green-500 rounded-full pulse-glow';
        document.getElementById('sse-label').textContent = 'SSE: conectado';
    };
    es.onerror = () => {
        document.getElementById('sse-dot').className = 'w-2 h-2 bg-red-500 rounded-full';
        document.getElementById('sse-label').textContent = 'SSE: reconectando...';
    };

    const allTypes = Object.keys(EVENT_COLORS);
    allTypes.forEach(tipo => {
        es.addEventListener(tipo, (e) => {
            try { addEvent(tipo, JSON.parse(e.data)); } catch(_) { addEvent(tipo, {raw: e.data}); }
        });
    });
    // catch-all for unknown types
    es.onmessage = (e) => {
        try { addEvent('info', JSON.parse(e.data)); } catch(_) { addEvent('info', {raw: e.data}); }
    };
}

function addEvent(tipo, data) {
    const box = document.getElementById('stream-box');
    const empty = document.getElementById('stream-empty');
    if (empty) empty.style.display = 'none';

    const cfg = EVENT_COLORS[tipo] || { color: 'text-gray-400', bg: 'bg-gray-800/50', icon: '·' };
    const time = new Date().toLocaleTimeString('es', {hour12: false});
    const summary = buildSummary(tipo, data);

    const div = document.createElement('div');
    div.className = `flex items-start space-x-2 px-2 py-1 rounded ${cfg.bg} fade-in`;
    div.innerHTML = `
        <span class="${cfg.color} font-bold w-5 text-center flex-shrink-0">${cfg.icon}</span>
        <span class="text-gray-600 flex-shrink-0">${time}</span>
        <span class="${cfg.color} font-semibold flex-shrink-0">${tipo}</span>
        <span class="text-gray-400 truncate">${summary}</span>
    `;
    box.prepend(div);
    eventCount++;

    // trim old events
    while (box.children.length > MAX_EVENTS) {
        box.removeChild(box.lastChild);
    }
    document.getElementById('stream-count').textContent = eventCount + ' eventos';
}

function buildSummary(tipo, data) {
    if (!data) return '';
    if (tipo === 'ciclo_inicio') return `ciclo #${data.ciclo || '?'}`;
    if (tipo === 'curiosidad_elegida') return data.concepto || data.pregunta || JSON.stringify(data).slice(0, 60);
    if (tipo === 'exploracion_completa') return `descubrimientos: ${data.descubrimientos || '?'}`;
    if (tipo === 'reflexion') return data.coherencia != null ? `coherencia: ${data.coherencia}` : JSON.stringify(data).slice(0, 60);
    if (tipo === 'evolucion') return `gen ${data.generacion || '?'}`;
    if (tipo === 'sueno') return data.veredicto || '';
    if (tipo === 'memoria_consolidacion') return `memorias: ${data.consolidadas || data.total || '?'}`;
    // default
    const s = JSON.stringify(data);
    return s.length > 80 ? s.slice(0, 80) + '...' : s;
}

// ===== POLLING =====
async function pollOrganismo() {
    try {
        const r = await fetch('/api/v1/organismo');
        if (!r.ok) return;
        const d = await r.json();
        document.getElementById('hdr-ciclo').textContent = d.ciclo_actual || 0;
        document.getElementById('hdr-gen').textContent = d.generacion || 0;
        document.getElementById('hdr-edad').textContent = formatEdad(d.edad_s || 0);

        document.getElementById('card-conceptos').textContent = d.conceptos || 0;
        document.getElementById('card-relaciones').textContent = d.relaciones || 0;
        document.getElementById('card-superficie').textContent = typeof d.superficie === 'number' ? d.superficie.toFixed(2) : '--';
        document.getElementById('card-generacion').textContent = d.generacion || 0;

        // Pulso emoji
        const pulso = d.pulso || {};
        const energia = pulso.energia || pulso.vitalidad || 0;
        const emoji = energia > 0.7 ? '&#x1F49A;' : energia > 0.3 ? '&#x1F49B;' : '&#x1F494;';
        document.getElementById('hdr-pulso').innerHTML = emoji;

        // Memoria viva
        updateMemoria(d.memoria_viva);
    } catch(_) {}
}

async function pollConsciencia() {
    try {
        const r = await fetch('/api/v1/consciencia');
        if (!r.ok) return;
        const d = await r.json();

        const pulso = d.pulso || {};
        const energia = pulso.energia || pulso.vitalidad || 0;
        const coherencia = pulso.coherencia || 0;
        const curiosidad = pulso.curiosidad || 0;

        setBar('con-energia', energia);
        setBar('con-coherencia', coherencia);
        setBar('con-curiosidad', curiosidad);

        // corrientes
        const corr = d.corrientes || {};
        const corrEl = document.getElementById('con-corrientes');
        if (Object.keys(corr).length > 0) {
            corrEl.innerHTML = Object.entries(corr).map(([k,v]) =>
                `<span class="inline-block bg-gray-800 rounded px-1 mr-1 mb-1">${k}: ${typeof v === 'number' ? v.toFixed(2) : v}</span>`
            ).join('');
        }

        // narrativa
        document.getElementById('con-narrativa').textContent = d.narrativa || '--';

        // sesgos
        const sesgosBox = document.getElementById('sesgos-box');
        const sesgos = d.sesgos || [];
        if (sesgos.length === 0) {
            sesgosBox.innerHTML = '<div class="text-xs text-gray-600">Ninguno detectado</div>';
        } else {
            sesgosBox.innerHTML = sesgos.map(s =>
                `<div class="text-xs text-amber-400/80">&bull; ${s.tipo || s.nombre || JSON.stringify(s)}</div>`
            ).join('');
        }
    } catch(_) {}
}

async function pollDiario() {
    try {
        const r = await fetch('/api/v1/vida/diario?ultimos=5');
        if (!r.ok) return;
        const d = await r.json();
        const box = document.getElementById('diario-box');
        const entradas = d.entradas || [];
        if (entradas.length === 0) {
            box.innerHTML = '<div class="text-xs text-gray-600 text-center py-4">Sin entradas aun</div>';
            return;
        }
        box.innerHTML = entradas.map(e => {
            const veredicto = e.veredicto || e.tipo || '';
            const score = e.score != null ? ` (${(e.score * 100).toFixed(0)}%)` : '';
            const vcolor = veredicto === 'positivo' ? 'text-green-400' :
                           veredicto === 'negativo' ? 'text-red-400' : 'text-gray-400';
            const texto = e.texto || e.contenido || e.resumen || JSON.stringify(e).slice(0, 120);
            return `<div class="bg-gray-800/50 rounded p-2 text-xs">
                <div class="flex justify-between mb-1">
                    <span class="${vcolor} font-semibold">${veredicto}${score}</span>
                    <span class="text-gray-600">${e.ciclo != null ? 'ciclo ' + e.ciclo : ''}</span>
                </div>
                <div class="text-gray-400 leading-relaxed">${escapeHtml(texto)}</div>
            </div>`;
        }).join('');
    } catch(_) {}
}

// ===== VIVIR =====
async function vivirCiclos(n) {
    abortCtrl = new AbortController();
    document.getElementById('btn-vivir1').disabled = true;
    document.getElementById('btn-vivir5').disabled = true;
    document.getElementById('btn-detener').classList.remove('hidden');

    for (let i = 0; i < n; i++) {
        if (abortCtrl.signal.aborted) break;
        document.getElementById('vivir-status').textContent = `Ciclo ${i+1}/${n}...`;
        try {
            await fetch('/api/v1/vida/ciclo', {method: 'POST', signal: abortCtrl.signal});
        } catch(e) {
            if (e.name === 'AbortError') break;
        }
        // small delay between cycles
        if (i < n - 1) await new Promise(r => setTimeout(r, 300));
    }
    document.getElementById('vivir-status').textContent = '';
    document.getElementById('btn-vivir1').disabled = false;
    document.getElementById('btn-vivir5').disabled = false;
    document.getElementById('btn-detener').classList.add('hidden');
    abortCtrl = null;
    // immediate refresh
    pollOrganismo();
    pollConsciencia();
    pollDiario();
}

function detener() {
    if (abortCtrl) abortCtrl.abort();
}

// ===== HELPERS =====
function setBar(prefix, value) {
    const pct = Math.max(0, Math.min(100, value * 100));
    document.getElementById(prefix).textContent = pct.toFixed(0) + '%';
    document.getElementById(prefix + '-bar').style.width = pct + '%';
}

function updateMemoria(mv) {
    if (!mv) return;
    const ep = mv.episodica || mv.episodicas || 0;
    const sem = mv.semantica || mv.semanticas || 0;
    const total = mv.total_activas || (ep + sem);
    const maxMem = Math.max(total, 50); // scale bar to at least 50

    document.getElementById('mem-episodica').textContent = ep;
    document.getElementById('mem-episodica-bar').style.width = (ep / maxMem * 100) + '%';
    document.getElementById('mem-semantica').textContent = sem;
    document.getElementById('mem-semantica-bar').style.width = (sem / maxMem * 100) + '%';
    document.getElementById('mem-total').textContent = total;
}

function formatEdad(s) {
    if (s < 60) return s.toFixed(0) + 's';
    if (s < 3600) return (s / 60).toFixed(1) + 'm';
    return (s / 3600).toFixed(1) + 'h';
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

// ===== INIT =====
connectSSE();
pollOrganismo();
pollConsciencia();
pollDiario();
setInterval(pollOrganismo, 3000);
setInterval(pollConsciencia, 5000);
setInterval(pollDiario, 10000);
</script>
</body>
</html>'''
