import AVFoundation
import Speech

/// Continuously listens on the microphone and streams speech-to-text using
/// SFSpeechRecognizer with `requiresOnDeviceRecognition = true`, so once the
/// on-device model for a language has been downloaded once (needs a brief
/// internet connection the first time), it keeps working fully offline.
///
/// On-device recognition auto-finalizes an utterance after a pause. Each
/// time that happens we hand the finished sentence to `onFinalSegment` and
/// immediately restart listening, so the mic effectively never stops.
@MainActor
final class SpeechRecognizer: NSObject, ObservableObject {
    @Published private(set) var partialText: String = ""
    @Published private(set) var isListening: Bool = false
    @Published var statusMessage: String?

    /// Called on the main actor whenever a full sentence/utterance has been
    /// recognized and is ready to be translated.
    var onFinalSegment: ((String) -> Void)?

    private let audioEngine = AVAudioEngine()
    private var recognizer: SFSpeechRecognizer?
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    private var currentLocale: Locale?
    private var preferredInputUID: String?
    /// Guards against restart loops racing a user-initiated stop().
    private var generation = 0

    func requestPermissions() async -> Bool {
        let speechStatus: SFSpeechRecognizerAuthorizationStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }
        guard speechStatus == .authorized else { return false }

        let micGranted: Bool = await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
        return micGranted
    }

    func start(locale: Locale, preferredInputUID: String?) throws {
        stopEngineAndTask()
        generation += 1
        currentLocale = locale
        self.preferredInputUID = preferredInputUID
        try startInternal(generation: generation)
        isListening = true
    }

    func stop() {
        generation += 1
        isListening = false
        stopEngineAndTask()
    }

    private func startInternal(generation: Int) throws {
        guard let locale = currentLocale else { return }
        guard let recognizer = SFSpeechRecognizer(locale: locale), recognizer.isAvailable else {
            statusMessage = "อุปกรณ์นี้ไม่รองรับการรู้จำเสียงสำหรับภาษานี้"
            return
        }
        self.recognizer = recognizer

        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .spokenAudio, options: [.allowBluetooth, .allowBluetoothA2DP, .duckOthers])
        try session.setActive(true, options: .notifyOthersOnDeactivation)
        if let uid = preferredInputUID, let port = session.availableInputs?.first(where: { $0.uid == uid }) {
            try? session.setPreferredInput(port)
        }

        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        if recognizer.supportsOnDeviceRecognition {
            req.requiresOnDeviceRecognition = true
            statusMessage = nil
        } else {
            statusMessage = "ภาษานี้ยังไม่รองรับการรู้จำเสียงแบบออฟไลน์บนอุปกรณ์นี้ จะต้องใช้อินเทอร์เน็ต"
        }
        self.request = req

        let inputNode = audioEngine.inputNode
        inputNode.removeTap(onBus: 0)
        let format = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            self?.request?.append(buffer)
        }

        audioEngine.prepare()
        try audioEngine.start()

        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            guard let self else { return }
            Task { @MainActor in
                self.handleResult(result, error: error, generation: generation)
            }
        }
    }

    private func handleResult(_ result: SFSpeechRecognitionResult?, error: Error?, generation: Int) {
        guard generation == self.generation, isListening else { return }

        if let result {
            partialText = result.bestTranscription.formattedString
            if result.isFinal {
                let text = result.bestTranscription.formattedString
                partialText = ""
                if !text.isEmpty {
                    onFinalSegment?(text)
                }
                scheduleRestart(generation: generation)
            }
        }

        if error != nil {
            partialText = ""
            scheduleRestart(generation: generation)
        }
    }

    /// On-device recognition tasks end after each finalized utterance (or
    /// error/silence), so we briefly pause and start a fresh task to keep
    /// listening continuously.
    private func scheduleRestart(generation: Int) {
        stopEngineAndTask()
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 250_000_000)
            guard generation == self.generation, isListening else { return }
            try? startInternal(generation: generation)
        }
    }

    private func stopEngineAndTask() {
        task?.cancel()
        task = nil
        request?.endAudio()
        request = nil
        if audioEngine.isRunning {
            audioEngine.stop()
        }
        audioEngine.inputNode.removeTap(onBus: 0)
    }
}
