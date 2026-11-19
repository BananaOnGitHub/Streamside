import SwiftUI

// The production editor/store, isolated from any donor/account services.
struct LocalTestEditorFixture: View {
    @StateObject private var store: LocalTestStreamStore
    init() {
        let name = "dev.streamside.local-editor-fixture"
        let defaults = UserDefaults(suiteName: name)!
        defaults.removePersistentDomain(forName: name)
        _store = StateObject(wrappedValue: LocalTestStreamStore(defaults: defaults))
    }
    var body: some View {
        NavigationStack {
            List {
                NavigationLink("Local test stream") { LocalTestStreamEditor(store: store) }
                if let channel = store.channel {
                    Text(channel.displayName).accessibilityIdentifier("local-fixture-name")
                } else { Text("No local test stream") }
            }
        }
    }
}
