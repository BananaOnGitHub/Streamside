import SwiftUI
import UIKit
import Combine

struct StreamsideShell: View {
    @ObservedObject var services: NativeServices
    @State private var settings = false
    @State private var diagnostics = false

    var body: some View {
        NavigationStack {
            List {
                if services.state.session == .authenticated {
                    let feed = FollowedFeed(services.state.channels)
                    Section {
                        if services.state.phase == 3 {
                            ProgressView("Loading followed channels")
                        } else if feed.live.isEmpty {
                            Label("No followed channels are live right now", systemImage: "moon")
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(feed.live) { channel in
                                LiveChannelRow(channel: channel, images: services.images,
                                               generation: services.imageGeneration)
                            }
                        }
                    } header: { Text("Live · \(feed.live.count)") }
                    if !feed.offline.isEmpty {
                        Section {
                            DisclosureGroup("Offline (\(feed.offline.count))") {
                                ForEach(feed.offline) { channel in
                                    OfflineChannelRow(channel: channel, images: services.images,
                                                      generation: services.imageGeneration)
                                }
                            }
                        }
                    }
                } else {
                    Section { AccountPanel(services: services) }
                }
                if let message = services.refreshMessage {
                    Section { Text(message).font(.footnote).foregroundStyle(.secondary) }
                }
                if let error = services.actionError {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .listStyle(.plain)
            .navigationTitle("Followed Streams")
            .navigationBarTitleDisplayMode(.inline)
            .refreshable { await services.refresh() }
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    if services.state.session == .authenticated {
                        Button { settings = true } label: { Label("Account and diagnostics", systemImage: "gearshape") }
                    } else {
                        Button { diagnostics = true } label: { Label("Diagnostics", systemImage: "waveform.path.ecg") }
                    }
                }
            }
            .sheet(isPresented: $settings) { AccountSettings(services: services) }
            .sheet(isPresented: $diagnostics) { DiagnosticsView(services: services, baseline: false) }
            .onChange(of: services.state.session) { session in
                if session == .signedOut { settings = false }
            }
        }
    }
}

private struct AccountPanel: View {
    @ObservedObject var services: NativeServices
    @State private var confirmSignOut = false
    var body: some View {
        Group {
            switch services.state.session {
            case .authenticated:
                if let account = services.state.account {
                    Label {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(account.displayName).font(.headline)
                            Text("@\(account.username)").foregroundStyle(.secondary)
                        }
                    } icon: { Image(systemName: "person.crop.circle") }
                    Button("Refresh") { Task { await services.refresh() } }.disabled(services.state.isBusy)
                    if services.state.canSignOut {
                        Button("Sign out", role: .destructive) { confirmSignOut = true }
                    }
                }
            case .restoring, .checkingAccount: ProgressView("Checking your existing account")
            case .signingOut: ProgressView("Signing out")
            case .signedOut:
                Label("Welcome to Streamside", systemImage: "person.crop.circle").font(.headline)
                Text("You’re signed out. Sign in using Twitch’s existing authentication.")
                    .foregroundStyle(.secondary)
                Button("Sign in") { services.signIn() }.disabled(!services.canSignIn)
                if !services.canSignIn {
                    Text("Waiting for Twitch’s native sign-in screen. See diagnostics if it remains unavailable.")
                        .foregroundStyle(.secondary)
                }
                Button("Check for an existing account") { Task { await services.refresh() } }
            case .failure:
                Text("Your account could not be verified. Check your connection and try again.")
                Button("Check account") { Task { await services.refresh() } }
            case .unavailable:
                Text("Account services are unavailable. Open diagnostics for details.")
            }
        }
        .confirmationDialog("Sign out of Twitch?", isPresented: $confirmSignOut, titleVisibility: .visible) {
            Button("Sign out", role: .destructive) { services.signOut() }
            Button("Cancel", role: .cancel) {}
        } message: { Text("You can sign in again using Twitch’s native authentication screen.") }
    }
}

private struct AccountSettings: View {
    @ObservedObject var services: NativeServices
    @Environment(\.dismiss) private var dismiss
    @State private var diagnostics = false
    var body: some View {
        NavigationStack {
            List {
                Section("Account") { AccountPanel(services: services) }
                Section { Button("Diagnostics") { diagnostics = true } }
            }
            .navigationTitle("Account")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
            .sheet(isPresented: $diagnostics) { DiagnosticsView(services: services, baseline: false) }
        }
    }
}

struct DiagnosticsView: View {
    @ObservedObject var services: NativeServices
    let baseline: Bool
    @Environment(\.dismiss) private var dismiss
    @State private var export: ReportExport?

    private var rootOwnerText: String {
        switch services.rootOwner {
        case 1: return "Streamside SwiftUI"
        case 2: return "Twitch / another controller"
        case 3: return "Missing"
        default: return "Unobserved"
        }
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Status") {
                    Text(services.diagnosticSummary).font(.body.monospaced())
                    Text("Window root: \(rootOwnerText)")
                    if !baseline && services.rootOwner == 2 {
                        Text("Twitch replaced the Streamside interface. Appearance does not identify its runtime; use the entry counts below.")
                    }
                    if baseline {
                        Text("This baseline runs Twitch's original interface and JavaScript runtimes.")
                    }
                }
                Section("Runtime entry counts") {
                    ForEach(services.runtimeCounts) { item in
                        LabeledContent(item.name, value: String(item.count))
                            .font(.body.monospaced())
                    }
                }
                Section {
                    Button("Refresh diagnostics") { services.reloadSnapshot() }
                    Button(baseline ? "Export baseline reports" : "Export native reports") {
                        export = ReportExport(urls: services.exportReports())
                    }
                } footer: {
                    Text("Reports contain counts and build information. They exclude account and channel names, credentials, and request content.")
                }
            }
            .navigationTitle("Diagnostics")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(baseline ? "Return to Twitch" : "Done") { dismiss() }
                }
            }
            .sheet(item: $export) { ReportShareSheet(urls: $0.urls) }
            .onReceive(Timer.publish(every: 2, on: .main, in: .common).autoconnect()) { _ in
                services.reloadSnapshot()
            }
        }
    }
}

private struct ReportExport: Identifiable {
    let id = UUID()
    let urls: [URL]
}

private struct ReportShareSheet: UIViewControllerRepresentable {
    let urls: [URL]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: urls, applicationActivities: nil)
    }
    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}
