// IANAE Dashboard v2.0 - D3.js + WebSocket + Experimentos
// Orden #24: Dashboard Avanzado

const API_BASE = "";
const UPDATE_INTERVAL = 10000;

let updateTimer = null;
let lastDocuments = [];
let ws = null;
let wsReconnectTimer = null;
let networkSimulation = null;
let currentNetworkData = null;

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    console.log('IANAE Dashboard v2.0 iniciado');
    startPolling();
    connectWebSocket();
    setupSliders();
    loadNetwork();
    loadAvailableConcepts();
    loadSnapshots();

    document.getElementById('filter-category').addEventListener('change', updateDocuments);
    document.getElementById('filter-worker').addEventListener('change', updateDocuments);
});

// ==================== Tab Navigation ====================

function switchTab(tabName) {
    const tabs = ['orchestra', 'network', 'ingestion', 'experiments'];
    tabs.forEach(t => {
        document.getElementById(`panel-${t}`).classList.toggle('hidden', t !== tabName);
        document.getElementById(`tab-${t}`).className = `pb-2 text-sm font-medium ${t === tabName ? 'tab-active' : 'tab-inactive'}`;
    });
    if (tabName === 'network') loadNetwork();
    if (tabName === 'experiments') loadSnapshots();
}

// ==================== Slider Setup ====================

function setupSliders() {
    const depthSlider = document.getElementById('ingest-depth');
    const tempSlider = document.getElementById('ingest-temp');
    const umbralSlider = document.getElementById('exp-umbral');

    if (depthSlider) {
        depthSlider.addEventListener('input', () => {
            document.getElementById('ingest-depth-val').textContent = depthSlider.value;
        });
    }
    if (tempSlider) {
        tempSlider.addEventListener('input', () => {
            document.getElementById('ingest-temp-val').textContent = (parseInt(tempSlider.value) / 100).toFixed(2);
        });
    }
    if (umbralSlider) {
        umbralSlider.addEventListener('input', () => {
            document.getElementById('exp-umbral-val').textContent = (parseInt(umbralSlider.value) / 100).toFixed(2);
        });
    }
}

// ==================== WebSocket ====================

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket conectado');
            document.getElementById('ws-dot').className = 'w-2 h-2 bg-green-500 rounded-full status-pulse';
            document.getElementById('ws-status').textContent = 'WebSocket: conectado';
            document.getElementById('ws-status').className = 'text-xs ws-connected';
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleWSMessage(msg);
            } catch (e) {
                console.error('Error parsing WS message:', e);
            }
        };

        ws.onclose = () => {
            console.log('WebSocket desconectado');
            document.getElementById('ws-dot').className = 'w-2 h-2 bg-red-500 rounded-full';
            document.getElementById('ws-status').textContent = 'WebSocket: desconectado';
            document.getElementById('ws-status').className = 'text-xs ws-disconnected';
            // Reconectar
            if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
            wsReconnectTimer = setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    } catch (e) {
        console.error('WebSocket connection failed:', e);
        if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
        wsReconnectTimer = setTimeout(connectWebSocket, 5000);
    }
}

function handleWSMessage(msg) {
    switch (msg.type) {
        case 'ianae_status':
            updateIANAEMetrics(msg.data);
            break;
        case 'network_update':
            renderD3Network(msg.data, 'network-svg');
            break;
        case 'activation':
            if (msg.data.network) {
                renderD3Network(msg.data.network, 'network-svg');
            }
            break;
        case 'experiment_result':
            if (msg.data.network) {
                renderD3Network(msg.data.network, 'exp-network-svg');
            }
            if (msg.data.metricas) {
                updateIANAEMetricsFromObj(msg.data.metricas);
            }
            break;
        case 'snapshot_loaded':
            renderD3Network(msg.data, 'network-svg');
            break;
        case 'pong':
            break;
        default:
            console.log('WS message:', msg);
    }
}

// ==================== D3.js Network Visualization ====================

async function loadNetwork() {
    try {
        const response = await fetch(`${API_BASE}/api/ianae/network`);
        const data = await response.json();
        currentNetworkData = data;
        renderD3Network(data, 'network-svg');
        updateIANAEMetrics(data);
        updateCategoryCounts(data.categorias);
    } catch (error) {
        console.error('Error loading network:', error);
    }
}

