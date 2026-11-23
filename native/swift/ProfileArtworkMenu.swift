import SwiftUI
import UIKit
import QuickLook

struct ProfileArtworkMenu: ViewModifier {
    enum Kind: Equatable {
        case banner, avatar

        var title: String { self == .banner ? "Profile banner" : "Profile picture" }
        var identifier: String { self == .banner ? "profile.banner" : "profile.avatar" }
    }

    let url: URL?
    let kind: Kind
    let images: ChannelImageCache
    let previewSize: CGSize
    @State private var file: ProfileArtworkFile?
    @State private var viewerURL: URL?
    @State private var preparingViewer = false
    @State private var viewerError = false

    func body(content: Content) -> some View {
        artwork(content)
            .onChange(of: url) { _ in
                viewerURL = nil
                preparingViewer = false
                file = nil
            }
    }

    @ViewBuilder private func artwork(_ content: Content) -> some View {
        if let url, ChannelImagePolicy.allowed(url) {
            content
                .accessibilityElement(children: .ignore)
                .accessibilityHidden(false)
                .accessibilityLabel(kind.title)
                .accessibilityIdentifier(kind.identifier)
                .accessibilityAddTraits(.isImage)
                .accessibilityAction(named: "Open image") { openImage(url) }
                .contextMenu {
                    Button { openImage(url) } label: { Label("Open image", systemImage: "arrow.up.right") }
                } preview: {
                    ProfileArtworkPreview(url: url, kind: kind, images: images, size: previewSize, file: $file)
                }
                .overlay {
                    if preparingViewer { ProgressView().accessibilityLabel("Loading image").allowsHitTesting(false) }
                }
                .quickLookPreview($viewerURL)
                .task(id: preparingViewer ? url : nil) {
                    guard preparingViewer else { return }
                    let loaded = await images.loadProfileArtwork(url: url, avatar: kind == .avatar, title: kind.title)
                    guard !Task.isCancelled else { return }
                    preparingViewer = false
                    file = loaded
                    showImage(loaded)
                }
                .alert("Image unavailable", isPresented: $viewerError) {
                    Button("OK", role: .cancel) {}
                }
        } else {
            content.accessibilityHidden(true).allowsHitTesting(false)
        }
    }

    private func openImage(_ url: URL) {
        if let file, file.source == url { showImage(file) }
        else { preparingViewer = true }
    }

    private func showImage(_ loaded: ProfileArtworkFile?) {
        guard let loaded, QLPreviewController.canPreview(loaded.fileURL as NSURL) else {
            viewerError = true
            return
        }
        viewerURL = loaded.fileURL
    }
}

private struct ProfileArtworkPreview: View {
    let url: URL
    let kind: ProfileArtworkMenu.Kind
    let images: ChannelImageCache
    let size: CGSize
    @Binding var file: ProfileArtworkFile?
    @State private var thumbnail: UIImage?
    @State private var failed = false

    var body: some View {
        let height = min(size.height, size.width * (kind == .avatar ? 1 : 0.55))
        Group {
            if let image = (file?.source == url ? file?.preview : nil) ?? thumbnail {
                Image(uiImage: image).resizable().scaledToFit()
                    .accessibilityLabel(kind.title)
            } else if failed {
                Label("Image unavailable", systemImage: "photo")
            } else {
                ProgressView().accessibilityLabel("Loading image")
            }
        }
        .frame(width: size.width, height: height)
        .background(Color(uiColor: .systemBackground))
        .task(id: url) {
            guard file?.source != url else { return }
            let avatar = kind == .avatar
            let cached = await images.cachedImage(url: url, generation: 0, avatar: avatar)
            guard !Task.isCancelled else { return }
            thumbnail = cached
            let loaded = await images.loadProfileArtwork(url: url, avatar: avatar, title: kind.title)
            guard !Task.isCancelled else { return }
            file = loaded
            failed = loaded == nil
        }
    }
}
