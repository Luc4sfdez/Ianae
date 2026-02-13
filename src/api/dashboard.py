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
    <script src="https://d3js.org/d3.v7.min.js"></script>
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
        .graph-link { stroke-opacity: 0.4; }
        .graph-node { cursor: pointer; transition: r 0.2s, stroke-width 0.2s; }
        .graph-label { font-size: 9px; fill: #94a3b8; pointer-events: none; }
        .community-hull { fill-opacity: 0.06; stroke-opacity: 0.3; stroke-width: 1.5; }
        .graph-tab { transition: background-color 0.2s, color 0.2s; }
        .graph-tab.active-concepts { background-color: #065f46; color: #6ee7b7; }
        .graph-tab.active-arch { background-color: #4c1d95; color: #c4b5fd; }
        #graph-tooltip { position: absolute; display: none; background: #1e293b; border: 1px solid #475569;
            border-radius: 6px; padding: 8px 12px; font-size: 11px; color: #e2e8f0;
            pointer-events: none; z-index: 50; max-width: 280px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
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
        <button onclick="vivirAuto()" id="btn-auto"
            class="bg-amber-700 hover:bg-amber-600 text-white text-sm px-4 py-2 rounded font-medium transition-colors">
            &#x221E; Modo Auto
        </button>
        <button onclick="detener()" id="btn-detener"
            class="bg-red-800 hover:bg-red-700 text-white text-sm px-4 py-2 rounded font-medium transition-colors hidden">
            &#x25A0; Detener
        </button>
        <span id="vivir-status" class="text-xs text-gray-500"></span>
    </div>

    <!-- ====== GRAFO INTERACTIVO (Fase 15) ====== -->
    <div class="max-w-7xl mx-auto px-6 pb-4">
        <div class="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
            <!-- Tab switcher -->
            <div class="flex items-center justify-between px-4 py-2 border-b border-gray-800">
                <div class="flex items-center space-x-2">
                    <button onclick="switchGraphView('concepts')" id="tab-concepts"
                        class="graph-tab text-xs font-semibold px-3 py-1.5 rounded active-concepts">
                        Conceptos
                    </button>
                    <button onclick="switchGraphView('arch')" id="tab-arch"
                        class="graph-tab text-xs font-semibold px-3 py-1.5 rounded text-gray-500 bg-gray-800">
                        Arquitectura
                    </button>
                </div>
                <div class="flex items-center space-x-3">
                    <span id="graph-info" class="text-xs text-gray-500"></span>
                    <button onclick="resetGraphZoom()" class="text-xs text-gray-500 hover:text-gray-300 bg-gray-800 px-2 py-1 rounded">Reset</button>
                </div>
            </div>
            <!-- SVG -->
            <svg id="graph-svg" width="100%" height="420" style="background:#0b0f19;display:block;"></svg>
            <!-- Legend -->
            <div id="graph-legend" class="flex flex-wrap items-center gap-3 px-4 py-2 border-t border-gray-800 text-xs text-gray-500"></div>
        </div>
        <!-- Tooltip -->
        <div id="graph-tooltip"></div>
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

            <!-- Conocimiento Externo (Fase 13) -->
            <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
                <h2 class="text-sm font-semibold text-gray-400 mb-3">CONOCIMIENTO EXTERNO</h2>
                <div class="space-y-2">
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-500">Estado</span>
                        <span id="ce-estado" class="text-teal-400 font-semibold">--</span>
                    </div>
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-500">Exploraciones</span>
                        <span id="ce-exploraciones" class="text-gray-300">0</span>
                    </div>
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-500">Absorbidos</span>
                        <span id="ce-absorbidos" class="text-green-400">0</span>
                    </div>
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-500">Rechazados</span>
                        <span id="ce-rechazados" class="text-red-400">0</span>
                    </div>
                    <div class="pt-2 border-t border-gray-800">
                        <div class="text-xs text-gray-500 mb-1">Fuentes</div>
                        <div id="ce-fuentes" class="flex flex-wrap gap-1">
                            <span class="text-xs text-gray-600">--</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Introspeccion (Fase 14) -->
            <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
                <h2 class="text-sm font-semibold text-gray-400 mb-3">INTROSPECCION</h2>
                <div class="space-y-2">
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-500">Modulos</span>
                        <span id="intro-modulos" class="text-violet-400 font-bold">--</span>
                    </div>
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-500">Clases</span>
                        <span id="intro-clases" class="text-violet-300">--</span>
                    </div>
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-500">Metodos</span>
                        <span id="intro-metodos" class="text-violet-300">--</span>
                    </div>
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-500">Lineas de codigo</span>
                        <span id="intro-lineas" class="text-gray-300">--</span>
                    </div>
                    <div class="pt-2 border-t border-gray-800">
                        <div class="text-xs text-gray-500 mb-1">Quien soy</div>
                        <div id="intro-quien" class="text-xs text-violet-200 italic leading-relaxed">--</div>
                    </div>
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
    exploracion_externa:    { color: 'text-teal-400',    bg: 'bg-teal-900/30',    icon: 'W' },
    introspeccion:          { color: 'text-violet-400',  bg: 'bg-violet-900/30',  icon: 'I' },
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
    if (tipo === 'exploracion_externa') return `${data.concepto || '?'} — ${data.absorbidos || 0} absorbidos (${data.fuente || '?'})`;
    if (tipo === 'introspeccion') return `${data.concepto || '?'} — ${data.resultados || 0} hallazgos`;
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
            // Flatten: if flujos is a nested object, show its entries instead
            const flat = {};
            Object.entries(corr).forEach(([k, v]) => {
                if (typeof v === 'object' && v !== null) {
                    Object.entries(v).forEach(([k2, v2]) => { flat[k2] = v2; });
                } else {
                    flat[k] = v;
                }
            });
            corrEl.innerHTML = Object.entries(flat).map(([k,v]) =>
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
let autoMode = false;
let ciclosTotales = 0;

function setBotonesVivir(running) {
    document.getElementById('btn-vivir1').disabled = running;
    document.getElementById('btn-vivir5').disabled = running;
    document.getElementById('btn-auto').disabled = running;
    document.getElementById('btn-vivir1').classList.toggle('opacity-50', running);
    document.getElementById('btn-vivir5').classList.toggle('opacity-50', running);
    document.getElementById('btn-auto').classList.toggle('opacity-50', running);
    document.getElementById('btn-detener').classList.toggle('hidden', !running);
}

async function vivirCiclos(n) {
    abortCtrl = new AbortController();
    setBotonesVivir(true);

    for (let i = 0; i < n; i++) {
        if (abortCtrl.signal.aborted) break;
        document.getElementById('vivir-status').textContent = `Ciclo ${i+1}/${n}...`;
        try {
            await fetch('/api/v1/vida/ciclo', {method: 'POST', signal: abortCtrl.signal});
        } catch(e) {
            if (e.name === 'AbortError') break;
        }
        if (i < n - 1) await new Promise(r => setTimeout(r, 300));
    }
    document.getElementById('vivir-status').textContent = '';
    setBotonesVivir(false);
    abortCtrl = null;
    pollOrganismo();
    pollConsciencia();
    pollDiario();
    pollGraph();
}

async function vivirAuto() {
    autoMode = true;
    abortCtrl = new AbortController();
    ciclosTotales = 0;
    setBotonesVivir(true);

    while (autoMode && !abortCtrl.signal.aborted) {
        ciclosTotales++;
        document.getElementById('vivir-status').textContent = `AUTO: ciclo #${ciclosTotales} corriendo...`;
        try {
            await fetch('/api/v1/vida/ciclo', {method: 'POST', signal: abortCtrl.signal});
        } catch(e) {
            if (e.name === 'AbortError') break;
        }
        document.getElementById('vivir-status').textContent = `AUTO: ${ciclosTotales} ciclos completados`;
        // pausa entre ciclos para dejar respirar al server y ver los eventos
        await new Promise(r => setTimeout(r, 500));
    }
    document.getElementById('vivir-status').textContent = `AUTO detenido tras ${ciclosTotales} ciclos`;
    autoMode = false;
    setBotonesVivir(false);
    abortCtrl = null;
    pollOrganismo();
    pollConsciencia();
    pollDiario();
    pollGraph();
}

function detener() {
    autoMode = false;
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
    const epRaw = mv.episodica || mv.episodicas || 0;
    const semRaw = mv.semantica || mv.semanticas || 0;
    const ep = typeof epRaw === 'object' ? (epRaw.activas || epRaw.total || 0) : epRaw;
    const sem = typeof semRaw === 'object' ? (semRaw.activas || semRaw.total || 0) : semRaw;
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

// ===== CONOCIMIENTO EXTERNO =====
async function pollConocimiento() {
    try {
        const r = await fetch('/api/v1/conocimiento');
        if (!r.ok) return;
        const d = await r.json();
        document.getElementById('ce-estado').textContent = d.habilitado ? 'Activo' : 'Inactivo';
        document.getElementById('ce-estado').className = d.habilitado ? 'text-teal-400 font-semibold' : 'text-gray-500 font-semibold';
        document.getElementById('ce-exploraciones').textContent = d.exploraciones || 0;
        const filtro = d.filtro || {};
        document.getElementById('ce-absorbidos').textContent = filtro.absorbidos_total || 0;
        document.getElementById('ce-rechazados').textContent = filtro.rechazados_total || 0;
        const fuentes = d.fuentes || {};
        const badges = Object.entries(fuentes).map(([name, info]) => {
            const avail = info && info.disponible;
            const cls = avail ? 'bg-teal-900/50 text-teal-300' : 'bg-gray-800 text-gray-600';
            return `<span class="text-xs px-1.5 py-0.5 rounded ${cls}">${name}</span>`;
        }).join('');
        document.getElementById('ce-fuentes').innerHTML = badges || '<span class="text-xs text-gray-600">--</span>';
    } catch(_) {}
}

// ===== INTROSPECCION =====
async function pollIntrospeccion() {
    try {
        const r = await fetch('/api/v1/introspeccion');
        if (!r.ok) return;
        const d = await r.json();
        document.getElementById('intro-modulos').textContent = d.modulos || 0;
        document.getElementById('intro-clases').textContent = d.clases || 0;
        document.getElementById('intro-metodos').textContent = d.metodos || 0;
        document.getElementById('intro-lineas').textContent = d.lineas ? d.lineas.toLocaleString() : '--';
        document.getElementById('intro-quien').textContent = d.quien_soy || '--';
    } catch(_) {}
}

// ===== GRAFO INTERACTIVO (Fase 15) =====
const CATEGORY_COLORS = {
    tecnologias: '#FF6B6B', proyectos: '#4ECDC4', lucas_personal: '#45B7D1',
    conceptos_ianae: '#96CEB4', herramientas: '#FFEAA7', emergentes: '#DDA0DD',
    nlp_extraidos: '#F472B6', autoconocimiento: '#A78BFA', conocimiento_externo: '#2DD4BF',
    default: '#94A3B8'
};
let currentView = 'concepts';
let graphSimulation = null;
let graphData = null;
let patternsData = null;
let archData = null;
let graphZoom = null;

function catColor(cat) { return CATEGORY_COLORS[cat] || CATEGORY_COLORS.default; }

async function fetchGraphData() {
    try {
        const [nr, pr] = await Promise.all([
            fetch('/api/v1/network'), fetch('/api/v1/insights/patrones')
        ]);
        if (nr.ok) graphData = await nr.json();
        if (pr.ok) patternsData = await pr.json();
    } catch(_) {}
}

async function fetchArchData() {
    try {
        const r = await fetch('/api/v1/introspeccion/dependencias');
        if (r.ok) archData = await r.json();
    } catch(_) {}
}

function renderConceptGraph() {
    if (!graphData) return;
    const svg = d3.select('#graph-svg');
    svg.selectAll('*').remove();
    const rect = document.getElementById('graph-svg').getBoundingClientRect();
    const width = rect.width || 900;
    const height = rect.height || 420;

    const g = svg.append('g');

    // Zoom
    graphZoom = d3.zoom().scaleExtent([0.3, 4]).on('zoom', (e) => g.attr('transform', e.transform));
    svg.call(graphZoom);

    // Data
    const nodes = (graphData.conceptos || []).map(c => ({
        id: c.nombre, categoria: c.categoria, activaciones: c.activaciones || 0,
        fuerza: c.fuerza || 1.0, ...c
    }));
    const nodeIds = new Set(nodes.map(n => n.id));
    const links = (graphData.relaciones || []).filter(r => nodeIds.has(r.source) && nodeIds.has(r.target))
        .map(r => ({source: r.source, target: r.target, weight: r.weight || 0.5}));

    // Puentes set
    const puenteIds = new Set();
    if (patternsData && patternsData.puentes) {
        patternsData.puentes.forEach(p => { if (p.concepto) puenteIds.add(p.concepto); });
    }

    // Simulation
    graphSimulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(d => Math.max(40, 120 - d.weight * 80)))
        .force('charge', d3.forceManyBody().strength(-150).distanceMax(300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide().radius(d => nodeRadius(d) + 4));

    // Community hulls
    if (patternsData && patternsData.comunidades) {
        const hullColors = ['#4ECDC4', '#FF6B6B', '#FFEAA7', '#DDA0DD', '#45B7D1', '#96CEB4', '#F472B6', '#A78BFA'];
        const hullGroup = g.append('g').attr('class', 'hulls');

        graphSimulation.on('tick.hulls', () => {
            hullGroup.selectAll('path').remove();
            patternsData.comunidades.forEach((comunidad, ci) => {
                if (comunidad.length < 3) return;
                const points = [];
                comunidad.forEach(name => {
                    const node = nodes.find(n => n.id === name);
                    if (node && node.x != null) points.push([node.x, node.y]);
                });
                if (points.length < 3) return;
                const hull = d3.polygonHull(points);
                if (!hull) return;
                hullGroup.append('path')
                    .attr('d', 'M' + hull.map(p => p.join(',')).join('L') + 'Z')
                    .attr('class', 'community-hull')
                    .attr('fill', hullColors[ci % hullColors.length])
                    .attr('stroke', hullColors[ci % hullColors.length]);
            });
        });
    }

    // Links
    const link = g.append('g').selectAll('line').data(links).join('line')
        .attr('class', 'graph-link')
        .attr('stroke', '#475569')
        .attr('stroke-width', d => Math.max(0.5, d.weight * 4))
        .attr('stroke-opacity', d => 0.2 + d.weight * 0.5);

    // Nodes
    const node = g.append('g').selectAll('circle').data(nodes).join('circle')
        .attr('class', 'graph-node')
        .attr('r', d => nodeRadius(d))
        .attr('fill', d => catColor(d.categoria))
        .attr('stroke', d => puenteIds.has(d.id) ? '#ffffff' : 'none')
        .attr('stroke-width', d => puenteIds.has(d.id) ? 2 : 0)
        .call(d3.drag()
            .on('start', (e, d) => { if (!e.active) graphSimulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
            .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
            .on('end', (e, d) => { if (!e.active) graphSimulation.alphaTarget(0); d.fx = null; d.fy = null; })
        );

    // Labels
    const label = g.append('g').selectAll('text').data(nodes.filter(n => n.activaciones > 0 || n.fuerza > 0.8))
        .join('text')
        .attr('class', 'graph-label')
        .attr('text-anchor', 'middle')
        .attr('dy', d => -nodeRadius(d) - 3)
        .text(d => d.id.length > 14 ? d.id.slice(0, 12) + '..' : d.id);

    // Tick
    graphSimulation.on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('cx', d => d.x).attr('cy', d => d.y);
        label.attr('x', d => d.x).attr('y', d => d.y);
    });

    // Tooltip + highlight
    const tooltip = document.getElementById('graph-tooltip');
    node.on('click', (e, d) => {
        e.stopPropagation();
        const neighbors = new Set();
        links.forEach(l => {
            const sid = typeof l.source === 'object' ? l.source.id : l.source;
            const tid = typeof l.target === 'object' ? l.target.id : l.target;
            if (sid === d.id) neighbors.add(tid);
            if (tid === d.id) neighbors.add(sid);
        });
        neighbors.add(d.id);
        node.attr('opacity', n => neighbors.has(n.id) ? 1 : 0.15);
        link.attr('opacity', l => {
            const sid = typeof l.source === 'object' ? l.source.id : l.source;
            const tid = typeof l.target === 'object' ? l.target.id : l.target;
            return (sid === d.id || tid === d.id) ? 1 : 0.05;
        });
        label.attr('opacity', n => neighbors.has(n.id) ? 1 : 0.1);
        tooltip.style.display = 'block';
        tooltip.style.left = (e.pageX + 12) + 'px';
        tooltip.style.top = (e.pageY - 10) + 'px';
        tooltip.innerHTML = `<div class="font-bold mb-1" style="color:${catColor(d.categoria)}">${escapeHtml(d.id)}</div>
            <div>Categoria: ${d.categoria}</div>
            <div>Activaciones: ${d.activaciones}</div>
            <div>Fuerza: ${d.fuerza.toFixed(2)}</div>
            ${puenteIds.has(d.id) ? '<div class="mt-1 text-amber-400">Puente entre comunidades</div>' : ''}`;
    });
    svg.on('click', () => {
        node.attr('opacity', 1); link.attr('opacity', 1); label.attr('opacity', 1);
        tooltip.style.display = 'none';
    });

    updateGraphInfo('concepts', nodes.length, links.length, patternsData ? (patternsData.comunidades || []).length : 0);
    updateLegend('concepts');
}

function nodeRadius(d) {
    return 5 + Math.min(d.activaciones || 0, 30) * 0.5 + (d.fuerza || 0) * 3;
}

function renderArchGraph() {
    if (!archData) return;
    const svg = d3.select('#graph-svg');
    svg.selectAll('*').remove();
    const rect = document.getElementById('graph-svg').getBoundingClientRect();
    const width = rect.width || 900;
    const height = rect.height || 420;

    // Defs for arrowheads
    svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#64748b');

    const g = svg.append('g');
    graphZoom = d3.zoom().scaleExtent([0.3, 4]).on('zoom', (e) => g.attr('transform', e.transform));
    svg.call(graphZoom);

    const nodes = (archData.nodos || []).map(n => ({...n}));
    const nodeIds = new Set(nodes.map(n => n.id));
    const links = (archData.aristas || []).filter(a => nodeIds.has(a.source) && nodeIds.has(a.target))
        .map(a => ({source: a.source, target: a.target}));

    graphSimulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-200).distanceMax(400))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide().radius(d => archRadius(d) + 8));

    const link = g.append('g').selectAll('line').data(links).join('line')
        .attr('class', 'graph-link')
        .attr('stroke', '#475569')
        .attr('stroke-width', 1.5)
        .attr('marker-end', 'url(#arrowhead)');

    const node = g.append('g').selectAll('circle').data(nodes).join('circle')
        .attr('class', 'graph-node')
        .attr('r', d => archRadius(d))
        .attr('fill', d => d.es_core ? '#A78BFA' : '#64748B')
        .attr('stroke', '#1e293b').attr('stroke-width', 1.5)
        .call(d3.drag()
            .on('start', (e, d) => { if (!e.active) graphSimulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
            .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
            .on('end', (e, d) => { if (!e.active) graphSimulation.alphaTarget(0); d.fx = null; d.fy = null; })
        );

    const label = g.append('g').selectAll('text').data(nodes).join('text')
        .attr('class', 'graph-label')
        .attr('text-anchor', 'middle')
        .attr('dy', d => -archRadius(d) - 4)
        .text(d => d.id);

    graphSimulation.on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('cx', d => d.x).attr('cy', d => d.y);
        label.attr('x', d => d.x).attr('y', d => d.y);
    });

    const tooltip = document.getElementById('graph-tooltip');
    node.on('click', (e, d) => {
        e.stopPropagation();
        tooltip.style.display = 'block';
        tooltip.style.left = (e.pageX + 12) + 'px';
        tooltip.style.top = (e.pageY - 10) + 'px';
        tooltip.innerHTML = `<div class="font-bold mb-1" style="color:${d.es_core ? '#A78BFA' : '#94A3B8'}">${escapeHtml(d.id)}</div>
            <div>Lineas: ${d.lineas}</div>
            <div>Clases: ${d.clases} &middot; Funciones: ${d.funciones}</div>
            ${d.docstring ? '<div class="mt-1 text-gray-400 italic">' + escapeHtml(d.docstring.slice(0, 120)) + '</div>' : ''}`;
    });
    svg.on('click', () => { tooltip.style.display = 'none'; });

    updateGraphInfo('arch', nodes.length, links.length, 0);
    updateLegend('arch');
}

function archRadius(d) { return 6 + Math.min((d.lineas || 0) / 100, 12); }

function switchGraphView(view) {
    currentView = view;
    const tabC = document.getElementById('tab-concepts');
    const tabA = document.getElementById('tab-arch');
    if (view === 'concepts') {
        tabC.className = 'graph-tab text-xs font-semibold px-3 py-1.5 rounded active-concepts';
        tabA.className = 'graph-tab text-xs font-semibold px-3 py-1.5 rounded text-gray-500 bg-gray-800';
        renderConceptGraph();
    } else {
        tabA.className = 'graph-tab text-xs font-semibold px-3 py-1.5 rounded active-arch';
        tabC.className = 'graph-tab text-xs font-semibold px-3 py-1.5 rounded text-gray-500 bg-gray-800';
        renderArchGraph();
    }
}

function resetGraphZoom() {
    const svg = d3.select('#graph-svg');
    if (graphZoom) svg.transition().duration(400).call(graphZoom.transform, d3.zoomIdentity);
}

function updateGraphInfo(view, nodos, aristas, comunidades) {
    const el = document.getElementById('graph-info');
    if (view === 'concepts') {
        el.textContent = nodos + ' nodos \\u00b7 ' + aristas + ' aristas' + (comunidades ? ' \\u00b7 ' + comunidades + ' comunidades' : '');
    } else {
        el.textContent = nodos + ' modulos \\u00b7 ' + aristas + ' dependencias';
    }
}

function updateLegend(view) {
    const el = document.getElementById('graph-legend');
    if (view === 'concepts') {
        const cats = Object.entries(CATEGORY_COLORS).filter(([k]) => k !== 'default');
        el.innerHTML = cats.map(([k, c]) =>
            '<span class="flex items-center gap-1"><span style="background:' + c + ';width:8px;height:8px;border-radius:50%;display:inline-block;"></span>' + k + '</span>'
        ).join('') + '<span class="flex items-center gap-1 ml-2"><span style="width:8px;height:8px;border-radius:50%;display:inline-block;border:2px solid white;"></span>puente</span>';
    } else {
        el.innerHTML = '<span class="flex items-center gap-1"><span style="background:#A78BFA;width:8px;height:8px;border-radius:50%;display:inline-block;"></span>core</span>'
            + '<span class="flex items-center gap-1"><span style="background:#64748B;width:8px;height:8px;border-radius:50%;display:inline-block;"></span>otro</span>'
            + '<span class="flex items-center gap-1 ml-2">\\u2192 importa</span>';
    }
}

async function pollGraph() {
    if (currentView === 'concepts') {
        await fetchGraphData();
        renderConceptGraph();
    } else {
        await fetchArchData();
        renderArchGraph();
    }
}

// ===== INIT =====
connectSSE();
pollOrganismo();
pollConsciencia();
pollDiario();
pollConocimiento();
pollIntrospeccion();
// Init graph data
fetchGraphData().then(() => fetchArchData().then(() => { if (currentView === 'concepts') renderConceptGraph(); else renderArchGraph(); }));
setInterval(pollOrganismo, 3000);
setInterval(pollConsciencia, 5000);
setInterval(pollDiario, 10000);
setInterval(pollConocimiento, 5000);
setInterval(pollIntrospeccion, 10000);
setInterval(pollGraph, 8000);
</script>
</body>
</html>'''
