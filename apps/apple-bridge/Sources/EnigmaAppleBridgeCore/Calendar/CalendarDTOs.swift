import Foundation

/// Canonical private calendar event JSON (matches `PrivateCalendarEvent` in packages/domain).
public struct PrivateCalendarEventDTO: Codable, Equatable, Sendable {
    public var id: String
    public var provider: String
    public var provider_event_id: String
    public var calendar_id: String?
    public var calendar_name: String?
    public var title: String
    public var description: String?
    public var location: String?
    public var url: String?
    public var start_at: String
    public var end_at: String
    public var all_day: Bool
    public var availability: String?
    public var organiser: PrivatePersonRefDTO?
    public var attendees: [PrivatePersonRefDTO]
    public var recurrence: RecurrenceInfoDTO?
    public var updated_at: String?

    public init(
        id: String,
        provider: String = "apple_calendar",
        provider_event_id: String,
        calendar_id: String? = nil,
        calendar_name: String? = nil,
        title: String,
        description: String? = nil,
        location: String? = nil,
        url: String? = nil,
        start_at: String,
        end_at: String,
        all_day: Bool = false,
        availability: String? = nil,
        organiser: PrivatePersonRefDTO? = nil,
        attendees: [PrivatePersonRefDTO] = [],
        recurrence: RecurrenceInfoDTO? = nil,
        updated_at: String? = nil
    ) {
        self.id = id
        self.provider = provider
        self.provider_event_id = provider_event_id
        self.calendar_id = calendar_id
        self.calendar_name = calendar_name
        self.title = title
        self.description = description
        self.location = location
        self.url = url
        self.start_at = start_at
        self.end_at = end_at
        self.all_day = all_day
        self.availability = availability
        self.organiser = organiser
        self.attendees = attendees
        self.recurrence = recurrence
        self.updated_at = updated_at
    }
}

public struct PrivatePersonRefDTO: Codable, Equatable, Sendable {
    public var display_name: String?
    public var email: String?
    public var provider_id: String?

    public init(display_name: String? = nil, email: String? = nil, provider_id: String? = nil) {
        self.display_name = display_name
        self.email = email
        self.provider_id = provider_id
    }
}

public struct RecurrenceInfoDTO: Codable, Equatable, Sendable {
    public var rule: String?
    public var raw: [String: String]

    public init(rule: String? = nil, raw: [String: String] = [:]) {
        self.rule = rule
        self.raw = raw
    }
}

public struct SyncCursorDTO: Codable, Equatable, Sendable {
    public var value: String
    public var source: String?

    public init(value: String, source: String? = "apple_calendar") {
        self.value = value
        self.source = source
    }
}

/// Bridge response for `GET /calendar/changes`.
public struct CalendarChangesResponse: Codable, Equatable, Sendable {
    public var authorised: Bool
    public var items: [PrivateCalendarEventDTO]
    public var next_cursor: SyncCursorDTO?
    public var exhausted: Bool

    public init(
        authorised: Bool,
        items: [PrivateCalendarEventDTO] = [],
        next_cursor: SyncCursorDTO? = nil,
        exhausted: Bool = true
    ) {
        self.authorised = authorised
        self.items = items
        self.next_cursor = next_cursor
        self.exhausted = exhausted
    }
}

public struct CalendarInfoDTO: Codable, Equatable, Sendable {
    public var id: String
    public var name: String
    public var allows_content_modifications: Bool

    public init(id: String, name: String, allows_content_modifications: Bool = false) {
        self.id = id
        self.name = name
        self.allows_content_modifications = allows_content_modifications
    }
}
