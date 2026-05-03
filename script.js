// ═══════════════════════════════════════════════════════════
// CARTAS T — Sistema Completo de las 4 Máquinas
// Basado en "Poética Menor" de Daniel Zimmermann
// ═══════════════════════════════════════════════════════════

// ── Las 22 Cartas: 10 Individuos + 12 Componentes ──
const arcanosData = [
    // 10 Individuos (Planetas / Principios Fundamentales)
    { id:1,  title:'Generación',     type:'Individuo',    symbol:'☉', color:'#e67e22', meaning:'Fuerza generativa, origen y nacimiento de la energía vital.' },
    { id:2,  title:'Regresión',      type:'Individuo',    symbol:'☽', color:'#7f8c8d', meaning:'Retorno a las fuentes, movimiento hacia atrás, memoria profunda.' },
    { id:3,  title:'Selección',      type:'Individuo',    symbol:'☿', color:'#f39c12', meaning:'Elección discriminativa, separación de lo esencial de lo accesorio.' },
    { id:4,  title:'Inestabilidad',  type:'Individuo',    symbol:'♀', color:'#27ae60', meaning:'Cambio, fluctuación y la danza entre opuestos.' },
    { id:5,  title:'Desplazamiento', type:'Individuo',    symbol:'♂', color:'#c0392b', meaning:'Movimiento, transferencia y traslación de fuerzas.' },
    { id:6,  title:'Tendencia',      type:'Individuo',    symbol:'♃', color:'#2980b9', meaning:'Inclinación natural, propensión y dirección espontánea.' },
    { id:7,  title:'Plan',           type:'Individuo',    symbol:'♄', color:'#6c3483', meaning:'Estructuración consciente, diseño intencional del proceso.' },
    { id:8,  title:'Polaridad',      type:'Individuo',    symbol:'♅', color:'#0e6655', meaning:'Tensión entre opuestos como motor de la transformación.' },
    { id:9,  title:'Energía',        type:'Individuo',    symbol:'♆', color:'#1a5276', meaning:'Carga, potencial y capacidad de trabajo del sistema.' },
    { id:10, title:'Vitalidad',      type:'Individuo',    symbol:'♇', color:'#512e5f', meaning:'Intensidad y renovación permanente de la fuerza de vida.' },
    // 12 Componentes (Zodiacales / Momentos del Proceso)
    { id:11, title:'Condición',      type:'Componente',   symbol:'♈', color:'#c0392b', meaning:'Circunstancias necesarias que permiten el inicio del proceso.' },
    { id:12, title:'Fusión',         type:'Componente',   symbol:'♉', color:'#27ae60', meaning:'Unión de elementos en un todo nuevo e integrado.' },
    { id:13, title:'División',       type:'Componente',   symbol:'♊', color:'#f39c12', meaning:'Separación analítica para conocer las partes del conjunto.' },
    { id:14, title:'Disolución',     type:'Componente',   symbol:'♋', color:'#2980b9', meaning:'Desintegración de lo rígido para liberar potencial oculto.' },
    { id:15, title:'Activación',     type:'Componente',   symbol:'♌', color:'#e67e22', meaning:'Puesta en marcha, catálisis del proceso dormido.' },
    { id:16, title:'Circulación',    type:'Componente',   symbol:'♍', color:'#7dcea0', meaning:'Flujo dinámico que nutre y mantiene el sistema en movimiento.' },
    { id:17, title:'Precipitación',  type:'Componente',   symbol:'♎', color:'#e91e63', meaning:'Cristalización acelerada, la forma que emerge del caos.' },
    { id:18, title:'Formación',      type:'Componente',   symbol:'♏', color:'#922b21', meaning:'Configuración estructural y moldeado de la materia.' },
    { id:19, title:'Compenetración', type:'Componente',   symbol:'♐', color:'#7b1fa2', meaning:'Interpenetración profunda de fuerzas aparentemente distintas.' },
    { id:20, title:'Desconfusión',   type:'Componente',   symbol:'♑', color:'#4d5656', meaning:'Clarificación, separación del ruido del proceso verdadero.' },
    { id:21, title:'Conversión',     type:'Componente',   symbol:'♒', color:'#0097a7', meaning:'Transformación cualitativa, cambio de naturaleza de la energía.' },
    { id:22, title:'Proyección',     type:'Componente',   symbol:'♓', color:'#1976d2', meaning:'Lanzamiento hacia el exterior, manifestación en el mundo.' }
];

