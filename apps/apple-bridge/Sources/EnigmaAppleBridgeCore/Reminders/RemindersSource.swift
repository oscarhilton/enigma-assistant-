import EventKit
import Foundation

/// Read-only EventKit reminders adapter (M09).
public final class RemindersSource: @unchecked Sendable {
    private let store: EKEventStore
    private let defaults: ReminderIngestDefaults
    private let snapshotProvider: () -> [ReminderSnapshot]
    private let authorisedProvider: () -> Bool

    public init(
        store: EKEventStore = EKEventStore(),
        defaults: ReminderIngestDefaults = .mvp,
        snapshotProvider: (() -> [ReminderSnapshot])? = nil,
        authorisedProvider: (() -> Bool)? = nil
    ) {
        self.store = store
        self.defaults = defaults
        self.snapshotProvider = snapshotProvider ?? { ReminderEventKit.fetchSnapshots(store: store) }
        self.authorisedProvider = authorisedProvider ?? {
            EKEventStore.authorizationStatus(for: .reminder) == .fullAccess
        }
    }

    public func isReady() -> Bool { isAuthorised() }
    public func isAuthorised() -> Bool { authorisedProvider() }

    @discardableResult
    public func requestAuthorisation() async -> Bool {
        do { return try await store.requestFullAccessToReminders() }
        catch { return false }
    }

    public func changes(cursor: String?) -> ReminderChangeBatch {
        guard isAuthorised() else {
            return ReminderChangeBatch(items: [], next_cursor: nil, exhausted: true, authorised: false)
        }
        return ReminderMapper.changeBatch(
            from: snapshotProvider(),
            cursor: cursor,
            defaults: defaults,
            authorised: true
        )
    }
}

enum ReminderEventKit {
    static func fetchSnapshots(store: EKEventStore) -> [ReminderSnapshot] {
        let semaphore = DispatchSemaphore(value: 0)
        var result: [ReminderSnapshot] = []
        let predicate = store.predicateForReminders(in: nil)
        store.fetchReminders(matching: predicate) { reminders in
            defer { semaphore.signal() }
            guard let reminders else { return }
            result = reminders.map(snapshot(from:))
        }
        _ = semaphore.wait(timeout: .now() + 10)
        return result
    }

    static func snapshot(from reminder: EKReminder) -> ReminderSnapshot {
        ReminderSnapshot(
            calendarItemIdentifier: reminder.calendarItemIdentifier,
            listIdentifier: reminder.calendar?.calendarIdentifier,
            title: reminder.title ?? "",
            notes: reminder.notes,
            dueAt: date(from: reminder.dueDateComponents),
            completedAt: reminder.completionDate,
            isCompleted: reminder.isCompleted,
            priority: reminder.priority == 0 ? nil : Int(reminder.priority),
            createdAt: reminder.creationDate,
            lastModifiedAt: reminder.lastModifiedDate
        )
    }

    static func date(from components: DateComponents?) -> Date? {
        guard let components else { return nil }
        return Calendar.current.date(from: components)
    }
}
