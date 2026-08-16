import Foundation

/// EventKit-free snapshot used for mapping and unit tests.
public struct CalendarEventSnapshot: Equatable, Sendable {
    public var eventIdentifier: String
    public var calendarIdentifier: String?
    public var calendarTitle: String?
    public var title: String
    public var notes: String?
    public var location: String?
    public var url: String?
    public var startDate: Date
    public var endDate: Date
    public var isAllDay: Bool
    public var availability: String?
    public var organiser: PrivatePersonRefDTO?
    public var attendees: [PrivatePersonRefDTO]
    public var recurrenceRule: String?
    public var recurrenceFrequency: String?
    public var lastModified: Date?

    public init(
        eventIdentifier: String,
        calendarIdentifier: String? = nil,
        calendarTitle: String? = nil,
        title: String,
        notes: String? = nil,
        location: String? = nil,
        url: String? = nil,
        startDate: Date,
        endDate: Date,
        isAllDay: Bool = false,
        availability: String? = nil,
        organiser: PrivatePersonRefDTO? = nil,
        attendees: [PrivatePersonRefDTO] = [],
        recurrenceRule: String? = nil,
        recurrenceFrequency: String? = nil,
        lastModified: Date? = nil
    ) {
        self.eventIdentifier = eventIdentifier
        self.calendarIdentifier = calendarIdentifier
        self.calendarTitle = calendarTitle
        self.title = title
        self.notes = notes
        self.location = location
        self.url = url
        self.startDate = startDate
        self.endDate = endDate
        self.isAllDay = isAllDay
        self.availability = availability
        self.organiser = organiser
        self.attendees = attendees
        self.recurrenceRule = recurrenceRule
        self.recurrenceFrequency = recurrenceFrequency
        self.lastModified = lastModified
    }
}

/// Maps EventKit-shaped snapshots → `PrivateCalendarEvent` JSON DTOs.
public enum CalendarEventMapper {
    public static let provider = "apple_calendar"

    private static let isoFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let isoFormatterFallback: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    public static func map(_ snapshot: CalendarEventSnapshot) -> PrivateCalendarEventDTO {
        let recurrence: RecurrenceInfoDTO?
        if snapshot.recurrenceRule != nil || snapshot.recurrenceFrequency != nil {
            var raw: [String: String] = [:]
            if let frequency = snapshot.recurrenceFrequency {
                raw["frequency"] = frequency
            }
            recurrence = RecurrenceInfoDTO(rule: snapshot.recurrenceRule, raw: raw)
        } else {
            recurrence = nil
        }

        return PrivateCalendarEventDTO(
            id: "apple_calendar:\(snapshot.eventIdentifier)",
            provider: provider,
            provider_event_id: snapshot.eventIdentifier,
            calendar_id: snapshot.calendarIdentifier,
            calendar_name: snapshot.calendarTitle,
            title: snapshot.title,
            description: snapshot.notes,
            location: snapshot.location,
            url: snapshot.url,
            start_at: format(snapshot.startDate),
            end_at: format(snapshot.endDate),
            all_day: snapshot.isAllDay,
            availability: snapshot.availability,
            organiser: snapshot.organiser,
            attendees: snapshot.attendees,
            recurrence: recurrence,
            updated_at: snapshot.lastModified.map(format)
        )
    }

    public static func format(_ date: Date) -> String {
        if let withFraction = optionalFractional(date) {
            return withFraction
        }
        return isoFormatterFallback.string(from: date)
    }

    public static func parseCursor(_ value: String?) -> Date? {
        guard let value, !value.isEmpty else { return nil }
        if let date = isoFormatter.date(from: value) {
            return date
        }
        return isoFormatterFallback.date(from: value)
    }

    private static func optionalFractional(_ date: Date) -> String? {
        isoFormatter.string(from: date)
    }
}
