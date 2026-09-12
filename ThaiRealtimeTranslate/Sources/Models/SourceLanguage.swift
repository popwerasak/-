import Foundation
import Translation

/// Languages the app can listen to and translate from. Target is always Thai.
enum SourceLanguage: String, CaseIterable, Identifiable, Hashable {
    case english
    case korean
    case japanese

    var id: String { rawValue }

    var displayNameThai: String {
        switch self {
        case .english: return "อังกฤษ"
        case .korean: return "เกาหลี"
        case .japanese: return "ญี่ปุ่น"
        }
    }

    /// Locale used by SFSpeechRecognizer for speech-to-text.
    var speechLocale: Locale {
        switch self {
        case .english: return Locale(identifier: "en-US")
        case .korean: return Locale(identifier: "ko-KR")
        case .japanese: return Locale(identifier: "ja-JP")
        }
    }

    /// Language used by the Translation framework.
    var translationLanguage: Locale.Language {
        switch self {
        case .english: return Locale.Language(identifier: "en")
        case .korean: return Locale.Language(identifier: "ko")
        case .japanese: return Locale.Language(identifier: "ja")
        }
    }
}

enum TargetLanguage {
    static let thai = Locale.Language(identifier: "th")
}
