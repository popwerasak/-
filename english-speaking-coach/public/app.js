const state = {
    isRecording: false,
    thaiText: '',
    englishText: '',
};

const micBtn = document.getElementById('micBtn');
const micStatusText = document.getElementById('micStatusText');
const textInput = document.getElementById('textInput');
const sendTextBtn = document.getElementById('sendTextBtn');

const resultContainer = document.getElementById('resultContainer');
const thaiOutput = document.getElementById('thaiOutput');

const loadingIndicator = document.getElementById('loadingIndicator');

const englishResultCard = document.getElementById('englishResultCard');
const englishOutput = document.getElementById('englishOutput');
const replayBtn = document.getElementById('replayBtn');
const replayBtnText = document.getElementById('replayBtnText');
const copyBtn = document.getElementById('copyBtn');
const rateSelect = document.getElementById('rateSelect');
const historyList = document.getElementById('historyList');
const engineBadge = document.getElementById('engineBadge');

const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');
const toastIcon = document.getElementById('toastIcon');

let recognition = null;
let toastTimeout = null;

// ---------- Speech recognition (Thai voice input) ----------

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast('เบราว์เซอร์นี้ไม่รองรับการพูดสั่งงาน กรุณาใช้ Chrome หรือ Edge (พิมพ์แทนได้)', 'warning');
        micBtn.disabled = true;
        micBtn.classList.add('opacity-50', 'cursor-not-allowed');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'th-TH';

    recognition.onstart = () => {
        state.isRecording = true;
        micBtn.classList.add('mic-pulse', 'bg-red-500', 'hover:bg-red-600');
        micBtn.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
        micBtn.innerHTML = '<i class="fa-solid fa-stop"></i>';
        micStatusText.textContent = 'กำลังฟัง... (กดเพื่อหยุด)';
        textInput.disabled = true;
    };

    recognition.onresult = (event) => {
        let interim = '';
        let final = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                final += event.results[i][0].transcript;
            } else {
                interim += event.results[i][0].transcript;
            }
        }
        if (interim) textInput.value = interim;
        if (final) {
            textInput.value = final;
            state.thaiText = final;
        }
    };

    recognition.onerror = (event) => {
        stopRecordingUi();
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
            showToast('เกิดข้อผิดพลาดในการรับเสียง: ' + event.error, 'error');
        }
    };

    recognition.onend = () => {
        const wasRecording = state.isRecording;
        stopRecordingUi();
        if (wasRecording) {
            const text = state.thaiText || textInput.value;
            if (text.trim()) processInput(text.trim());
        }
    };
}

function toggleRecording() {
    if (!recognition) return;
    if (state.isRecording) {
        recognition.stop();
        return;
    }
    state.thaiText = '';
    textInput.value = '';
    try {
        recognition.start();
    } catch (e) {
        recognition.stop();
        setTimeout(() => recognition.start(), 400);
    }
}

function stopRecordingUi() {
    state.isRecording = false;
    micBtn.classList.remove('mic-pulse', 'bg-red-500', 'hover:bg-red-600');
    micBtn.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
    micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
    micStatusText.textContent = 'แตะไมค์เพื่อพูดภาษาไทย';
    textInput.disabled = false;
}

// ---------- Translation (backend) ----------

async function translateToEnglish(thaiText) {
    const res = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text: thaiText }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `เกิดข้อผิดพลาด (${res.status})`);
    }
    const data = await res.json();
    return data.english;
}

// ---------- Speech synthesis (English playback, built into the browser) ----------

function speakEnglish(text) {
    if (!('speechSynthesis' in window)) {
        showToast('เบราว์เซอร์นี้ไม่รองรับการอ่านออกเสียง', 'error');
        return;
    }
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'en-US';
    utter.rate = parseFloat(rateSelect.value);

    const voices = window.speechSynthesis.getVoices();
    const enVoice = voices.find((v) => v.lang === 'en-US') || voices.find((v) => v.lang?.startsWith('en'));
    if (enVoice) utter.voice = enVoice;

    replayBtn.disabled = true;
    replayBtnText.textContent = 'กำลังพูด...';
    utter.onend = () => {
        replayBtn.disabled = false;
        replayBtnText.textContent = 'ฟังซ้ำ';
    };
    utter.onerror = () => {
        replayBtn.disabled = false;
        replayBtnText.textContent = 'ฟังซ้ำ';
    };

    window.speechSynthesis.speak(utter);
}

// ---------- History (saved locally in this browser) ----------

