const arcanosData = [
    // 10 Individuos (Planetarios / Alquímicos)
    { id: 1, title: 'El Sol', type: 'Individuo', symbol: '☉', color: '#d32f2f', meaning: 'Esencia pura, vitalidad y claridad de consciencia.' },
    { id: 2, title: 'La Luna', type: 'Individuo', symbol: '☽', color: '#1976d2', meaning: 'Intuición profunda, emociones y el inconsciente.' },
    { id: 3, title: 'Mercurio', type: 'Individuo', symbol: '☿', color: '#f57c00', meaning: 'Comunicación, intelecto y adaptación ágil.' },
    { id: 4, title: 'Venus', type: 'Individuo', symbol: '♀', color: '#388e3c', meaning: 'Armonía, atracción y valor estético.' },
    { id: 5, title: 'Marte', type: 'Individuo', symbol: '♂', color: '#d32f2f', meaning: 'Acción, voluntad, fuerza impulsora y deseo.' },
    { id: 6, title: 'Júpiter', type: 'Individuo', symbol: '♃', color: '#1976d2', meaning: 'Expansión, sabiduría y crecimiento filosófico.' },
    { id: 7, title: 'Saturno', type: 'Individuo', symbol: '♄', color: '#5d4037', meaning: 'Estructura, límites, tiempo y disciplina.' },
    { id: 8, title: 'Urano', type: 'Individuo', symbol: '♅', color: '#0097a7', meaning: 'Revolución, originalidad y despertares súbitos.' },
    { id: 9, title: 'Neptuno', type: 'Individuo', symbol: '♆', color: '#7b1fa2', meaning: 'Misticismo, disolución de límites y sueños.' },
    { id: 10, title: 'Plutón', type: 'Individuo', symbol: '♇', color: '#455a64', meaning: 'Transformación profunda, muerte y renacimiento.' },
    // 12 Momentos de Proceso (Zodiacales)
    { id: 11, title: 'Aries', type: 'Proceso', symbol: '♈', color: '#d32f2f', meaning: 'El inicio, el impulso y la chispa originaria.' },
    { id: 12, title: 'Tauro', type: 'Proceso', symbol: '♉', color: '#388e3c', meaning: 'La consolidación, la materia y la estabilidad.' },
    { id: 13, title: 'Géminis', type: 'Proceso', symbol: '♊', color: '#fbc02d', meaning: 'La dualidad, el aprendizaje y el intercambio.' },
    { id: 14, title: 'Cáncer', type: 'Proceso', symbol: '♋', color: '#1976d2', meaning: 'La nutrición, el origen y la protección.' },
    { id: 15, title: 'Leo', type: 'Proceso', symbol: '♌', color: '#f57c00', meaning: 'La expresión, la identidad y el brillo.' },
    { id: 16, title: 'Virgo', type: 'Proceso', symbol: '♍', color: '#689f38', meaning: 'El análisis, el servicio y el perfeccionamiento.' },
    { id: 17, title: 'Libra', type: 'Proceso', symbol: '♎', color: '#e91e63', meaning: 'El equilibrio, el otro y la complementariedad.' },
    { id: 18, title: 'Escorpio', type: 'Proceso', symbol: '♏', color: '#d32f2f', meaning: 'La intensidad, la fusión y la alquimia.' },
    { id: 19, title: 'Sagitario', type: 'Proceso', symbol: '♐', color: '#7b1fa2', meaning: 'La dirección, la búsqueda de sentido y la síntesis.' },
    { id: 20, title: 'Capricornio', type: 'Proceso', symbol: '♑', color: '#455a64', meaning: 'La cristalización, la meta y la maestría.' },
    { id: 21, title: 'Acuario', type: 'Proceso', symbol: '♒', color: '#0097a7', meaning: 'La red, la visión de conjunto y la liberación.' },
    { id: 22, title: 'Piscis', type: 'Proceso', symbol: '♓', color: '#1976d2', meaning: 'La totalidad, la empatía y la redención.' }
];

let activeCards = [];
let intentionTriple = {};

const screens = {
    start: document.getElementById('start-screen'),
    game: document.getElementById('game-screen'),
    result: document.getElementById('result-screen')
};

const ui = {
    startBtn: document.getElementById('start-btn'),
    restartBtn: document.getElementById('restart-btn'),
    cosmicInput: document.getElementById('intention-cosmic'),
    psychicInput: document.getElementById('intention-psychic'),
    alchemicalInput: document.getElementById('intention-alchemical'),
    intentionDisplay: document.getElementById('current-intention-display'),
    row1: document.getElementById('row-1'),
    row2: document.getElementById('row-2'),
    finalCards: document.getElementById('final-cards')
};

function init() {
    ui.startBtn.addEventListener('click', startRitual);
    ui.restartBtn.addEventListener('click', resetRitual);
    ui.row1.addEventListener('click', () => selectRow(1));
    ui.row2.addEventListener('click', () => selectRow(2));
}

function showScreen(screenName) {
    Object.values(screens).forEach(s => s.classList.remove('active'));
    screens[screenName].classList.add('active');
}