function renderD3Network(data, svgId) {
    const svgElement = document.getElementById(svgId);
    if (!svgElement) return;

    const svg = d3.select(`#${svgId}`);
    svg.selectAll('*').remove();

    const rect = svgElement.getBoundingClientRect();
    const width = rect.width || 800;
    const height = rect.height || 500;

    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const g = svg.append('g');

    // Zoom
    const zoom = d3.zoom()
        .scaleExtent([0.3, 4])
        .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);
    svg.__zoomBehavior = zoom;

    const nodes = data.nodes.map(d => ({...d}));
    const links = data.links.map(d => ({...d}));

    // Simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(d => 80 / (d.weight || 0.5)))
        .force('charge', d3.forceManyBody().strength(-120))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => d.size + 5));

    if (svgId === 'network-svg') networkSimulation = simulation;

    // Links
    const link = g.append('g')
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('class', 'link')
        .attr('stroke', '#4b5563')
        .attr('stroke-width', d => Math.max(1, d.weight * 3))
        .attr('stroke-opacity', d => 0.2 + d.weight * 0.5);

    // Nodes
    const node = g.append('g')
        .selectAll('circle')
        .data(nodes)
        .join('circle')
        .attr('r', d => d.size || 6)
        .attr('fill', d => d.color || '#888')
        .attr('stroke', d => d.activacion_actual > 0.1 ? '#fff' : '#1e293b')
        .attr('stroke-width', d => d.activacion_actual > 0.1 ? 2 : 1)
        .attr('opacity', d => d.activacion_actual > 0 ? 1 : 0.8)
        .style('cursor', 'pointer')
        .call(d3.drag()
            .on('start', (event, d) => {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x; d.fy = d.y;
            })
            .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
            .on('end', (event, d) => {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null; d.fy = null;
            })
        );

    // Labels
    const label = g.append('g')
        .selectAll('text')
        .data(nodes)
        .join('text')
        .attr('class', 'node-label')
        .text(d => d.id.replace(/_/g, ' '))
        .attr('font-size', d => d.activacion_actual > 0.1 ? '11px' : '9px')
        .attr('font-weight', d => d.activacion_actual > 0.1 ? 'bold' : 'normal')
        .attr('fill', d => d.activacion_actual > 0.1 ? '#fbbf24' : '#94a3b8')
        .attr('text-anchor', 'middle')
        .attr('dy', d => -(d.size || 6) - 4);

    // Click handler
    node.on('click', (event, d) => {
        showNodeDetail(d);
        // Highlight connections
        const connectedIds = new Set();
        links.forEach(l => {
            const sid = typeof l.source === 'object' ? l.source.id : l.source;
            const tid = typeof l.target === 'object' ? l.target.id : l.target;
            if (sid === d.id) connectedIds.add(tid);
            if (tid === d.id) connectedIds.add(sid);
        });
        connectedIds.add(d.id);

        node.attr('opacity', n => connectedIds.has(n.id) ? 1 : 0.2);
        link.attr('stroke-opacity', l => {
            const sid = typeof l.source === 'object' ? l.source.id : l.source;
            const tid = typeof l.target === 'object' ? l.target.id : l.target;
            return (sid === d.id || tid === d.id) ? 0.8 : 0.05;
        });
        label.attr('opacity', n => connectedIds.has(n.id) ? 1 : 0.1);
    });

    // Double click to reset highlight
    svg.on('dblclick.reset', () => {
        node.attr('opacity', d => d.activacion_actual > 0 ? 1 : 0.8);
        link.attr('stroke-opacity', d => 0.2 + d.weight * 0.5);
        label.attr('opacity', 1);
    });

    // Tick
    simulation.on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('cx', d => d.x).attr('cy', d => d.y);
        label.attr('x', d => d.x).attr('y', d => d.y - (d.size || 6) - 4);
    });
}

function resetNetworkZoom() {
    const svg = d3.select('#network-svg');
    if (svg.__zoomBehavior) {
        svg.transition().duration(500).call(svg.__zoomBehavior.transform, d3.zoomIdentity);
    }
}

