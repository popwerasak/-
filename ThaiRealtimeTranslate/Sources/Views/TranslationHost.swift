import SwiftUI
import Translation

/// `.translationTask` is a view modifier, so `LiveTranslator` (a plain
/// ObservableObject) needs an invisible host view to attach it to. Embed
/// this anywhere in the view hierarchy alongside the visible UI.
struct TranslationHost: View {
    @ObservedObject var translator: LiveTranslator

    var body: some View {
        Color.clear
            .translationTask(translator.configuration) { session in
                await translator.run(session: session)
            }
    }
}
