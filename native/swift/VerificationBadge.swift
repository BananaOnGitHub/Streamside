import SwiftUI
import UIKit

private final class VerificationBundle: NSObject {}

@MainActor enum VerificationArtwork {
    private static let images: [VerificationStyle: UIImage] = {
        var result: [VerificationStyle: UIImage] = [:]
        for style in VerificationStyle.allCases {
            if let name = style.asset, let url = Bundle(for: VerificationBundle.self).url(forResource: name, withExtension: "png"),
               let image = UIImage(contentsOfFile: url.path) {
                let format = UIGraphicsImageRendererFormat(); format.scale = 3
                result[style] = UIGraphicsImageRenderer(size: CGSize(width: 18, height: 18), format: format).image { _ in
                    image.draw(in: CGRect(x: 0, y: 0, width: 18, height: 18))
                }
            }
        }
        return result
    }()
    static func image(_ style: VerificationStyle) -> UIImage? { images[style] }
}

struct VerificationBadge: View {
    let verified: Bool
    @AppStorage(VerificationStyle.preferenceKey) private var stored = VerificationStyle.twitch.rawValue
    var body: some View {
        let style = VerificationStyle.resolve(stored)
        if verified, style != .off, let image = VerificationArtwork.image(style) {
            Image(uiImage: image).renderingMode(.original).resizable().interpolation(.high).scaledToFit()
                .frame(width: 16, height: 16).fixedSize()
                .accessibilityLabel("Verified channel").accessibilityIdentifier("verification." + style.rawValue)
        }
    }
}

struct VerifiedChannelName: View {
    let channel: FollowedChannel
    var body: some View {
        HStack(spacing: 5) {
            Text(channel.displayName).lineLimit(1)
            VerificationBadge(verified: channel.isVerified)
        }
    }
}

struct GeneralSettings: View {
    @AppStorage(VerificationStyle.preferenceKey) private var stored = VerificationStyle.twitch.rawValue
    var body: some View {
        Form {
            Section {
                Picker("Verified badge", selection: $stored) {
                    ForEach(VerificationStyle.allCases) { style in
                        Label {
                            Text(style.label)
                        } icon: {
                            if let image = VerificationArtwork.image(style) { Image(uiImage: image).renderingMode(.original) }
                            else { Image(systemName: "eye.slash") }
                        }.tag(style.rawValue)
                    }
                }.pickerStyle(.menu).accessibilityIdentifier("verification.style")
            } header: { Label("General", systemImage: "gearshape") }
        }
        .navigationTitle("General").navigationBarTitleDisplayMode(.inline)
        .onAppear { stored = VerificationStyle.resolve(stored).rawValue }
    }
}