// ── Definición de las 4 Máquinas ──
const MACHINES = {
    siquica: {
        name: 'Máquina Síquica',
        cardsNeeded: 5,
        positions: ['Centro Vegetativo / Sexual', 'Centro Motriz', 'Centro Emotivo', 'Centro Intelectual', 'Centro Emotivo Superior']
    },
    alquimia: {
        name: 'Máquina de la Alquimia',
        cardsNeeded: 9,
        positions: ['1 — Punto de partida', '2 — Primer choque', '3 — Resultado parcial', '4 — Intervención externa', '5 — Centro del proceso', '6 — Restricción', '7 — Resultado inevitable', '8 — Segundo choque', '9 — Síntesis final']
    },
    arbol: {
        name: 'Máquina del Árbol',
        cardsNeeded: 10,
        positions: ['Kether — Corona', 'Chokmah — Sabiduría', 'Binah — Entendimiento', 'Chesed — Amor', 'Geburah — Fuerza', 'Tiphareth — Belleza', 'Netzach — Victoria', 'Hod — Esplendor', 'Yesod — Fundamento', 'Malkuth — Reino']
    },
    horoscopo: {
        name: 'Máquina del Horóscopo',
        cardsNeeded: 12,
        positions: ['Casa 1 — El Yo / Ascendente', 'Casa 2 — Recursos propios', 'Casa 3 — Comunicación', 'Casa 4 — Hogar / Raíces', 'Casa 5 — Creatividad', 'Casa 6 — Servicio / Salud', 'Casa 7 — Vínculos', 'Casa 8 — Transformación', 'Casa 9 — Filosofía', 'Casa 10 — Vocación / Legado', 'Casa 11 — Comunidad', 'Casa 12 — Lo oculto / Karma']
    }
};

// ── Estado global ──
let activeCards = [];
let selectedMachine = null;
let intentionTriple = {};

// ── Refs UI ──
const screens = {
    start: document.getElementById('start-screen'),
    game:  document.getElementById('game-screen'),
    result:document.getElementById('result-screen')
};
const ui = {
    startBtn:      document.getElementById('start-btn'),
    restartBtn:    document.getElementById('restart-btn'),
    cosmicInput:   document.getElementById('intention-cosmic'),
    psychicInput:  document.getElementById('intention-psychic'),
    alchemicalInput: document.getElementById('intention-alchemical'),
    machineBadge:  document.getElementById('game-machine-badge'),
    instructionTxt:document.getElementById('instruction-text'),
    cardsCount:    document.getElementById('cards-count'),
    row1:          document.getElementById('row-1'),
    row2:          document.getElementById('row-2'),
    finalLayout:   document.getElementById('machine-layout'),
    resultTitle:   document.getElementById('result-title'),
    resultSubtitle:document.getElementById('result-subtitle'),
    concept:       document.getElementById('combined-concept')
};

// ── Init ──
function init() {
    // Machine card selection
    document.querySelectorAll('.machine-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.machine-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedMachine = card.dataset.machine;
            ui.startBtn.disabled = false;
            ui.startBtn.textContent = `Iniciar — ${MACHINES[selectedMachine].name}`;
        });
    });

    ui.startBtn.addEventListener('click', startRitual);
    ui.restartBtn.addEventListener('click', resetRitual);
    ui.row1.addEventListener('click', () => selectRow(1));
    ui.row2.addEventListener('click', () => selectRow(2));
}

function showScreen(name) {
    Object.values(screens).forEach(s => s.classList.remove('active'));
    screens[name].classList.add('active');
}

function shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

// ── Start ──
function startRitual() {
    if (!selectedMachine) return;
    intentionTriple = {
        cosmic:    ui.cosmicInput.value.trim()     || 'Propósito Mayor',
        psychic:   ui.psychicInput.value.trim()    || 'Estado Emocional',
        alchemical:ui.alchemicalInput.value.trim() || 'Acción Material'
    };
    const machine = MACHINES[selectedMachine];
    ui.machineBadge.textContent = machine.name.toUpperCase();
    activeCards = shuffle(arcanosData);
    dealCards();
    showScreen('game');
}

function resetRitual() {
    ui.cosmicInput.value = '';
    ui.psychicInput.value = '';
    ui.alchemicalInput.value = '';
    document.querySelectorAll('.machine-card').forEach(c => c.classList.remove('selected'));
    selectedMachine = null;
    ui.startBtn.disabled = true;
    ui.startBtn.textContent = 'Selecciona una Máquina';
    ui.concept.classList.remove('visible');
    showScreen('start');
}