function shuffle(array) {
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

function startRitual() {
    intentionTriple = {
        cosmic: ui.cosmicInput.value.trim() || 'Desarrollo Mental',
        psychic: ui.psychicInput.value.trim() || 'Equilibrio Emocional',
        alchemical: ui.alchemicalInput.value.trim() || 'Acción en el Mundo'
    };
    ui.intentionDisplay.textContent = "Siente la vibración de las esferas...";
    
    activeCards = shuffle(arcanosData);
    dealCards();
    showScreen('game');
}

function resetRitual() {
    ui.cosmicInput.value = '';
    ui.psychicInput.value = '';
    ui.alchemicalInput.value = '';
    const concept = document.getElementById('combined-concept');
    if (concept) concept.classList.remove('visible');
    showScreen('start');
}

function createCardHTML(card, isFinal = false) {
    return `
        <div class="card" data-id="${card.id}">
            <div class="card-inner">
                <div class="card-face card-back">
                    <div class="card-back-inner">
                        <div class="card-back-t">T</div>
                    </div>
                </div>
                <div class="card-face card-front">
                    <div class="card-front-inner" style="border-color: ${card.color};">
                        <div class="card-num-circle" style="color: ${card.color}; border-color: ${card.color}">${card.id}</div>
                        <div class="card-symbol-circle" style="color: ${card.color}; border-color: ${card.color}">${card.symbol}</div>
                        
                        <div class="schematic-human">
                            <div class="human-arms"></div>
                            <div class="human-legs"></div>
                            <div class="chakra chakra-1"></div>
                            <div class="chakra chakra-2"></div>
                            <div class="chakra chakra-3"></div>
                            <div class="chakra chakra-4"></div>
                            <div class="chakra chakra-5"></div>
                        </div>
                        
                        <div class="card-text-container">
                            <div class="card-title-text" style="color: ${card.color}; font-weight: bold;">${card.title}</div>
                            <div class="card-type-text">${card.type}</div>
                        </div>
                        
                        ${isFinal ? `<div class="card-meaning-text">${card.meaning}</div>` : ''}
                        
                        <div class="card-bottom-circle" style="color: ${card.color}; border-color: ${card.color}">${card.id}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function dealCards() {
    ui.row1.innerHTML = '';
    ui.row2.innerHTML = '';
    ui.row1.classList.remove('discarding');
    ui.row2.classList.remove('discarding');

    const half = Math.ceil(activeCards.length / 2);
    const half1 = activeCards.slice(0, half);
    const half2 = activeCards.slice(half);

    half1.forEach((card, idx) => {
        setTimeout(() => {
            ui.row1.insertAdjacentHTML('beforeend', createCardHTML(card));
        }, idx * 50);
    });

    half2.forEach((card, idx) => {
        setTimeout(() => {
            ui.row2.insertAdjacentHTML('beforeend', createCardHTML(card));
        }, (idx + half1.length) * 50);
    });
}

function selectRow(rowNum) {
    // Prevent multiple clicks while animating
    if (ui.row1.classList.contains('discarding') || ui.row2.classList.contains('discarding')) return;

    const keptRow = rowNum === 1 ? ui.row1 : ui.row2;
    const discardedRow = rowNum === 1 ? ui.row2 : ui.row1;

    // Discard animation
    discardedRow.classList.add('discarding');

    // Determine kept cards by extracting from DOM or matching activeCards
    const half = Math.ceil(activeCards.length / 2);
    activeCards = rowNum === 1 ? activeCards.slice(0, half) : activeCards.slice(half);

    setTimeout(() => {
        if (activeCards.length <= 3) {
            showFinalResult();
        } else {
            // Shuffle again and split
            activeCards = shuffle(activeCards);
            dealCards();
        }
    }, 800); // Wait for discard animation
}

function showFinalResult() {
    showScreen('result');
    ui.finalCards.innerHTML = '';
    
    activeCards.forEach((card, idx) => {
        ui.finalCards.insertAdjacentHTML('beforeend', createCardHTML(card, true));
    });

    // Animate flip sequentially
    setTimeout(() => {
        const finalCardEls = ui.finalCards.querySelectorAll('.card');
        finalCardEls.forEach((el, idx) => {
            setTimeout(() => {
                el.classList.add('flipped');
            }, idx * 400);
        });
    }, 500);

    // Show combined concept after all flips
    setTimeout(() => {
        generateCombinedConcept();
    }, 500 + (activeCards.length * 400) + 600);
}

function generateCombinedConcept() {
    const container = document.getElementById('combined-concept');
    if (!container || activeCards.length === 0) return;
    
    let text = "<h3>Lectura de la Pregunta Triple</h3>";
    
    if (activeCards.length === 1) {
        text += `<p>Las tres esferas de tu ser han cristalizado en una única fuerza: <strong>${activeCards[0].title}</strong>. Esto indica una alineación total entre mente, emoción y materia.</p>`;
        text += `<p><em>${activeCards[0].meaning}</em></p>`;
    } else if (activeCards.length >= 2) {
        const c1 = activeCards[0];
        const c2 = activeCards[1];
        const c3 = activeCards[2] || activeCards[1];

        text += `<p><strong>Nivel Cósmico (Mente):</strong> <em>"${intentionTriple.cosmic}"</em><br>
                 Es influenciado por <strong>${c1.title}</strong> (${c1.type}): ${c1.meaning}</p>`;
                 
        text += `<p><strong>Nivel Psíquico (Emoción):</strong> <em>"${intentionTriple.psychic}"</em><br>
                 Es influenciado por <strong>${c2.title}</strong> (${c2.type}): ${c2.meaning}</p>`;
                 
        if (activeCards.length === 3) {
            text += `<p><strong>Nivel Alquímico (Materia):</strong> <em>"${intentionTriple.alchemical}"</em><br>
                     Es influenciado por <strong>${c3.title}</strong> (${c3.type}): ${c3.meaning}</p>`;
        } else {
            text += `<p><strong>Nivel Alquímico (Materia):</strong> <em>"${intentionTriple.alchemical}"</em><br>
                     La energía se condensa conjuntamente en el plano físico mediante la misma fuerza emocional.</p>`;
        }
    }

    container.innerHTML = text;
    container.classList.add('visible');
}

// Initialize the application
init();
