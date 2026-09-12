import Foundation
import Translation

/// Feeds finalized source-language sentences into Apple's on-device
/// Translation framework and streams back Thai translations. Runs inside a
/// SwiftUI `.translationTask` (see `TranslationHost`), which is what lets it
/// stay fully on-device once the language pack is downloaded.
@MainActor
final class LiveTranslator: ObservableObject {
    @Published private(set) var translatedText: String = ""
    @Published var lastError: String?
    @Published private(set) var configuration: TranslationSession.Configuration?

    /// (originalText, translatedText), called as each translation completes.
    var onTranslated: ((String, String) -> Void)?

    private var textStream: AsyncStream<String> = AsyncStream { _ in }
    private var continuation: AsyncStream<String>.Continuation?

    /// Call whenever the source language (or target) changes; this also
    /// tears down and recreates the pending-text queue.
    func configure(source: Locale.Language, target: Locale.Language) {
        let (stream, continuation) = AsyncStream<String>.makeStream(bufferingPolicy: .unbounded)
        self.textStream = stream
        self.continuation = continuation
        self.configuration = TranslationSession.Configuration(source: source, target: target)
    }

    func enqueue(_ text: String) {
        guard !text.isEmpty else { return }
        continuation?.yield(text)
    }

    /// Entry point invoked by `TranslationHost`'s `.translationTask`.
    func run(session: TranslationSession) async {
        do {
            try await session.prepareTranslation()
            lastError = nil
        } catch {
            lastError = "เตรียมโมเดลแปลภาษาไม่สำเร็จ: \(error.localizedDescription)"
        }

        for await text in textStream {
            do {
                let response = try await session.translate(text)
                translatedText = response.targetText
                onTranslated?(text, response.targetText)
                lastError = nil
            } catch {
                lastError = "แปลไม่สำเร็จ: \(error.localizedDescription)"
            }
        }
    }
}
