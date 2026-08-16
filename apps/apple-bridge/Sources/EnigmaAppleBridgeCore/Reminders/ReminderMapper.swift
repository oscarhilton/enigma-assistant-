import Foundation

public enum ReminderMapper {
    public static let provider = "apple_reminders"
    public static let intentSignalKind = "explicit_reminder"

    public static func canonicalID(providerID: String) -> String {
        "\(provider):\(providerID)"
    }

    public static func shouldIngest(
        _ snapshot: ReminderSnapshot,
        defaults: ReminderIngestDefaults = .mvp
    ) -> Bool {
        if defaults.incompleteOnly, snapshot.isCompleted { return false }
        if defaults.requireDueDate, snapshot.dueAt == nil { return false }
        return true
    }

    public static func map(
        _ snapshot: ReminderSnapshot,
        defaults: ReminderIngestDefaults = .mvp
    ) -> PrivateReminderDTO? {
        guard shouldIngest(snapshot, defaults: defaults) else { return nil }
        return PrivateReminderDTO(
            id: canonicalID(providerID: snapshot.calendarItemIdentifier),
            provider: provider,
            provider_id: snapshot.calendarItemIdentifier,
            list_id: snapshot.listIdentifier,
            title: snapshot.title,
            notes: snapshot.notes,
            due_at: iso8601(snapshot.dueAt),
            completed_at: iso8601(snapshot.completedAt),
            is_completed: snapshot.isCompleted,
            priority: snapshot.priority,
            created_at: iso8601(snapshot.createdAt),
            updated_at: iso8601(snapshot.lastModifiedAt)
        )
    }

    public static func mapAll(
        _ snapshots: [ReminderSnapshot],
        defaults: ReminderIngestDefaults = .mvp
    ) -> [PrivateReminderDTO] {
        snapshots.compactMap { map($0, defaults: defaults) }
    }

    public static func changeBatch(
        from snapshots: [ReminderSnapshot],
        cursor: String?,
        defaults: ReminderIngestDefaults = .mvp,
        authorised: Bool = true
    ) -> ReminderChangeBatch {
        guard authorised else {
            return ReminderChangeBatch(items: [], next_cursor: nil, exhausted: true, authorised: false)
        }

        let mapped = mapAll(snapshots, defaults: defaults).sorted { lhs, rhs in
            cursorKey(updatedAt: lhs.updated_at, providerID: lhs.provider_id)
                < cursorKey(updatedAt: rhs.updated_at, providerID: rhs.provider_id)
        }

        let filtered: [PrivateReminderDTO]
        if let cursor, !cursor.isEmpty {
            filtered = mapped.filter {
                cursorKey(updatedAt: $0.updated_at, providerID: $0.provider_id) > cursor
            }
        } else {
            filtered = mapped
        }

        let next: ReminderSyncCursor?
        if let last = filtered.last {
            next = ReminderSyncCursor(
                value: cursorKey(updatedAt: last.updated_at, providerID: last.provider_id),
                source: provider
            )
        } else if let cursor, !cursor.isEmpty {
            next = ReminderSyncCursor(value: cursor, source: provider)
        } else {
            next = nil
        }

        return ReminderChangeBatch(
            items: filtered,
            next_cursor: next,
            exhausted: true,
            authorised: true
        )
    }

    public static func cursorKey(updatedAt: String?, providerID: String) -> String {
        "\(updatedAt ?? "")|\(providerID)"
    }

    public static func iso8601(_ date: Date?) -> String? {
        guard let date else { return nil }
        return isoFormatter.string(from: date)
    }

    private static let isoFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
