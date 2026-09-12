import AVFoundation
import Combine

/// Tracks available microphone inputs (iPhone mic, AirPods, etc.) and lets the
/// user pin a preferred one. iOS automatically offers a connected AirPods
/// (Pro 2 / 4th gen) mic here once it is paired and in range, since they
/// expose a standard Bluetooth HFP input port.
@MainActor
final class AudioInputManager: NSObject, ObservableObject {
    @Published private(set) var availableInputs: [AVAudioSessionPortDescription] = []
    @Published var selectedInputUID: String?
    @Published private(set) var currentInputName: String = "ไม่ทราบ"

    override init() {
        super.init()
        refresh()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleRouteChange),
            name: AVAudioSession.routeChangeNotification,
            object: nil
        )
    }

    @objc private func handleRouteChange() {
        Task { @MainActor in
            self.refresh()
        }
    }

    func refresh() {
        let session = AVAudioSession.sharedInstance()
        availableInputs = session.availableInputs ?? []
        currentInputName = session.currentRoute.inputs.first?.portName ?? "ไม่ทราบ"
    }

    /// Applies the preferred input to the active audio session. Call after
    /// the session's category has been set and activated.
    func applyPreferredInput() {
        let session = AVAudioSession.sharedInstance()
        guard let uid = selectedInputUID,
              let port = availableInputs.first(where: { $0.uid == uid }) else {
            try? session.setPreferredInput(nil)
            refresh()
            return
        }
        try? session.setPreferredInput(port)
        refresh()
    }
}