// ── Crear HTML de carta pequeña ──
function createCardHTML(card) {
    return `
        <div class="card" data-id="${card.id}">
            <div class="card-inner">
                <div class="card-face card-back">
                    <div class="card-back-pattern">
                        <div class="card-back-t">T</div>
                    </div>
                </div>
                <div class="card-face card-front">
                    <div class="cf-inner" style="border-color:${card.color}">
                        <span class="cf-num" style="color:${card.color}">${card.id}</span>
                        <span class="cf-symbol" style="color:${card.color}">${card.symbol}</span>
                        <div class="cf-human">
                            <div class="cf-head"></div>
                            <div class="cf-body">
                                <div class="cf-arms"></div>
                                <div class="cf-chakra c1"></div>
                                <div class="cf-chakra c2"></div>
                                <div class="cf-chakra c3"></div>
                                <div class="cf-chakra c4"></div>
                            </div>
                            <div class="cf-legs"></div>
                        </div>
                        <div class="cf-title" style="color:${card.color}">${card.title}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ── Crear HTML de carta resultado (grande, posicionable) ──
function createResultCardHTML(card, posLabel) {
    return `
        <div class="result-card" data-id="${card.id}">
            <div class="card-inner">
                <div class="card-face card-back">
                    <div class="card-back-pattern">
                        <div class="card-back-t">T</div>
                    </div>
                </div>
                <div class="card-face card-front">
                    <div class="cf-inner" style="border-color:${card.color}">
                        <span class="cf-num" style="color:${card.color}">${card.id}</span>
                        <span class="cf-symbol" style="color:${card.color}">${card.symbol}</span>
                        <div class="cf-human">
                            <div class="cf-head"></div>
                            <div class="cf-body">
                                <div class="cf-arms"></div>
                                <div class="cf-chakra c1"></div>
                                <div class="cf-chakra c2"></div>
                                <div class="cf-chakra c3"></div>
                                <div class="cf-chakra c4"></div>
                            </div>
                            <div class="cf-legs"></div>
                        </div>
                        <div class="cf-title" style="color:${card.color}">${card.title}</div>
                        <div class="cf-type">${card.type}</div>
                    </div>
                </div>
            </div>
            <div class="card-pos-label">${posLabel}</div>
        </div>
    `;
}

// ── Repartir cartas ──
function dealCards() {
    const machine = MACHINES[selectedMachine];
    const target = machine.cardsNeeded;

    ui.row1.querySelector('.row-label').textContent = 'FILA A — Haz clic para elegir';
    ui.row2.querySelector('.row-label').textContent = 'FILA B — Haz clic para elegir';

    ui.row1.innerHTML = '<div class="row-label">FILA A — Haz clic para elegir</div>';
    ui.row2.innerHTML = '<div class="row-label">FILA B — Haz clic para elegir</div>';
    ui.row1.classList.remove('discarding');
    ui.row2.classList.remove('discarding');

    const half = Math.ceil(activeCards.length / 2);
    const half1 = activeCards.slice(0, half);
    const half2 = activeCards.slice(half);

    half1.forEach((card, idx) => {
        setTimeout(() => ui.row1.insertAdjacentHTML('beforeend', createCardHTML(card)), idx * 40);
    });
    half2.forEach((card, idx) => {
        setTimeout(() => ui.row2.insertAdjacentHTML('beforeend', createCardHTML(card)), (idx + half1.length) * 40);
    });

    ui.cardsCount.textContent = activeCards.length;
    ui.instructionTxt.textContent = `Quedan ${activeCards.length} cartas. Necesitas ${target}. Siente la fila que más resuena contigo.`;
}

// ── Seleccionar fila ──
function selectRow(rowNum) {
    if (ui.row1.classList.contains('discarding') || ui.row2.classList.contains('discarding')) return;
    const machine = MACHINES[selectedMachine];
    const target = machine.cardsNeeded;

    const discardedRow = rowNum === 1 ? ui.row2 : ui.row1;
    discardedRow.classList.add('discarding');

    const half = Math.ceil(activeCards.length / 2);
    activeCards = rowNum === 1 ? activeCards.slice(0, half) : activeCards.slice(half);

    setTimeout(() => {
        // Si las cartas son <= target, terminamos
        if (activeCards.length <= target) {
            // Trim si hay más de las necesarias
            activeCards = activeCards.slice(0, target);
            showFinalResult();
        } else {
            activeCards = shuffle(activeCards);
            dealCards();
        }
    }, 700);
}

// ── Mostrar resultado ──
function showFinalResult() {
    const machine = MACHINES[selectedMachine];
    ui.resultTitle.textContent = machine.name;
    ui.resultSubtitle.textContent = `Las ${activeCards.length} cartas revelan tu lectura completa`;

    showScreen('result');
    renderMachineLayout();

    // Voltear cartas secuencialmente
    setTimeout(() => {
        const cards = ui.finalLayout.querySelectorAll('.result-card');
        cards.forEach((el, i) => {
            setTimeout(() => el.classList.add('flipped'), i * 350);
        });
    }, 400);

    // Concepto combinado
    setTimeout(() => buildCombinedConcept(), 400 + activeCards.length * 350 + 800);
}

// ── Renderizar geometría de cada máquina ──
function renderMachineLayout() {
    ui.finalLayout.innerHTML = '';

    switch (selectedMachine) {
        case 'siquica':    renderSiquica();    break;
        case 'alquimia':   renderAlquimia();   break;
        case 'arbol':      renderArbol();      break;
        case 'horoscopo':  renderHoroscopo();  break;
    }
}

// ── Síquica: columna vertical de 5 centros ──
function renderSiquica() {
    const machine = MACHINES.siquica;
    const container = document.createElement('div');
    container.className = 'layout-siquica';

    // Línea vertebral visual
    const spine = document.createElement('div');
    spine.className = 'siquica-spine';
    container.appendChild(spine);

    // Centro inferior a superior
    const labels = machine.positions;
    // invertimos para que el vegetativo quede abajo
    const reversed = [...activeCards].reverse();
    reversed.forEach((card, i) => {
        const row = document.createElement('div');
        row.className = 'siquica-row';
        row.innerHTML = `
            <div class="siquica-label">${labels[labels.length - 1 - i]}</div>
            ${createResultCardHTML(card, labels[labels.length - 1 - i].split(' — ')[0])}
            <div class="siquica-label right"></div>
        `;
        container.appendChild(row);
    });

    ui.finalLayout.appendChild(container);
}

// ── Árbol de la Vida: 10 esferas en formación clásica ──
function renderArbol() {
    // Posiciones relativas (x%, y%) para la formación Sephiroth
    const sephirothPos = [
        [50, 3],   // 0 Kether
        [27, 16],  // 1 Chokmah
        [73, 16],  // 2 Binah
        [27, 35],  // 3 Chesed
        [73, 35],  // 4 Geburah
        [50, 47],  // 5 Tiphareth
        [27, 60],  // 6 Netzach
        [73, 60],  // 7 Hod
        [50, 74],  // 8 Yesod
        [50, 90],  // 9 Malkuth
    ];

    const container = document.createElement('div');
    container.className = 'layout-arbol';

    // SVG lines connecting sephiroth
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'layout-svg');
    const W = 500, H = 720;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);

    const paths = [
        [0,1],[0,2],[1,2],[1,3],[2,4],[1,5],[2,5],[3,5],[4,5],
        [3,4],[3,6],[4,7],[5,6],[5,7],[5,8],[6,7],[6,8],[7,8],[8,9]
    ];
    paths.forEach(([a,b]) => {
        const x1 = sephirothPos[a][0] / 100 * W;
        const y1 = sephirothPos[a][1] / 100 * H + 45;
        const x2 = sephirothPos[b][0] / 100 * W;
        const y2 = sephirothPos[b][1] / 100 * H + 45;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1); line.setAttribute('y1', y1);
        line.setAttribute('x2', x2); line.setAttribute('y2', y2);
        line.setAttribute('stroke', '#ccc'); line.setAttribute('stroke-width', '1.5');
        svg.appendChild(line);
    });
    container.appendChild(svg);

    const machine = MACHINES.arbol;
    activeCards.forEach((card, i) => {
        const [xp, yp] = sephirothPos[i];
        const wrapper = document.createElement('div');
        wrapper.style.cssText = `position:absolute; left:${xp}%; top:${yp}%; transform:translate(-50%,-50%);`;
        wrapper.innerHTML = createResultCardHTML(card, machine.positions[i].split(' — ')[1]);
        container.appendChild(wrapper);
    });

    ui.finalLayout.appendChild(container);
}

// ── Horóscopo: 12 cartas en círculo ──
function renderHoroscopo() {
    const container = document.createElement('div');
    container.className = 'layout-horoscopo';

    const center = document.createElement('div');
    center.className = 'horoscopo-center-label';
    center.innerHTML = '🌐<br>Horóscopo';
    container.appendChild(center);

    const machine = MACHINES.horoscopo;
    const R = 230; // radius in px
    const cx = 300, cy = 300;
    const cardW = 90, cardH = 140;

    activeCards.forEach((card, i) => {
        const angle = (i * 30 - 90) * (Math.PI / 180); // start top
        const x = cx + R * Math.cos(angle) - cardW / 2;
        const y = cy + R * Math.sin(angle) - cardH / 2;
        const wrapper = document.createElement('div');
        wrapper.style.cssText = `position:absolute; left:${x}px; top:${y}px;`;
        wrapper.innerHTML = createResultCardHTML(card, machine.positions[i].split(' — ')[1]);
        container.appendChild(wrapper);
    });

    ui.finalLayout.appendChild(container);
}

// ── Alquimia (Eneagrama): 9 puntos ──
function renderAlquimia() {
    const container = document.createElement('div');
    container.className = 'layout-alquimia';

    const machine = MACHINES.alquimia;
    const R = 220;
    const cx = 280, cy = 280;
    const cardW = 90, cardH = 140;

    // Eneagrama: 9 puntos con distribución específica (0 en la cima)
    activeCards.forEach((card, i) => {
        const angle = (i * 40 - 90) * (Math.PI / 180);
        const x = cx + R * Math.cos(angle) - cardW / 2;
        const y = cy + R * Math.sin(angle) - cardH / 2;
        const wrapper = document.createElement('div');
        wrapper.style.cssText = `position:absolute; left:${x}px; top:${y}px;`;
        wrapper.innerHTML = createResultCardHTML(card, (i + 1).toString());
        container.appendChild(wrapper);
    });

    // SVG eneagrama lines (inner triangle + hexagon pattern)
    const W = 560, H = 560;
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'layout-svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);

    const pts = Array.from({length: 9}, (_, i) => {
        const a = (i * 40 - 90) * Math.PI / 180;
        return [cx + R * Math.cos(a) + cardW / 2, cy + R * Math.sin(a) + cardH / 2];
    });
    // Inner triangle (3-6-9 style → indices 2,5,8)
    [[2,5],[5,8],[8,2]].forEach(([a,b]) => {
        const line = document.createElementNS('http://www.w3.org/2000/svg','line');
        line.setAttribute('x1',pts[a][0]); line.setAttribute('y1',pts[a][1]);
        line.setAttribute('x2',pts[b][0]); line.setAttribute('y2',pts[b][1]);
        line.setAttribute('stroke','#aaa'); line.setAttribute('stroke-width','1.5');
        svg.appendChild(line);
    });
    // Outer lines between consecutive points
    for (let i = 0; i < 9; i++) {
        const next = (i + 1) % 9;
        const line = document.createElementNS('http://www.w3.org/2000/svg','line');
        line.setAttribute('x1',pts[i][0]); line.setAttribute('y1',pts[i][1]);
        line.setAttribute('x2',pts[next][0]); line.setAttribute('y2',pts[next][1]);
        line.setAttribute('stroke','#ddd'); line.setAttribute('stroke-width','1');
        svg.appendChild(line);
    }
    container.appendChild(svg);

    ui.finalLayout.appendChild(container);
}

// ── Texto síntesis ──
function buildCombinedConcept() {
    const machine = MACHINES[selectedMachine];
    let html = `<h3>Síntesis de la ${machine.name}</h3>`;

    const levels = ['Cósmico', 'Psíquico', 'Alquímico'];
    const intentions = [intentionTriple.cosmic, intentionTriple.psychic, intentionTriple.alchemical];

    // Primeras 3 cartas → Pregunta Triple
    html += `<p><strong>Pregunta Triple:</strong></p>`;
    for (let i = 0; i < Math.min(3, activeCards.length); i++) {
        const c = activeCards[i];
        html += `<p><strong>Nivel ${levels[i]}:</strong> <em>"${intentions[i]}"</em><br>
        → <strong>${c.symbol} ${c.title}</strong> (${c.type}): ${c.meaning}</p>`;
    }

    // Resto de cartas → posiciones de la máquina
    if (activeCards.length > 3) {
        html += `<p><strong>Posiciones de la ${machine.name}:</strong></p>`;
        for (let i = 3; i < activeCards.length; i++) {
            const c = activeCards[i];
            const pos = machine.positions[i] || `Posición ${i + 1}`;
            html += `<p><strong>${pos}:</strong> <strong>${c.symbol} ${c.title}</strong> — ${c.meaning}</p>`;
        }
    }

    ui.concept.innerHTML = html;
    ui.concept.classList.add('visible');
}

// ── Arrancar ──
init();
