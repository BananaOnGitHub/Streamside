import SwiftUI
import UIKit
import Combine

struct StreamsideShell: View {
    @ObservedObject var services: NativeServices
    @State private var diagnostics = false
    @State private var confirmSignOut = false

    var body: some View {
        NavigationStack {
            List {
                Section("Account") { accountContent }
                if services.state.session == .authenticated {
                    Section {
                        if services.state.phase == 3 {
                            ProgressView("Loading followed channels")
                        } else if services.state.channels.isEmpty {
                            Text("No followed channels returned.").foregroundStyle(.secondary)
                        } else {
                            ForEach(services.state.channels) { channel in
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(channel.displayName).font(.headline)
                                    Text("@\(channel.username)").font(.subheadline).foregroundStyle(.secondary)
                                }
                                .accessibilityElement(children: .combine)
                            }
                        }
                    } header: { Text("Followed channels") }
                      footer: { Text("Showing the first 50. Live status is unavailable in this build.") }
                }
                if let error = services.actionError {
                    Section { Text(error).foregroundStyle(.red).accessibilityAddTraits(.isStaticText) }
                }
            }
            .navigationTitle("Streamside")
            .refreshable { services.refresh() }
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button { diagnostics = true } label: { Label("Diagnostics", systemImage: "waveform.path.ecg") }
                        .accessibilityIdentifier("streamside.diagnostics")
                }
            }
            .sheet(isPresented: $diagnostics) {
                DiagnosticsView(services: services, baseline: false)
            }
            .confirmationDialog("Sign out of Twitch?", isPresented: $confirmSignOut, titleVisibility: .visible) {
                Button("Sign out", role: .destructive) { services.signOut() }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("You can sign in again using Twitch’s native authentication screen.")
            }
        }
    }

    @ViewBuilder private var accountContent: some View {
        switch services.state.session {
        case .authenticated:
            if let account = services.state.account {
                Label {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(account.displayName).font(.headline)
                        Text("@\(account.username)").foregroundStyle(.secondary)
                    }
                } icon: { Image(systemName: "person.crop.circle") }
                Button("Refresh") { services.refresh() }.disabled(services.state.isBusy)
                if services.state.canSignOut {
                    Button("Sign out", role: .destructive) { confirmSignOut = true }
                } else {
                    Text("Sign-out is unavailable. See diagnostics.").foregroundStyle(.secondary)
                }
            }
        case .restoring, .checkingAccount:
            ProgressView("Checking your existing account")
        case .signingOut:
            ProgressView("Signing out")
        case .signedOut:
            Label("Welcome to Streamside", systemImage: "person.crop.circle")
                .font(.headline)
            Text("You’re signed out. Sign in using Twitch’s existing authentication.")
                .foregroundStyle(.secondary)
            Button("Sign in") { services.signIn() }.disabled(!services.canSignIn)
            if !services.canSignIn {
                Text("Waiting for Twitch’s native sign-in screen. See diagnostics if it remains unavailable.")
                    .foregroundStyle(.secondary)
            }
            Button("Check for an existing account") { services.refresh() }
        case .failure:
            Text("Your account could not be verified. Check your connection and try again.")
            Button("Check account") { services.refresh() }
        case .unavailable:
            Text("Account services are unavailable. Open diagnostics for details.")
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
