import SwiftUI
import UIKit

// All symbols and popovers are owned native controls. Disabled actions are kept
// explicit until their native service/navigation contracts have been validated.
struct PlayerControls: View {
    let channel: FollowedChannel
    let clock: StreamClock
    let paused: Bool
    let muted: Bool
    let close: () -> Void
    let pause: () -> Void
    let mute: () -> Void
    let interact: () -> Void
    let presentationChanged: (Bool) -> Void
    @AppStorage(PlayerPreferences.glassButtonsKey) private var glassButtons = true
    @State private var sharing = false
    @State private var settings = false

    var body: some View {
        ZStack {
            Color.black.opacity(0.06).allowsHitTesting(false)
            VStack(spacing: 0) {
                HStack(spacing: 2) {
                    control("Close stream", "chevron.down", action: close)
                    Spacer(minLength: 0)
                    control("Create clip — coming later", "movieclapper", disabled: true) {}
                    control("Cast — unavailable", "tv.badge.wifi", disabled: true) {}
                    control("Share stream", "square.and.arrow.up") { sharing = true }
                        .popover(isPresented: $sharing, attachmentAnchor: .rect(.bounds), arrowEdge: .top) {
                            StreamSharePopover(channel: channel, copied: { sharing = false })
                                .presentationCompactAdaptation(.popover)
                                .presentationBackground(.regularMaterial)
                        }
                    control("Player settings", "gearshape") { settings = true }
                        .popover(isPresented: $settings, attachmentAnchor: .rect(.bounds), arrowEdge: .top) {
                            VStack(alignment: .leading, spacing: 14) {
                                Text("Player").font(.headline)
                                PlayerSettingsOptions()
                            }.padding(16).frame(idealWidth: 270, maxWidth: 290)
                                .presentationCompactAdaptation(.popover)
                                .presentationBackground(.regularMaterial)
                        }
                }
                Spacer(minLength: 0)
                control(paused ? "Play" : "Pause", paused ? "play.fill" : "pause.fill", action: pause)
                    .font(.title2)
                Spacer(minLength: 0)
                HStack(spacing: 2) {
                    PlayerLiveInfo(channel: channel, clock: clock)
                    Spacer(minLength: 2)
                    control(muted ? "Unmute stream" : "Mute stream", muted ? "speaker.slash.fill" : "speaker.wave.2.fill", action: mute)
                    control("Full screen — coming later", "arrow.up.left.and.arrow.down.right", disabled: true) {}
                }
            }.padding(6)
        }
        .onChange(of: sharing || settings) { presentationChanged($0) }
        .onDisappear { presentationChanged(false) }
    }

    private func control(_ title: String, _ symbol: String, disabled: Bool = false, action: @escaping () -> Void) -> some View {
        Button { interact(); action() } label: {
            Image(systemName: symbol).font(.system(size: 19, weight: .semibold))
                .frame(width: 44, height: 44)
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.65), radius: 2, y: 1)
                .modifier(PlayerButtonSurface(enabled: glassButtons))
        }
        .buttonStyle(.plain)
        .disabled(disabled)
        .opacity(disabled ? 0.45 : 1)
        .accessibilityLabel(title)
    }
}

private struct PlayerButtonSurface: ViewModifier {
    let enabled: Bool
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @ViewBuilder func body(content: Content) -> some View {
        if !enabled { content }
        else if reduceTransparency { content.background(.black.opacity(0.9), in: Circle()) }
        else if #available(iOS 26.0, *) { content.glassEffect(.regular.interactive(), in: Circle()) }
        else { content.background(.ultraThinMaterial, in: Circle()) }
    }
}

private struct PlayerLiveInfo: View {
    let channel: FollowedChannel
    @ObservedObject var clock: StreamClock
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    private var elapsed: Int? { channel.startedAt.map { StreamElapsed.seconds(startedAt: $0, now: clock.now) } }
    private var label: some View {
        HStack(spacing: 6) {
            Circle().fill(channel.isLive ? Color.red : Color.secondary).frame(width: 6, height: 6).accessibilityHidden(true)
            Text(elapsed.map { StreamElapsed.label(seconds: $0) } ?? (channel.isLive ? "LIVE" : "Offline"))
                .monospacedDigit()
                .contentTransition(reduceMotion ? .identity : .numericText(countsDown: false))
                .animation(reduceMotion ? nil : .easeInOut(duration: 0.2), value: elapsed)
            Image(systemName: "person").accessibilityHidden(true)
            Text(channel.viewerCount.map { $0.formatted(.number.notation(.compactName)) } ?? "—")
                .monospacedDigit()
                .contentTransition(reduceMotion ? .identity : .numericText())
                .animation(reduceMotion ? nil : .easeInOut(duration: 0.2), value: channel.viewerCount)
        }
        .font(.system(size: 12, weight: .medium))
        .foregroundStyle(.white)
        .padding(.horizontal, 9).padding(.vertical, 7)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Live stream")
        .accessibilityValue("\(elapsed.map { StreamElapsed.label(seconds: $0) } ?? "Duration unavailable"), \(channel.viewerCount.map { "\($0) viewers" } ?? "Viewers unavailable")")
    }
    @ViewBuilder var body: some View {
        if reduceTransparency { label.background(.black.opacity(0.9), in: Capsule()) }
        else if #available(iOS 26.0, *) { label.glassEffect(.regular, in: Capsule()) }
        else { label.background(.ultraThinMaterial, in: Capsule()) }
    }
}

private struct StreamSharePopover: View {
    let channel: FollowedChannel
    let copied: () -> Void
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(channel.title.isEmpty ? channel.displayName : channel.title)
                .font(.subheadline.weight(.semibold)).lineLimit(2)
            if let url = StreamShareLink.url(username: channel.username) {
                HStack(alignment: .top, spacing: 8) {
                    Button { UIPasteboard.general.url = url; copied() } label: {
                        choice("Copy link", "doc.on.doc")
                    }
                    ShareLink(item: url) { choice("Share link", "square.and.arrow.up") }
                    Button {} label: { choice("Whisper", "message") }
                        .disabled(true).opacity(0.45)
                        .accessibilityHint("Whispers are not available yet")
                }.buttonStyle(.plain)
            }
        }
        .padding(14).frame(idealWidth: 270, maxWidth: 290)
    }
    private func choice(_ title: String, _ symbol: String) -> some View {
        VStack(spacing: 7) {
            Image(systemName: symbol).font(.title3).frame(width: 44, height: 44)
                .background(.quaternary, in: Circle())
            Text(title).font(.caption).multilineTextAlignment(.center)
        }.frame(maxWidth: .infinity).contentShape(Rectangle())
    }
}

struct PlayerSettingsOptions: View {
    @AppStorage(PlayerPreferences.glassButtonsKey) private var glassButtons = true
    var body: some View { Toggle("Liquid Glass buttons", isOn: $glassButtons) }
}

struct PlayerSettings: View {
    var body: some View {
        Form { Section { PlayerSettingsOptions() } }
            .navigationTitle("Player")
            .navigationBarTitleDisplayMode(.inline)
    }
}
