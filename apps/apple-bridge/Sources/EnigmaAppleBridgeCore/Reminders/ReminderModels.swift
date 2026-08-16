import Foundation

/// Canonical reminder payload — mirrors `PrivateReminder` (snake_case JSON).
public struct PrivateReminderDTO: Codable, Equatable, Sendable {
    public var id: String
    public var provider: String
    public var provider_id: String
    public var list_id: String?
    public var title: String
    public var notes: String?
    public var due_at: String?
    public var completed_at: String?
    public var is_completed: Bool
    public var priority: Int?
    public var created_at: String?
    public var updated_at: String?

    public init(
        id: String,
        provider: String = "apple_reminders",
        provider_id: String,
        list_id: String? = nil,
        title: String,
        notes: String? = nil,
        due_at: String? = nil,
        completed_at: String? = nil,
        is_completed: Bool = false,
        priority: Int? = nil,
        created_at: String? = nil,
        updated_at: String? = nil
    ) {
        self.id = id
        self.provider = provider
        self.provider_id = provider_id
        self.list_id = list_id
        self.title = title
        self.notes = notes
        self.due_at = due_at
        self.completed_at = completed_at
        self.is_completed = is_completed
        self.priority = priority
        self.created_at = created_at
        self.updated_at = updated_at
    }
}

public struct ReminderSyncCursor: Codable, Equatable, Sendable {
    public var value: String
    public var source: String?

    public init(value: String, source: String? = "apple_reminders") {
        self.value = value
        self.source = source
    }
}

public struct ReminderChangeBatch: Codable, Equatable, Sendable {
    public var items: [PrivateReminderDTO]
    public var next_cursor: ReminderSyncCursor?
    public var exhausted: Bool
    public var authorised: Bool

    public init(
        items: [PrivateReminderDTO],
        next_cursor: ReminderSyncCursor? = nil,
        exhausted: Bool = true,
        authorised: Bool = true
    ) {
        self.items = items
        self.next_cursor = next_cursor
        self.exhausted = exhausted
        self.authorised = authorised
    }
}

public struct ReminderSnapshot: Equatable, Sendable {
    public var calendarItemIdentifier: String
    public var listIdentifier: String?
    public var title: String
    public var notes: String?
    public var dueAt: Date?
    public var completedAt: Date?
    public var isCompleted: Bool
    public var priority: Int?
    public var createdAt: Date?
    public var lastModifiedAt: Date?

    public init(
        calendarItemIdentifier: String,
        listIdentifier: String? = nil,
        title: String,
        notes: String? = nil,
        dueAt: Date? = nil,
        completedAt: Date? = nil,
        isCompleted: Bool = false,
        priority: Int? = nil,
        createdAt: Date? = nil,
        lastModifiedAt: Date? = nil
    ) {
        self.calendarItemIdentifier = calendarItemIdentifier
        self.listIdentifier = listIdentifier
        self.title = title
        self.notes = notes
        self.dueAt = dueAt
        self.completedAt = completedAt
        self.isCompleted = isCompleted
        self.priority = priority
        self.createdAt = createdAt
        self.lastModifiedAt = lastModifiedAt
    }
}

public struct ReminderIngestDefaults: Equatable, Sendable {
    public var incompleteOnly: Bool
    public var requireDueDate: Bool

    public init(incompleteOnly: Bool = true, requireDueDate: Bool = true) {
        self.incompleteOnly = incompleteOnly
        self.requireDueDate = requireDueDate
    }

    public static let mvp = ReminderIngestDefaults()
}
