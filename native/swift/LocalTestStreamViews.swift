import SwiftUI
import UIKit

struct LocalTestStreamEditor: View {
    @ObservedObject var store: LocalTestStreamStore
    @Environment(\.dismiss) private var dismiss
    @State private var draft: LocalTestStream
    init(store: LocalTestStreamStore) {
        self.store = store; _draft = State(initialValue: store.value)
    }
    var body: some View {
        Form {
            Section {
                Toggle("Show local test stream", isOn: $draft.enabled)
                Text("Appears separately at the top of your followed list. Uses local artwork and a placeholder, with no stream connection or audio.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            Section("Channel and stream") {
                TextField("Username", text: $draft.username).textInputAutocapitalization(.never).autocorrectionDisabled()
                TextField("Channel name", text: $draft.name)
                TextField("Stream title", text: $draft.title, axis: .vertical).lineLimit(2...8)
                TextField("Category", text: $draft.category)
                TextField("Tags, separated by commas", text: $draft.tags, axis: .vertical)
                Toggle("Live", isOn: $draft.live)
                Toggle("Verified badge", isOn: $draft.verified)
                Stepper("Viewers: \(draft.viewers)", value: $draft.viewers, in: 0...999999)
            }
            Section("Content warning") {
                Toggle("Marked content", isOn: $draft.marked)
                if draft.marked {
                    TextField("Content labels, separated by commas", text: $draft.labels, axis: .vertical)
                    Text("Uses the normal warning and thumbnail preferences. Re-enable Show marked stream warnings in Player settings to repeat a test.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            Section("Simulated playback status") {
                Picker("Status", selection: $draft.status) {
                    Text("Ready").tag(LocalTestStream.Status.ready)
                    Text("Loading").tag(LocalTestStream.Status.loading)
                    Text("Buffering").tag(LocalTestStream.Status.buffering)
                }
            }
            Section {
                Button("Remove local test stream", role: .destructive) { store.remove(); dismiss() }
                Text("Local entries are not Twitch follows or evidence of real playback. Their metadata is excluded from diagnostic exports.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Local test stream").navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .confirmationAction) {
            Button("Save") { store.save(draft); dismiss() }.disabled(!DevelopmentTools.enabled)
        } }
    }
}

// Bundled-in-code artwork; never an image URL or a remote preview.
@MainActor enum LocalTestArtwork {
    static let thumbnail = image(avatar: false)
    static let avatar = image(avatar: true)
    private static func image(avatar: Bool) -> UIImage {
        let size = avatar ? CGSize(width: 80, height: 80) : CGSize(width: 320, height: 180)
        return UIGraphicsImageRenderer(size: size).image { context in
            UIColor.systemIndigo.setFill(); context.fill(CGRect(origin: .zero, size: size))
            let side: CGFloat = avatar ? 44 : 64
            UIImage(systemName: avatar ? "person.crop.circle.fill" : "testtube.2")?
                .withTintColor(.white, renderingMode: .alwaysOriginal)
                .draw(in: CGRect(x: (size.width - side) / 2, y: (size.height - side) / 2, width: side, height: side))
        }
    }
}

struct LocalTestMedia: View {
    var body: some View {
        ZStack {
            Color.indigo
            VStack(spacing: 8) {
                Image(systemName: "testtube.2").font(.title)
                Text("Local test stream").font(.headline)
                Text("No video or audio").font(.caption)
            }.foregroundStyle(.white)
        }
    }
}
