import SwiftUI

// Content and actions are separate surfaces, like a link preview. The details
// size the card naturally and scroll only when the safe-area budget is exceeded.
struct QuickLookPanel<Video: View, Details: View>: View {
    let watch: () -> Void
    let close: () -> Void
    let video: () -> Video
    let details: () -> Details
    init(watch: @escaping () -> Void, close: @escaping () -> Void,
         @ViewBuilder video: @escaping () -> Video, @ViewBuilder details: @escaping () -> Details) {
        self.watch = watch; self.close = close; self.video = video; self.details = details
    }
    @Environment(\.dynamicTypeSize) private var typeSize
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @State private var detailsHeight: CGFloat = 120
    @State private var menuHeight: CGFloat = 112

    var body: some View {
        GeometryReader { geometry in
            let width = max(1, min(420, geometry.size.width - 32))
            let videoHeight = width * 9 / 16
            let detailsLimit = max(1, geometry.size.height - videoHeight - menuHeight - 46)
            ZStack {
                backdrop.contentShape(Rectangle()).onTapGesture(perform: close)
                    .accessibilityLabel("Dismiss stream preview").accessibilityAddTraits(.isButton)
                VStack(alignment: .leading, spacing: 14) {
                    VStack(spacing: 0) {
                        video().frame(width: width, height: videoHeight).clipped()
                        ScrollView {
                            details()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .fixedSize(horizontal: false, vertical: true)
                                .padding(16)
                                .background {
                                    GeometryReader { content in
                                        Color.clear.preference(key: PreviewDetailsHeight.self, value: content.size.height)
                                    }
                                }
                        }
                        .scrollBounceBehavior(.basedOnSize)
                        .frame(height: min(detailsHeight, detailsLimit))
                    }
                    .background(Color(uiColor: .secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
                    .shadow(color: .black.opacity(0.18), radius: 16, y: 8)
                    .accessibilityElement(children: .contain)
                    .accessibilityIdentifier("quicklook.card")
                    actionMenu
                        .frame(width: typeSize.isAccessibilitySize ? width : min(280, width))
                        .background {
                            GeometryReader { content in
                                Color.clear.preference(key: PreviewMenuHeight.self, value: content.size.height)
                            }
                        }
                }
                .frame(width: width)
                .padding(.vertical, 16)
            }
            .onPreferenceChange(PreviewDetailsHeight.self) { detailsHeight = max(1, ceil($0)) }
            .onPreferenceChange(PreviewMenuHeight.self) { menuHeight = max(1, ceil($0)) }
        }
    }
    @ViewBuilder private var backdrop: some View {
        if reduceTransparency {
            Color.black.opacity(0.85).ignoresSafeArea()
        } else {
            Rectangle().fill(.ultraThinMaterial)
                .overlay(Color.black.opacity(0.18)).ignoresSafeArea()
        }
    }
    private var menuRows: some View {
        VStack(spacing: 0) {
            Button(action: watch) {
                Label("Watch stream", systemImage: "play.fill")
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 20).padding(.vertical, 15)
                    .contentShape(Rectangle())
            }
            .accessibilityIdentifier("quicklook.watch")
            Divider().padding(.horizontal, 16)
            Button {} label: {
                Label("View profile", systemImage: "person.fill")
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 20).padding(.vertical, 15)
            }
            .disabled(true).opacity(0.4)
            .accessibilityHint("Not available yet")
        }
        .font(.body)
        .foregroundStyle(.primary)
        .buttonStyle(PreviewActionStyle())
    }
    @ViewBuilder private var actionMenu: some View {
        let shape = RoundedRectangle(cornerRadius: 24, style: .continuous)
        Group {
            if reduceTransparency {
                menuRows.background(Color(uiColor: .secondarySystemBackground), in: shape)
            } else if #available(iOS 26.0, *) {
                menuRows.glassEffect(.regular, in: shape)
            } else {
                menuRows.background(.regularMaterial, in: shape)
            }
        }
        .clipShape(shape)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("quicklook.menu")
    }
}

private struct PreviewActionStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.background(configuration.isPressed ? Color.primary.opacity(0.1) : .clear)
    }
}
private struct PreviewDetailsHeight: PreferenceKey {
    static var defaultValue: CGFloat = 120
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}
private struct PreviewMenuHeight: PreferenceKey {
    static var defaultValue: CGFloat = 112
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}
