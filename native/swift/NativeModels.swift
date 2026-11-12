import Foundation

struct StreamsideAccount: Equatable {
    let username: String
    let displayName: String
}

struct FollowedChannel: Identifiable, Equatable {
    let username: String
    let displayName: String
    var id: String { username }
}

enum SessionPresentation: Equatable {
    case restoring, signedOut, checkingAccount, authenticated, signingOut
    case failure, unavailable

    static func resolve(phase: Int, hasAccount: Bool, signOutState: Int) -> Self {
        if signOutState == 1 { return .signingOut }
        if signOutState == 2 { return .failure }
        switch phase {
        case 1: return .signedOut
        case 2: return .checkingAccount
        case 3, 4, 5: return hasAccount ? .authenticated : .failure
        case 6: return .failure
        case 7, 9: return .unavailable
        default: return .restoring
        }
    }
}

struct NativeServiceState {
    var phase = 0
    var account: StreamsideAccount?
    var channels: [FollowedChannel] = []
    var signOutState = 0
    var canSignOut = false
    var session: SessionPresentation {
        SessionPresentation.resolve(phase: phase, hasAccount: account != nil, signOutState: signOutState)
    }
    var isBusy: Bool {
        session == .checkingAccount || session == .restoring || session == .signingOut || phase == 3
    }
    // State changes immediately remove presentation data; a saved diagnostic
    // file from another process can never supply account/channel UI content.
    mutating func enforceSessionBoundary() {
        if session != .authenticated { account = nil; channels = [] }
        if phase != 4 && phase != 5 { channels = [] }
    }
}

// Native currentUser verification produces .authenticated before follows finish.
// A notification, saved token presence, or stale account alone is insufficient.
enum AuthenticationReturn {
    static func shouldReturn(session: SessionPresentation) -> Bool {
        session == .authenticated
    }
}
