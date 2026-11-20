import Combine
import SwiftUI
import UIKit

private struct QuickLookDetails: View {
    let channel: FollowedChannel
    @ObservedObject var services: NativeServices
    let profile: () -> Void
    private var current: FollowedChannel { services.presentationChannels.first { $0.id == channel.id } ?? channel }
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button(action: profile) {
                HStack(spacing: 10) {
                RemoteChannelImage(url: current.avatarURL, images: services.images, generation: services.imageGeneration, localImage: current.localTest == nil ? nil : LocalTestArtwork.avatar, avatar: true)
                    .frame(width: 36, height: 36).clipShape(Circle())
                    .overlay { LiveRing(clock: services.clock) }
                VerifiedChannelName(channel: current).font(.headline)
                }
            }.buttonStyle(.plain).accessibilityLabel("View " + current.displayName + " profile")
            Text(current.title.isEmpty ? "Live stream" : current.title)
                .font(.subheadline).fixedSize(horizontal: false, vertical: true)
            Text(current.category.isEmpty ? "Category unavailable" : current.category)
                .font(.subheadline).foregroundStyle(.secondary)
            if !current.tags.isEmpty { AllStreamTags(tags: current.tags) }
        }
    }
}

private struct QuickLookContent: View {
    let width: CGFloat
    let detailsHeight: CGFloat
    let details: QuickLookDetails
    @ObservedObject var playback: TheatrePlayback
    @ObservedObject var services: NativeServices
    let account: StreamsideAccount?
    let cancel: () -> Void
    var body: some View {
        QuickLookPanel(width: width, detailsHeight: detailsHeight) {
            if let gate = playback.contentGate {
                MarkedContentWarning(gate: gate)
            } else if playback.localTest != nil {
                LocalTestMedia()
            } else if let native = playback.native {
                PassivePlayerSurface(surface: native.view, topCornerRadius: 24)
                    .overlay(alignment: .bottomTrailing) {
                        Image(systemName: "speaker.slash.fill").font(.system(size: 10, weight: .medium))
                            .foregroundStyle(.white).padding(5)
                            .background(.black.opacity(0.4), in: Capsule()).padding(7)
                            .accessibilityLabel("Muted live preview").allowsHitTesting(false)
                    }
                    .accessibilityIdentifier("quicklook.video")
            }
        } details: { details } status: {
            if playback.contentGate == nil { PreviewPlaybackStatus(phase: playback.phase, message: playback.message) }
        }
        .onChange(of: services.state.account) { if $0 != account { cancel() } }
        .onChange(of: services.state.session) { if $0 != .authenticated { cancel() } }
        .task {
            while !Task.isCancelled {
                playback.update()
                if playback.error == 1 { cancel(); return }
                do { try await Task.sleep(nanoseconds: 250_000_000) } catch { return }
            }
        }
    }
}

@MainActor
enum NativeQuickLook {
    static func session(channel: FollowedChannel, services: NativeServices, source: UIView,
                        claim: @escaping (UUID) -> Bool, release: @escaping (UUID) -> Void,
                        handoff: @escaping (TheatrePlayback) -> Bool, profile: @escaping () -> Bool) -> ContextPreviewSession {
        let playback = TheatrePlayback(channel: channel.username, preview: true, localTest: channel.localTest)
        playback.setMuted(true) // Intent precedes authorization and IVS load/play.
        let account = services.state.account
        weak var transaction: ContextPreviewSession?
        playback.bindContentOwner(valid: {
            UIApplication.shared.applicationState == .active && SSNNavigationPermitted() &&
            services.state.session == .authenticated && services.state.account == account
        }, close: { transaction?.cancel() })
        services.prepareContentGate(channel, playback: playback)
        let windowSize = source.window?.bounds.size ?? CGSize(width: 390, height: 700)
        let width = max(1, min(380, windowSize.width - 32))
        let maximumHeight = max(width * 9 / 16 + 80, min(560, windowSize.height - 220))
        let details = QuickLookDetails(channel: channel, services: services, profile: { transaction?.activateProfile?() })
        // Reserve a normal status row even if the warning currently hides it.
        // The measured card height stays stable when loading starts after consent.
        let measure = UIHostingController(rootView: VStack(spacing: 0) {
            details.padding(16)
            PreviewPlaybackStatus(phase: 4, message: "Buffering…")
        })
        let natural = measure.sizeThatFits(in: CGSize(width: width, height: 10000)).height
        let height = min(ceil(natural), maximumHeight - width * 9 / 16)
        let content = UIHostingController(rootView: QuickLookContent(width: width, detailsHeight: height,
            details: details, playback: playback, services: services, account: account, cancel: { transaction?.cancel() }))
        let preview = QuickLookController(content: content, size: CGSize(width: width, height: width * 9 / 16 + height))
        let session = ContextPreviewSession(controller: preview, claim: claim, release: release, valid: {
            UIApplication.shared.applicationState == .active && services.state.session == .authenticated &&
                services.state.account == account && playback.native?.errorCode != 1
        }, start: playback.start, stop: playback.stop, handoff: { handoff(playback) }, profile: profile)
        session.videoTapAvailability = playback.$contentGate.map { $0 == nil }.eraseToAnyPublisher()
        transaction = session
        return session
    }
}