function showNodeDetail(d) {
    const detail = document.getElementById('node-detail');
    if (!detail) return;
    detail.innerHTML = `
        <div class="space-y-1">
            <div class="font-semibold text-sm" style="color:${d.color}">${d.id.replace(/_/g, ' ')}</div>
            <div>Categoria: <span class="text-gray-300">${d.category}</span></div>
            <div>Activaciones: <span class="text-gray-300">${d.activaciones}</span></div>
            <div>Fuerza: <span class="text-gray-300">${d.fuerza}</span></div>
            <div>Conexiones: <span class="text-gray-300">${d.conexiones}</span></div>
            ${d.activacion_actual > 0 ? `<div>Activacion actual: <span class="text-yellow-400 font-bold">${d.activacion_actual}</span></div>` : ''}
        </div>
    `;
}

function updateCategoryCounts(categorias) {
    const el = document.getElementById('category-counts');
    if (!el || !categorias) return;
    el.innerHTML = Object.entries(categorias).map(([cat, count]) =>
        `<div class="flex justify-between"><span>${cat.replace(/_/g, ' ')}</span><span class="text-gray-300">${count}</span></div>`
    ).join('');
}

// ==================== IANAE Metrics ====================

function updateIANAEMetrics(data) {
    if (!data) return;
    const m = data.metricas || data;
    if (m.ciclos_pensamiento !== undefined) {
        const el = document.getElementById('ianae-ciclos');
        if (el) el.textContent = m.ciclos_pensamiento;
    }
    if (m.auto_modificaciones !== undefined) {
        const el = document.getElementById('ianae-automods');
        if (el) el.textContent = m.auto_modificaciones;
    }
    if (m.emergencias_detectadas !== undefined) {
        const el = document.getElementById('ianae-emergencias');
        if (el) el.textContent = m.emergencias_detectadas;
    }
    if (data.conceptos !== undefined || data.conceptos_total !== undefined) {
        const el = document.getElementById('ianae-conceptos');
        if (el) el.textContent = data.conceptos || data.conceptos_total || (data.nodes ? data.nodes.length : '--');
    }
    if (data.relaciones !== undefined || data.relaciones_total !== undefined) {
        const el = document.getElementById('ianae-relaciones');
        if (el) el.textContent = data.relaciones || data.relaciones_total || (data.links ? data.links.length : '--');
    }
    // From network data
    if (data.nodes) {
        const el = document.getElementById('ianae-conceptos');
        if (el) el.textContent = data.nodes.length;
    }
    if (data.links) {
        const el = document.getElementById('ianae-relaciones');
        if (el) el.textContent = data.links.length;
    }
}

function updateIANAEMetricsFromObj(m) {
    if (m.ciclos_pensamiento !== undefined) {
        const el = document.getElementById('ianae-ciclos');
        if (el) el.textContent = m.ciclos_pensamiento;
    }
    if (m.auto_modificaciones !== undefined) {
        const el = document.getElementById('ianae-automods');
        if (el) el.textContent = m.auto_modificaciones;
    }
    if (m.emergencias_detectadas !== undefined) {
        const el = document.getElementById('ianae-emergencias');
        if (el) el.textContent = m.emergencias_detectadas;
    }
}

// ==================== Text Ingestion (Phase 2) ====================

async function loadAvailableConcepts() {
    try {
        const response = await fetch(`${API_BASE}/api/ianae/network`);
        const data = await response.json();
        const container = document.getElementById('available-concepts');
        if (!container || !data.nodes) return;

        container.innerHTML = data.nodes.map(n =>
            `<button onclick="document.getElementById('ingest-text').value='${n.id}'" class="text-xs px-2 py-1 rounded border border-gray-600 hover:border-blue-500 hover:text-blue-400 text-gray-400 transition-colors">${n.id.replace(/_/g, ' ')}</button>`
        ).join('');
    } catch (e) {
        console.error('Error loading concepts:', e);
    }
}