function loadHistory() {
    try {
        return JSON.parse(localStorage.getItem('engPraxHistory') || '[]');
    } catch {
        return [];
    }
}

function saveHistory(list) {
    localStorage.setItem('engPraxHistory', JSON.stringify(list.slice(0, 50)));
}

function addHistory(thai, english) {
    const list = loadHistory();
    list.unshift({ thai, english, ts: Date.now() });
    saveHistory(list);
    renderHistory();
}

function renderHistory() {
    const list = loadHistory();
    historyList.innerHTML = '';
    if (list.length === 0) {
        historyList.innerHTML = '<li class="text-sm text-gray-400">ยังไม่มีประวัติ ลองพูดหรือพิมพ์ประโยคแรกดูสิ</li>';
        return;
    }
    for (const item of list) {
        const li = document.createElement('li');
        li.className = 'history-item bg-white rounded-xl shadow-sm px-4 py-3 flex items-center justify-between cursor-pointer transition-colors';
        li.innerHTML = `
            <div class="min-w-0 pr-3">
                <p class="text-sm text-gray-500 truncate">${escapeHtml(item.thai)}</p>
                <p class="text-base font-semibold text-gray-900 truncate">${escapeHtml(item.english)}</p>
            </div>
            <i class="fa-solid fa-volume-high text-indigo-400 flex-shrink-0"></i>
        `;
        li.addEventListener('click', () => speakEnglish(item.english));
        historyList.appendChild(li);
    }
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ---------- Main flow ----------

async function processInput(text) {
    if (!text.trim()) return;

    resultContainer.classList.remove('hidden');
    resultContainer.classList.add('flex');
    thaiOutput.textContent = text;

    englishResultCard.classList.add('hidden');
    loadingIndicator.classList.remove('hidden');
    loadingIndicator.classList.add('flex');

    try {
        const english = await translateToEnglish(text);
        state.englishText = english;
        englishOutput.textContent = english;

        loadingIndicator.classList.add('hidden');
        loadingIndicator.classList.remove('flex');
        englishResultCard.classList.remove('hidden');

        speakEnglish(english);
        addHistory(text, english);
    } catch (err) {
        loadingIndicator.classList.add('hidden');
        loadingIndicator.classList.remove('flex');
        showToast('แปลไม่สำเร็จ: ' + err.message, 'error');
    }
}

// ---------- Toast ----------

function showToast(message, type = 'info') {
    toastMessage.textContent = message;

    toast.classList.remove('bg-gray-900', 'bg-red-600', 'bg-green-600', 'bg-yellow-600');
    if (type === 'error') {
        toast.classList.add('bg-red-600');
        toastIcon.className = 'fa-solid fa-circle-exclamation';
    } else if (type === 'success') {
        toast.classList.add('bg-green-600');
        toastIcon.className = 'fa-solid fa-check-circle';
    } else if (type === 'warning') {
        toast.classList.add('bg-yellow-600');
        toastIcon.className = 'fa-solid fa-triangle-exclamation';
    } else {
        toast.classList.add('bg-gray-900');
        toastIcon.className = 'fa-solid fa-info-circle';
    }

    toast.classList.remove('toast-enter', 'toast-exit-active');
    toast.classList.add('toast-enter-active');

    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        toast.classList.remove('toast-enter-active');
        toast.classList.add('toast-exit-active');
        setTimeout(() => {
            toast.classList.remove('toast-exit-active');
            toast.classList.add('toast-enter');
        }, 300);
    }, 3000);
}

// ---------- Wire up events ----------

micBtn.addEventListener('click', toggleRecording);

sendTextBtn.addEventListener('click', () => {
    const text = textInput.value.trim();
    if (text) {
        if (state.isRecording) recognition.stop();
        processInput(text);
    }
});

textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const text = textInput.value.trim();
        if (text) {
            if (state.isRecording) recognition.stop();
            processInput(text);
        }
    }
});

replayBtn.addEventListener('click', () => {
    if (state.englishText) speakEnglish(state.englishText);
});

copyBtn.addEventListener('click', () => {
    if (!state.englishText) return;
    navigator.clipboard.writeText(state.englishText).then(() => showToast('คัดลอกแล้ว', 'success'));
});

fetch('/api/health')
    .then((r) => r.json())
    .then((data) => {
        engineBadge.textContent = data.engine === 'claude' ? 'Powered by Claude' : 'Free translation engine';
    })
    .catch(() => {});

initSpeechRecognition();
renderHistory();
