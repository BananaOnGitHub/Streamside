import SwiftUI
import UIKit

// All symbols and popovers are owned native controls. Disabled actions are kept
// explicit until their native service/navigation contracts have been validated.
struct PlayerControls: View {
    let visible: Bool
    let channel: FollowedChannel
    let clock: StreamClock
    let paused: Bool
    let muted: Bool
    let close: () -> Void
    let pause: () -> Void
    let mute: () -> Void
    let interact: () -> Void
    let presentationChanged: (Bool) -> Void
    var motionSample: PlayerMotionSample? = nil
    // Owned fixture input; normal app callers use the read-only system value.
    var motionReductionOverride: Bool? = nil
    // Only the frame-sampling fixture stretches time; application callers use 1.
    var motionDurationScale = 1.0
    @State private var motionProgress = 0.0
    @State private var motionMounted = true
    @State private var motionRequestedVisible = true
    @State private var motionGeneration: UInt64 = 0
    @State private var motionTask: Task<Void, Never>?
    @AppStorage(PlayerPreferences.glassButtonsKey) private var glassButtons = true
    @AppStorage(PlayerPreferences.animationKey) private var storedAnimation = PlayerControlAnimation.vertical.rawValue
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var sharing = false
    @State private var settings = false

    var body: some View {
        Group {
            if #available(iOS 26.0, *), glassButtons {
                GlassEffectContainer(spacing: 0) { controlLayer }
            } else { controlLayer }
        }
        .onAppear { animateVisibility(visible) }
        .onChange(of: visible) { requested in animateVisibility(requested) }
        .onChange(of: sharing || settings) { presentationChanged($0) }
        .onDisappear {
            motionGeneration &+= 1
            motionTask?.cancel()
            presentationChanged(false)
        }
    }
    private var animationStyle: PlayerControlAnimation {
        PlayerControlAnimation.effective(stored: storedAnimation, reduceMotion: motionReductionOverride ?? reduceMotion)
    }
    private func animateVisibility(_ requested: Bool) {
        motionRequestedVisible = requested
        motionGeneration &+= 1
        let generation = motionGeneration
        motionTask?.cancel()
        let duration = PlayerControlMotion.duration(style: animationStyle) * motionDurationScale
        if requested {
            if motionMounted {
                withAnimation(.linear(duration: duration)) { motionProgress = 1 }
            } else {
                // Mount hidden first; a separate render update prevents a jump.
                withTransaction(Transaction(animation: nil)) { motionMounted = true }
                motionTask = Task { @MainActor in
                    do { try await Task.sleep(nanoseconds: 20_000_000) } catch { return }
                    guard generation == motionGeneration, motionRequestedVisible, !Task.isCancelled else { return }
                    withAnimation(.linear(duration: duration)) { motionProgress = 1 }
                }
            }
        } else if #available(iOS 17.0, *) {
            withAnimation(.linear(duration: duration), completionCriteria: .removed) {
                motionProgress = 0
            } completion: {
                finishHiding(generation: generation)
            }
        } else {
            withAnimation(.linear(duration: duration)) { motionProgress = 0 }
            // iOS 16 lacks animation completion. Allow a final frame before
            // cleanup; a new request cancels this compatibility task.
            motionTask = Task { @MainActor in
                do { try await Task.sleep(nanoseconds: UInt64((duration + 0.1) * 1_000_000_000)) } catch { return }
                guard !Task.isCancelled else { return }
                finishHiding(generation: generation)
            }
        }
    }
    private func finishHiding(generation: UInt64) {
        guard generation == motionGeneration, !motionRequestedVisible else { return }
        withTransaction(Transaction(animation: nil)) { motionMounted = false }
    }
    private func motion(_ region: PlayerControlRegion, size: CGSize) -> PlayerControlMotionEffect {
        PlayerControlMotionEffect(progress: motionProgress, style: animationStyle, region: region,
                                  size: size, sample: motionSample)
    }
    private var controlLayer: some View {
        GeometryReader { geometry in
            if motionMounted {
                ZStack {
                    Color.black.opacity(0.06).modifier(motion(.shade, size: geometry.size)).allowsHitTesting(false)
                    VStack(spacing: 0) {
                        HStack(spacing: 2) {
                            control("Close stream", "chevron.down", id: "close", event: 1, action: close)
                                .modifier(motion(.topLeading, size: geometry.size))
                            Spacer(minLength: 0)
                            topActions.frame(width: 182, height: 44)
                                .modifier(motion(.topTrailing, size: geometry.size))
                        }
                        Spacer(minLength: 0)
                        control(paused ? "Play" : "Pause", paused ? "play.fill" : "pause.fill", id: "pause", event: 2, action: pause)
                            .modifier(motion(.center, size: geometry.size))
                        Spacer(minLength: 0)
                        HStack(spacing: 2) {
                            PlayerLiveInfo(channel: channel, clock: clock)
                                .modifier(motion(.bottomLeading, size: geometry.size))
                                .accessibilityHidden(!visible)
                            Spacer(minLength: 2)
                            HStack(spacing: 2) {
                                control(muted ? "Unmute stream" : "Mute stream", muted ? "speaker.slash.fill" : "speaker.wave.2.fill", id: "mute", event: 3, action: mute)
                                control("Full screen — coming later", "arrow.up.left.and.arrow.down.right", disabled: true) {}
                            }.frame(width: 90, height: 44)
                                .modifier(motion(.bottomTrailing, size: geometry.size))
                        }.frame(height: 44)
                    }.padding(6)
                }
                // Block input now, retaining rendering until exit completion.
                .allowsHitTesting(visible)
                .accessibilityHidden(!visible)
            }
        }
    }
    private var topActions: some View {
        HStack(spacing: 2) {
            control("Create clip — coming later", "movieclapper", grouped: true, disabled: true) {}
            control("Cast — unavailable", "tv.badge.wifi", grouped: true, disabled: true) {}
            control("Share stream", "square.and.arrow.up", id: "share", event: 4, grouped: true) { sharing = true }
                .popover(isPresented: $sharing, attachmentAnchor: .rect(.bounds), arrowEdge: .top) {
                    StreamSharePopover(channel: channel, copied: { sharing = false })
                        .presentationCompactAdaptation(.popover)
                        .presentationBackground(.regularMaterial)
                }
            control("Player settings", "gearshape", id: "settings", event: 5, grouped: true) { settings = true }
                .popover(isPresented: $settings, attachmentAnchor: .rect(.bounds), arrowEdge: .top) {
                    VStack(alignment: .leading, spacing: 14) {
                        Text("Player").font(.headline)
                        PlayerSettingsOptions()
                    }.padding(16).frame(idealWidth: 270, maxWidth: 290)
                        .presentationCompactAdaptation(.popover)
                        .presentationBackground(.regularMaterial)
                }
        }
        .modifier(PlayerActionsSurface(enabled: glassButtons))
    }

    private func control(_ title: String, _ symbol: String, id: String = "unavailable", event: UInt32? = nil, grouped: Bool = false, disabled: Bool = false, action: @escaping () -> Void) -> some View {
        Button { interact(); if let event { SSNPlayerControlEvent(event) }; action() } label: {
            Image(systemName: symbol).font(.system(size: 19, weight: .semibold))
                .frame(width: 44, height: 44)
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.65), radius: 2, y: 1)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .frame(width: 44, height: 44)
        .modifier(PlayerButtonSurface(enabled: glassButtons && !grouped))
        .contentShape(Rectangle())
        .accessibilityIdentifier("player." + id)
        .disabled(disabled)
        .opacity(disabled ? 0.45 : 1)
        .accessibilityLabel(title)
        .accessibilityHidden(!visible)
    }
}

