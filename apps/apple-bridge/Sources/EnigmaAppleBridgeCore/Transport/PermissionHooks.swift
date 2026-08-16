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
    private let remindersSource: RemindersSource

    public init(remindersSource: RemindersSource = RemindersSource()) {
        self.remindersSource = remindersSource
    }

    public func requestAuthorisation(for source: BridgeSourceID) async -> Bool {
        switch source {
        case .reminders:
            return await remindersSource.requestAuthorisation()
        case .calendar, .contacts, .notes:
            return false
        }
    }

    public func isAuthorised(_ source: BridgeSourceID) -> Bool {
        switch source {
        case .reminders:
            return remindersSource.isAuthorised()
        case .calendar, .contacts, .notes:
            return false
        }
    }

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
