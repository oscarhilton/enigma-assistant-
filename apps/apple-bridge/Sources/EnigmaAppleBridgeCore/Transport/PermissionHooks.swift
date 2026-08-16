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
    private let calendarIsAuthorised: @Sendable () -> Bool
    private let calendarRequestAccess: @Sendable () async -> Bool
    private let remindersSource: RemindersSource

    public init(
        calendarIsAuthorised: @escaping @Sendable () -> Bool = {
            EventKitCalendarAccess().authorizationStatus() == .authorised
        },
        calendarRequestAccess: @escaping @Sendable () async -> Bool = {
            await EventKitCalendarAccess().requestReadAccess()
        },
        remindersSource: RemindersSource = RemindersSource()
    ) {
        self.calendarIsAuthorised = calendarIsAuthorised
        self.calendarRequestAccess = calendarRequestAccess
        self.remindersSource = remindersSource
    }

    /// Permission prompt. Calendar/Reminders use EventKit; other sources remain stubs.
    public func requestAuthorisation(for source: BridgeSourceID) async -> Bool {
        switch source {
        case .calendar:
            return await calendarRequestAccess()
        case .reminders:
            return await remindersSource.requestAuthorisation()
        case .contacts, .notes:
            return false
        }
    }

    /// Current authorisation snapshot without prompting.
    public func isAuthorised(_ source: BridgeSourceID) -> Bool {
        switch source {
        case .calendar:
            return calendarIsAuthorised()
        case .reminders:
            return remindersSource.isAuthorised()
        case .contacts, .notes:
            return false
        }
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