// One capsule is drawn around all four actions; individual 44-point buttons
// and their popover anchors remain independent and accessible.
private struct PlayerActionsSurface: ViewModifier {
    let enabled: Bool
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @ViewBuilder func body(content: Content) -> some View {
        if !enabled { content }
        else if reduceTransparency { content.background(.black.opacity(0.9), in: Capsule()) }
        else if #available(iOS 26.0, *) { content.glassEffect(.regular.interactive(), in: Capsule()) }
        else { content.background(.ultraThinMaterial, in: Capsule()) }
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
                    Button { SSNPlayerControlEvent(6); UIPasteboard.general.url = url; copied() } label: {
                        choice("Copy link", "doc.on.doc")
                    }.accessibilityIdentifier("player.copy")
                    ShareLink(item: url) { choice("Share link", "square.and.arrow.up") }
                        .accessibilityIdentifier("player.system-share")
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

struct PlayerAnimationOptions: View {
    @AppStorage(PlayerPreferences.animationKey) private var storedAnimation = PlayerControlAnimation.vertical.rawValue
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private var selection: Binding<String> {
        Binding(get: { PlayerControlAnimation.effective(stored: storedAnimation, reduceMotion: reduceMotion).rawValue },
                set: { storedAnimation = $0 })
    }
    var body: some View {
        Picker("Control animation", selection: selection) {
            ForEach(PlayerControlAnimation.allCases) { style in Text(style.title).tag(style.rawValue) }
        }.disabled(reduceMotion)
        if reduceMotion {
            Text("Reduce Motion is on. Player controls use Fade.").font(.footnote).foregroundStyle(.secondary)
        }
    }
}

struct PlayerSettings: View {
    var body: some View {
        Form {
            Section { PlayerSettingsOptions() }
            Section("Controls") { PlayerAnimationOptions() }
        }
            .navigationTitle("Player")
            .navigationBarTitleDisplayMode(.inline)
    }
}