async function processText() {
    const text = document.getElementById('ingest-text').value.trim();
    if (!text) return;

    const btn = document.getElementById('btn-process');
    const resultDiv = document.getElementById('ingest-result');
    btn.disabled = true;
    btn.textContent = 'Procesando...';
    resultDiv.innerHTML = '<div class="text-xs text-blue-400 text-center py-4">Activando red IANAE...</div>';

    try {
        const depth = parseInt(document.getElementById('ingest-depth').value);
        const temp = parseInt(document.getElementById('ingest-temp').value) / 100;

        const response = await fetch(`${API_BASE}/api/ianae/process-text`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text, profundidad: depth, temperatura: temp})
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.innerHTML = `<div class="text-red-400 text-xs">${data.error}</div>`;
            return;
        }

        // Render result
        const nlpConceptos = data.conceptos_nlp_extraidos || [];
        const nlpModo = data.nlp_modo || 'no_disponible';
        let html = `
            <div class="space-y-3">
                <div class="p-3 bg-gray-750 rounded border border-blue-600">
                    <div class="text-sm font-semibold text-blue-400">Concepto activado: ${data.concepto_activado}</div>
                    ${data.conceptos_encontrados.length > 1 ? `<div class="text-xs text-gray-400 mt-1">Matches: ${data.conceptos_encontrados.join(', ')}</div>` : ''}
                    <div class="text-xs text-gray-500 mt-1">Mods Hebbianas: ${data.modificaciones_hebbianas} | NLP: ${nlpModo}</div>
                </div>
                ${nlpConceptos.length > 0 ? `
                <div class="p-3 bg-gray-750 rounded border border-pink-600">
                    <div class="text-xs font-semibold text-pink-400 mb-1">Conceptos NLP extraidos (${nlpConceptos.length}):</div>
                    <div class="flex flex-wrap gap-1">${nlpConceptos.map(c => `<span class="text-xs px-2 py-0.5 rounded bg-pink-900 text-pink-300">${c}</span>`).join('')}</div>
                </div>` : ''}
                <div>
                    <div class="text-xs font-semibold text-gray-300 mb-2">Top Activaciones:</div>
                    <div class="space-y-1">
        `;

        (data.activaciones || []).forEach(a => {
            const pct = Math.min(100, a.activacion * 100);
            html += `
                <div class="flex items-center space-x-2">
                    <span class="text-xs text-gray-400 w-28 truncate">${a.concepto}</span>
                    <div class="flex-1 bg-gray-700 rounded-full h-2">
                        <div class="bg-blue-500 h-2 rounded-full" style="width:${pct}%"></div>
                    </div>
                    <span class="text-xs text-gray-500 w-12 text-right">${a.activacion.toFixed(3)}</span>
                </div>
            `;
        });

        html += '</div></div></div>';
        resultDiv.innerHTML = html;

        // Show mini network
        if (data.network) {
            document.getElementById('ingest-network-container').classList.remove('hidden');
            renderD3Network(data.network, 'ingest-network-svg');
            // Also update main network
            renderD3Network(data.network, 'network-svg');
            updateIANAEMetrics(data.network);
        }

    } catch (error) {
        resultDiv.innerHTML = `<div class="text-red-400 text-xs">Error: ${error.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Activar Red IANAE';
    }
}

// ==================== Experiments (Phase 4) ====================

async function runExperiment(name, params) {
    const resultDiv = document.getElementById('experiment-result');
    const metricasDiv = document.getElementById('exp-metricas');
    resultDiv.innerHTML = `<div class="text-blue-400">Ejecutando experimento: ${name}...</div>`;

    try {
        const response = await fetch(`${API_BASE}/api/ianae/experiment/${name}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({params})
        });

        const data = await response.json();

        if (data.detail) {
            resultDiv.innerHTML = `<div class="text-red-400">${data.detail}</div>`;
            return;
        }

        resultDiv.textContent = data.resultado || 'Experimento completado';

        if (data.metricas) {
            metricasDiv.textContent = `edad:${data.metricas.edad} ciclos:${data.metricas.ciclos_pensamiento} mods:${data.metricas.auto_modificaciones}`;
            updateIANAEMetricsFromObj(data.metricas);
        }

        if (data.network) {
            renderD3Network(data.network, 'exp-network-svg');
            // Also update main network
            renderD3Network(data.network, 'network-svg');
            updateIANAEMetrics(data.network);
        }

    } catch (error) {
        resultDiv.innerHTML = `<div class="text-red-400">Error: ${error.message}</div>`;
    }
}

function runConvergencia() {
    const checks = document.querySelectorAll('.conv-check:checked');
    const proyectos = Array.from(checks).map(c => c.value);
    if (proyectos.length < 2) {
        document.getElementById('experiment-result').innerHTML = '<div class="text-yellow-400">Selecciona al menos 2 proyectos</div>';
        return;
    }
    runExperiment('convergencia_proyectos', {proyectos});
}

// ==================== Snapshots ====================

