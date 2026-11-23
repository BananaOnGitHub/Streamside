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
    @State private var viewerFile: ProfileArtworkFile?
    @State private var preparingViewer = false
    @State private var viewerError = false

    func body(content: Content) -> some View {
        artwork(content)
            .onChange(of: url) { _ in
                viewerFile = nil
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
                .fullScreenCover(item: $viewerFile) { file in
                    ProfileArtworkViewer(file: file)
                }
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
        viewerFile = loaded
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

// The profile navigation bar is hidden. Give the image preview its own
// controls outside Quick Look's content view so sharing and closing stay visible.
private struct ProfileArtworkViewer: View {
    let file: ProfileArtworkFile
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button { dismiss() } label: {
                    Text("Done").frame(minWidth: 44, minHeight: 44)
                }
                .accessibilityIdentifier("profile.artwork-done")
                Spacer()
                Text(file.fileURL.deletingPathExtension().lastPathComponent)
                    .font(.headline).lineLimit(1)
                Spacer()
                ShareLink(item: file.fileURL) {
                    Image(systemName: "square.and.arrow.up").frame(width: 44, height: 44)
                }
                .accessibilityLabel("Share")
                .accessibilityIdentifier("profile.artwork-share")
            }
            .padding(.horizontal, 16)
            .frame(minHeight: 48)
            .background(Color(uiColor: .systemBackground))
            ProfileArtworkCanvas(file: file).frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

private struct ProfileArtworkCanvas: UIViewControllerRepresentable {
    let file: ProfileArtworkFile

    @MainActor final class Source: NSObject, QLPreviewControllerDataSource {
        let file: ProfileArtworkFile
        init(file: ProfileArtworkFile) { self.file = file }

        func numberOfPreviewItems(in controller: QLPreviewController) -> Int { 1 }

        func previewController(_ controller: QLPreviewController, previewItemAt index: Int) -> any QLPreviewItem {
            file.fileURL as NSURL
        }
    }

    func makeCoordinator() -> Source { Source(file: file) }

    func makeUIViewController(context: Context) -> QLPreviewController {
        let preview = QLPreviewController()
        preview.dataSource = context.coordinator
        return preview
    }

    func updateUIViewController(_ controller: QLPreviewController, context: Context) {}
}
