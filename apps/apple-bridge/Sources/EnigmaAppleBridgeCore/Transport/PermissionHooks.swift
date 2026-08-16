import Foundation

/// Per-source permission hooks. Source tickets (M08–M10, M13) replace stubs with
/// EventKit / Contacts / Notes prompts. Unauthorised sources must not abort the bridge.
public enum BridgeSourceID: String, Codable, Sendable, CaseIterable {
    case calendar
    case reminders
    case contacts
    case notes
}

public struct PermissionHooks: Sendable {
    public init() {}

    /// Stub permission prompt. Always returns `false` until a source ticket lands.
    public func requestAuthorisation(for source: BridgeSourceID) async -> Bool {
        _ = source
        return false
    }

    /// Current authorisation snapshot without prompting.
    public func isAuthorised(_ source: BridgeSourceID) -> Bool {
        _ = source
        return false
    }

    /// Build a capability report that continues even when individual sources are denied.
    public func capabilities() -> CapabilityReport {
        CapabilityReport(
            calendar: .init(available: true, authorised: isAuthorised(.calendar)),
            reminders: .init(available: true, authorised: isAuthorised(.reminders)),
            contacts: .init(available: true, authorised: isAuthorised(.contacts)),
            notes: .init(
                available: true,
                authorised: isAuthorised(.notes),
                quality: "best_effort"
            )
        )
    }
}