async function saveSnapshot() {
    const name = document.getElementById('snapshot-name').value.trim() || 'manual';
    try {
        const response = await fetch(`${API_BASE}/api/ianae/snapshot/save?name=${encodeURIComponent(name)}`, {method: 'POST'});
        const data = await response.json();
        if (data.saved) {
            document.getElementById('snapshot-name').value = '';
            loadSnapshots();
        }
    } catch (e) {
        console.error('Error saving snapshot:', e);
    }
}

async function loadSnapshots() {
    try {
        const response = await fetch(`${API_BASE}/api/ianae/snapshots`);
        const data = await response.json();
        const list = document.getElementById('snapshots-list');
        if (!list) return;

        if (!data.snapshots || data.snapshots.length === 0) {
            list.innerHTML = '<div class="text-xs text-gray-500">No hay snapshots</div>';
            return;
        }

        list.innerHTML = data.snapshots.map(s =>
            `<div class="flex items-center justify-between p-1 hover:bg-gray-700 rounded">
                <div class="text-xs text-gray-400 truncate flex-1">${s.filename}</div>
                <div class="flex items-center space-x-2">
                    <span class="text-xs text-gray-500">${s.size_kb}KB</span>
                    <button onclick="loadSnapshotFile('${s.filename}')" class="text-xs text-blue-400 hover:text-blue-300">Cargar</button>
                </div>
            </div>`
        ).join('');
    } catch (e) {
        console.error('Error loading snapshots:', e);
    }
}

async function loadSnapshotFile(filename) {
    try {
        const response = await fetch(`${API_BASE}/api/ianae/snapshot/load?filename=${encodeURIComponent(filename)}`, {method: 'POST'});
        const data = await response.json();
        if (data.loaded) {
            loadNetwork();
        }
    } catch (e) {
        console.error('Error loading snapshot:', e);
    }
}

// ==================== Polling Loop (Orchestra tab) ====================

function startPolling() {
    updateAll();
    updateTimer = setInterval(updateAll, UPDATE_INTERVAL);
}

