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
    private let notesSource: NotesSource

    public init(
        calendarIsAuthorised: @escaping @Sendable () -> Bool = {
            EventKitCalendarAccess().authorizationStatus() == .authorised
        },
        calendarRequestAccess: @escaping @Sendable () async -> Bool = {
            await EventKitCalendarAccess().requestReadAccess()
        },
        remindersSource: RemindersSource = RemindersSource(),
        notesSource: NotesSource = NotesSource()
    ) {
        self.calendarIsAuthorised = calendarIsAuthorised
        self.calendarRequestAccess = calendarRequestAccess
        self.remindersSource = remindersSource
        self.notesSource = notesSource
    }

    /// Permission prompt. Calendar/Reminders use EventKit; Notes uses opt-in + automation.
    public func requestAuthorisation(for source: BridgeSourceID) async -> Bool {
        switch source {
        case .calendar:
            return await calendarRequestAccess()
        case .reminders:
            return await remindersSource.requestAuthorisation()
        case .notes:
            return await notesSource.requestAuthorisation()
        case .contacts:
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
        case .notes:
            return notesSource.isAuthorised()
        case .contacts:
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
