import SwiftUI

struct ContentView: View {
    @StateObject private var audioInput = AudioInputManager()
    @StateObject private var speech = SpeechRecognizer()
    @StateObject private var translator = LiveTranslator()

    @State private var sourceLanguage: SourceLanguage = .english
    @State private var isRunning = false
    @State private var showPermissionAlert = false
    @State private var history: [HistoryEntry] = []

    struct HistoryEntry: Identifiable {
        let id = UUID()
        let source: String
        let translated: String
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Picker("ภาษาต้นทาง", selection: $sourceLanguage) {
                    ForEach(SourceLanguage.allCases) { lang in
                        Text(lang.displayNameThai).tag(lang)
                    }
                }
                .pickerStyle(.segmented)
                .disabled(isRunning)
                .onChange(of: sourceLanguage) { _, newValue in
                    translator.configure(source: newValue.translationLanguage, target: TargetLanguage.thai)
                }

                micPicker

                partialTranscriptView

                historyView

                if let status = speech.statusMessage {
                    Text(status)
                        .font(.caption)
                        .foregroundStyle(.orange)
                        .multilineTextAlignment(.center)
                }
                if let err = translator.lastError {
                    Text(err)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.center)
                }

                startStopButton
            }
            .padding()
            .navigationTitle("แปลภาษาเรียลไทม์ → ไทย")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                translator.configure(source: sourceLanguage.translationLanguage, target: TargetLanguage.thai)
                speech.onFinalSegment = { text in
                    translator.enqueue(text)
                }
                translator.onTranslated = { source, translated in
                    history.append(HistoryEntry(source: source, translated: translated))
                }
            }
            .background(TranslationHost(translator: translator))
            .alert("ต้องได้รับสิทธิ์ไมโครโฟนและการรู้จำเสียง", isPresented: $showPermissionAlert) {
                Button("ตกลง", role: .cancel) {}
            } message: {
                Text("กรุณาเปิดสิทธิ์ในการตั้งค่า iPhone > ความเป็นส่วนตัวและความปลอดภัย")
            }
        }
    }

    private var micPicker: some View {
        Picker("ไมโครโฟน", selection: Binding(
            get: { audioInput.selectedInputUID ?? "auto" },
            set: { audioInput.selectedInputUID = $0 == "auto" ? nil : $0 }
        )) {
            Text("อัตโนมัติ (\(audioInput.currentInputName))").tag("auto")
            ForEach(audioInput.availableInputs, id: \.uid) { port in
                Text(port.portName).tag(port.uid)
            }
        }
        .disabled(isRunning)
    }

    private var partialTranscriptView: some View {
        Text(speech.partialText.isEmpty ? "…" : speech.partialText)
            .font(.subheadline)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, minHeight: 40, alignment: .leading)
            .padding(.horizontal, 4)
    }

    private var historyView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    ForEach(history) { entry in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(entry.source)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                            Text(entry.translated)
                                .font(.title3.bold())
                        }
                        .id(entry.id)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.vertical)
            }
            .onChange(of: history.count) { _, _ in
                guard let last = history.last?.id else { return }
                withAnimation { proxy.scrollTo(last, anchor: .bottom) }
            }
        }
    }

    private var startStopButton: some View {
        Button(action: toggleListening) {
            Label(
                isRunning ? "หยุดฟัง" : "เริ่มฟังและแปล",
                systemImage: isRunning ? "stop.circle.fill" : "mic.circle.fill"
            )
            .font(.title2)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
        }
        .buttonStyle(.borderedProminent)
        .tint(isRunning ? .red : .accentColor)
    }

    private func toggleListening() {
        if isRunning {
            speech.stop()
            isRunning = false
            return
        }

        Task {
            let granted = await speech.requestPermissions()
            guard granted else {
                showPermissionAlert = true
                return
            }
            do {
                try speech.start(locale: sourceLanguage.speechLocale, preferredInputUID: audioInput.selectedInputUID)
                isRunning = true
            } catch {
                speech.statusMessage = "เริ่มไม่สำเร็จ: \(error.localizedDescription)"
            }
        }
    }
}

#Preview {
    ContentView()
}