async function updateAll() {
    try {
        await Promise.all([
            updateStatus(),
            updateDocuments(),
            updateWorkers(),
            updateActivity(),
            updateMetrics(),
            updateAlerts()
        ]);
        const now = new Date().toLocaleTimeString('es-ES');
        document.getElementById('last-update').textContent = `${now}`;
    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

// ==================== Status Update ====================

async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();

        const docsService = data.services?.docs_service;
        if (docsService) {
            const docsEmoji = document.getElementById('docs-status-emoji');
            const docsText = document.getElementById('docs-status-text');
            if (docsService.status === 'online') {
                docsEmoji.textContent = '\u{1F7E2}';
                docsText.textContent = `Online (${docsService.port})`;
                docsText.className = 'text-xs text-green-400';
            } else {
                docsEmoji.textContent = '\u{1F534}';
                docsText.textContent = docsService.status;
                docsText.className = 'text-xs text-red-400';
            }
        }

        const daemon = data.services?.daemon;
        if (daemon) {
            const daemonEmoji = document.getElementById('daemon-status-emoji');
            const daemonText = document.getElementById('daemon-status-text');
            if (daemon.status === 'online') {
                daemonEmoji.textContent = '\u{1F7E2}';
                daemonText.textContent = `Online (${daemon.minutes_ago || 0}min)`;
                daemonText.className = 'text-xs text-green-400';
            } else if (daemon.status === 'idle') {
                daemonEmoji.textContent = '\u{1F7E1}';
                daemonText.textContent = `Idle (${daemon.minutes_ago}min)`;
                daemonText.className = 'text-xs text-yellow-400';
            } else {
                daemonEmoji.textContent = '\u{1F534}';
                daemonText.textContent = daemon.status;
                daemonText.className = 'text-xs text-red-400';
            }
        }

        const apiMetrics = data.api_metrics || {};
        document.getElementById('api-calls-today').textContent = apiMetrics.calls_today || 0;
        document.getElementById('api-cost').textContent = `$${(apiMetrics.cost_estimate || 0).toFixed(2)}`;
        const percentage = ((apiMetrics.calls_today || 0) / 100) * 100;
        document.getElementById('api-progress').style.width = `${percentage}%`;

    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// ==================== Documents Update ====================

async function updateDocuments() {
    try {
        const category = document.getElementById('filter-category').value;
        const worker = document.getElementById('filter-worker').value;

        let url = `${API_BASE}/api/documents?limit=50`;
        if (category) url += `&category=${category}`;
        if (worker) url += `&worker=${worker}`;

        const response = await fetch(url);
        const data = await response.json();
        lastDocuments = data.documents || [];

        const tbody = document.getElementById('documents-tbody');
        tbody.innerHTML = '';

        if (lastDocuments.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-500">No hay documentos</td></tr>';
            return;
        }

        lastDocuments.forEach(doc => {
            const row = document.createElement('tr');
            row.className = 'border-b border-gray-700 hover:bg-gray-750 cursor-pointer';
            row.onclick = () => showDocument(doc);

            const title = doc.title.length > 50 ? doc.title.substring(0, 50) + '...' : doc.title;
            const statusColors = {
                'pending': 'bg-blue-600', 'in_progress': 'bg-yellow-600',
                'completed': 'bg-green-600', 'blocked': 'bg-red-600', 'cancelled': 'bg-gray-600'
            };
            const workflowStatus = doc.workflow_status || doc.status || 'pending';
            const statusColor = statusColors[workflowStatus] || 'bg-gray-600';

            row.innerHTML = `
                <td class="py-2 text-gray-400">${doc.id}</td>
                <td class="py-2">${escapeHtml(title)}</td>
                <td class="py-2 text-gray-400">${doc.author}</td>
                <td class="py-2"><span class="text-xs px-2 py-1 rounded ${getCategoryColor(doc.category)}">${doc.category}</span></td>
                <td class="py-2"><span class="text-xs px-2 py-1 rounded ${statusColor}">${workflowStatus}</span></td>
                <td class="py-2 text-xs text-gray-400">${doc.relative_time}</td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error fetching documents:', error);
        document.getElementById('documents-tbody').innerHTML =
            '<tr><td colspan="6" class="text-center py-4 text-red-400">Error cargando documentos</td></tr>';
    }
}

// ==================== Workers Update ====================

async function updateWorkers() {
    try {
        const response = await fetch(`${API_BASE}/api/workers`);
        const data = await response.json();
        const workersList = document.getElementById('workers-list');
        workersList.innerHTML = '';

        if (!data.workers || data.workers.length === 0) {
            workersList.innerHTML = '<div class="text-xs text-gray-500 text-center">No hay workers</div>';
            return;
        }

        data.workers.forEach(worker => {
            const div = document.createElement('div');
            div.className = 'border border-gray-700 rounded p-3';
            div.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <span class="font-semibold text-sm text-gray-200">${worker.name.toUpperCase()}</span>
                    <span class="text-xl">${worker.status_emoji}</span>
                </div>
                <div class="space-y-1 text-xs text-gray-400">
                    <div class="flex justify-between"><span>Pendientes:</span><span class="text-gray-300">${worker.pendientes || 0}</span></div>
                    <div class="flex justify-between"><span>Actividad:</span><span class="text-gray-300">${worker.relative_time || 'nunca'}</span></div>
                    <div class="flex justify-between"><span>Reportes:</span><span class="text-gray-300">${worker.reportes_publicados || 0}</span></div>
                    <div class="flex justify-between"><span>Estado:</span><span class="${getStatusColor(worker.status)}">${worker.status}</span></div>
                </div>
            `;
            workersList.appendChild(div);
        });
    } catch (error) {
        console.error('Error fetching workers:', error);
    }
}

// ==================== Activity Update ====================

async function updateActivity() {
    try {
        const response = await fetch(`${API_BASE}/api/activity?limit=50`);
        const data = await response.json();
        const timeline = document.getElementById('activity-timeline');
        timeline.innerHTML = '';

        if (!data.activity || data.activity.length === 0) {
            timeline.innerHTML = '<div class="text-xs text-gray-500 text-center">No hay actividad</div>';
            return;
        }

        const colorClasses = {
            'ORDEN': 'text-blue-400', 'REPORTE': 'text-green-400', 'DUDA': 'text-yellow-400',
            'RESPUESTA': 'text-purple-400', 'ESCALADO': 'text-red-400', 'INFO': 'text-gray-400'
        };

        data.activity.forEach(event => {
            const div = document.createElement('div');
            div.className = 'flex items-start space-x-3 p-2 hover:bg-gray-750 rounded';
            div.innerHTML = `
                <div class="text-xs text-gray-500 w-16 flex-shrink-0">${event.relative_time}</div>
                <div class="flex-1">
                    <span class="text-xs font-semibold ${colorClasses[event.tipo] || 'text-gray-400'}">[${event.tipo}]</span>
                    <span class="text-xs text-gray-400">${event.author} &rarr;</span>
                    <span class="text-xs text-gray-300">${escapeHtml(event.title)}</span>
                </div>
            `;
            timeline.appendChild(div);
        });
    } catch (error) {
        console.error('Error fetching activity:', error);
    }
}

// ==================== Metrics Update ====================

async function updateMetrics() {
    try {
        const response = await fetch(`${API_BASE}/api/metrics`);
        const data = await response.json();
        if (data.error) return;

        const quality = data.quality || {};
        document.getElementById('metric-efectividad').textContent = `${(quality.efectividad_daemon || 0).toFixed(1)}%`;
        document.getElementById('metric-autonomia').textContent = `${(quality.autonomia_real || 0).toFixed(1)}%`;
        document.getElementById('metric-completacion').textContent = `${(quality.tasa_completacion || 0).toFixed(1)}%`;
        document.getElementById('metric-throughput').textContent = quality.total_reportes || 0;
    } catch (error) {
        console.error('Error fetching metrics:', error);
    }
}

// ==================== Alerts Update ====================

async function updateAlerts() {
    try {
        const response = await fetch(`${API_BASE}/api/alerts`);
        const data = await response.json();

        const alertsContainer = document.getElementById('alerts-container');
        const alertsList = document.getElementById('alerts-list');
        const alertsCount = document.getElementById('alerts-count');

        if (!data.alerts || data.alerts.length === 0) {
            alertsContainer.classList.add('hidden');
            return;
        }

        alertsContainer.classList.remove('hidden');
        alertsCount.textContent = data.count;

        if (data.has_critical) {
            alertsCount.className = 'text-xs px-2 py-1 rounded bg-red-600 text-white';
        } else if (data.has_error) {
            alertsCount.className = 'text-xs px-2 py-1 rounded bg-orange-600 text-white';
        } else {
            alertsCount.className = 'text-xs px-2 py-1 rounded bg-yellow-600 text-white';
        }

        alertsList.innerHTML = '';
        data.alerts.slice(0, 10).forEach(alert => {
            const div = document.createElement('div');
            let bgColor, textColor, icon;
            if (alert.level === 'critical') { bgColor = 'bg-red-900 border-red-700'; textColor = 'text-red-300'; icon = '\u{1F534}'; }
            else if (alert.level === 'error') { bgColor = 'bg-orange-900 border-orange-700'; textColor = 'text-orange-300'; icon = '\u{1F7E0}'; }
            else { bgColor = 'bg-yellow-900 border-yellow-700'; textColor = 'text-yellow-300'; icon = '\u{1F7E1}'; }

            div.className = `flex items-start space-x-2 p-2 rounded border ${bgColor}`;
            div.innerHTML = `
                <span class="text-sm">${icon}</span>
                <div class="flex-1">
                    <div class="text-xs ${textColor} font-semibold">${alert.type.toUpperCase().replace(/_/g, ' ')}</div>
                    <div class="text-xs text-gray-300">${escapeHtml(alert.message)}</div>
                </div>
            `;
            alertsList.appendChild(div);
        });
    } catch (error) {
        console.error('Error fetching alerts:', error);
    }
}

// ==================== Modal ====================

function showDocument(doc) {
    document.getElementById('modal-title').textContent = doc.title;
    document.getElementById('modal-content').textContent = doc.content || 'Sin contenido';
    document.getElementById('document-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('document-modal').classList.add('hidden');
}

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

// ==================== Helpers ====================

function getCategoryColor(category) {
    return {'especificaciones': 'bg-blue-600', 'reportes': 'bg-green-600', 'dudas': 'bg-yellow-600', 'decisiones': 'bg-purple-600'}[category] || 'bg-gray-600';
}

function getStatusColor(status) {
    return {'Activo': 'text-green-400', 'Iniciando': 'text-yellow-400', 'Inactivo': 'text-red-400', 'Sin arrancar': 'text-gray-400', 'Error': 'text-red-400'}[status] || 'text-gray-400';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

window.addEventListener('beforeunload', () => {
    if (updateTimer) clearInterval(updateTimer);
    if (ws) ws.close();
});

console.log('IANAE Dashboard v2.0 JS loaded');
