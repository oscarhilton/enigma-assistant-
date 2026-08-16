import EventKit
import Foundation

/// Read-only Apple Calendar (EventKit) adapter.
///
/// Emits `PrivateCalendarEvent` JSON with `provider="apple_calendar"`.
/// Only calendars in `selectedCalendarIDs` are ingested; an empty selection yields no events.
public struct CalendarSource: Sendable {
    public typealias SnapshotFetcher = @Sendable (
        _ selectedCalendarIDs: Set<String>,
        _ start: Date,
        _ end: Date
    ) -> [CalendarEventSnapshot]

    private let isAuthorised: @Sendable () -> Bool
    private let requestAccess: @Sendable () async -> Bool
    private let fetchSnapshots: SnapshotFetcher
    private let listCalendarsImpl: @Sendable () -> [CalendarInfoDTO]

    public init(
        isAuthorised: @escaping @Sendable () -> Bool = {
            EventKitCalendarAccess().authorizationStatus() == .authorised
        },
        requestAccess: @escaping @Sendable () async -> Bool = {
            await EventKitCalendarAccess().requestReadAccess()
        },
        fetchSnapshots: SnapshotFetcher? = nil,
        listCalendars: (@Sendable () -> [CalendarInfoDTO])? = nil
    ) {
        self.isAuthorised = isAuthorised
        self.requestAccess = requestAccess
        self.fetchSnapshots = fetchSnapshots ?? { selected, start, end in
            Self.defaultFetchSnapshots(selectedCalendarIDs: selected, start: start, end: end)
        }
        self.listCalendarsImpl = listCalendars ?? {
            Self.defaultListCalendars()
        }
    }

    public func isReady() -> Bool {
        isAuthorised()
    }

    public func requestReadAccess() async -> Bool {
        await requestAccess()
    }

    public func listCalendars() -> [CalendarInfoDTO] {
        guard isAuthorised() else { return [] }
        return listCalendarsImpl()
    }

    /// Fetch changes since `cursor` (ISO-8601 last-modified watermark) for selected calendars.
    public func getChanges(
        cursor: String?,
        selectedCalendarIDs: Set<String>,
        now: Date = Date(),
        lookbackDays: Int = 90,
        lookaheadDays: Int = 365
    ) -> CalendarChangesResponse {
        guard isAuthorised() else {
            return CalendarChangesResponse(authorised: false, items: [], next_cursor: nil, exhausted: true)
        }

        if selectedCalendarIDs.isEmpty {
            return CalendarChangesResponse(authorised: true, items: [], next_cursor: nil, exhausted: true)
        }

        let cursorDate = CalendarEventMapper.parseCursor(cursor)
        let calendar = Calendar.current
        let windowStart = calendar.date(byAdding: .day, value: -lookbackDays, to: now) ?? now
        let windowEnd = calendar.date(byAdding: .day, value: lookaheadDays, to: now) ?? now

        let snapshots = fetchSnapshots(selectedCalendarIDs, windowStart, windowEnd)
            .filter { snapshot in
                guard let calendarID = snapshot.calendarIdentifier else { return false }
                guard selectedCalendarIDs.contains(calendarID) else { return false }
                if let cursorDate {
                    let modified = snapshot.lastModified ?? snapshot.startDate
                    return modified > cursorDate
                }
                return true
            }
            .sorted { lhs, rhs in
                let left = lhs.lastModified ?? lhs.startDate
                let right = rhs.lastModified ?? rhs.startDate
                if left != right { return left < right }
                return lhs.eventIdentifier < rhs.eventIdentifier
            }

        let items = snapshots.map(CalendarEventMapper.map)
        let nextCursor: SyncCursorDTO?
        if let last = snapshots.last {
            let stamp = last.lastModified ?? last.startDate
            nextCursor = SyncCursorDTO(value: CalendarEventMapper.format(stamp), source: "apple_calendar")
        } else if let cursor, !cursor.isEmpty {
            nextCursor = SyncCursorDTO(value: cursor, source: "apple_calendar")
        } else {
            nextCursor = nil
        }

        return CalendarChangesResponse(
            authorised: true,
            items: items,
            next_cursor: nextCursor,
            exhausted: true
        )
    }

    // MARK: - EventKit defaults

    private static func defaultListCalendars() -> [CalendarInfoDTO] {
        let store = EKEventStore()
        return store.calendars(for: .event).map { calendar in
            CalendarInfoDTO(
                id: calendar.calendarIdentifier,
                name: calendar.title,
                allows_content_modifications: calendar.allowsContentModifications
            )
        }
    }

    private static func defaultFetchSnapshots(
        selectedCalendarIDs: Set<String>,
        start: Date,
        end: Date
    ) -> [CalendarEventSnapshot] {
        let store = EKEventStore()
        let calendars = store.calendars(for: .event).filter { selectedCalendarIDs.contains($0.calendarIdentifier) }
        guard !calendars.isEmpty else { return [] }

        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: calendars)
        let events = store.events(matching: predicate)
        return events.map(Self.snapshot(from:))
    }

    public static func snapshot(from event: EKEvent) -> CalendarEventSnapshot {
        let availability: String?
        switch event.availability {
        case .busy: availability = "busy"
        case .free: availability = "free"
        case .tentative: availability = "tentative"
        case .unavailable: availability = "unavailable"
        case .notSupported: availability = nil
        @unknown default: availability = nil
        }

        let organiser: PrivatePersonRefDTO?
        if let participant = event.organizer {
            organiser = personRef(from: participant)
        } else {
            organiser = nil
        }

        let attendees = (event.attendees ?? []).map(personRef(from:))

        var recurrenceRule: String?
        var recurrenceFrequency: String?
        if let rule = event.recurrenceRules?.first {
            recurrenceRule = rule.description
            switch rule.frequency {
            case .daily: recurrenceFrequency = "daily"
            case .weekly: recurrenceFrequency = "weekly"
            case .monthly: recurrenceFrequency = "monthly"
            case .yearly: recurrenceFrequency = "yearly"
            @unknown default: recurrenceFrequency = nil
            }
        }

        return CalendarEventSnapshot(
            eventIdentifier: event.eventIdentifier ?? UUID().uuidString,
            calendarIdentifier: event.calendar?.calendarIdentifier,
            calendarTitle: event.calendar?.title,
            title: event.title ?? "",
            notes: event.notes,
            location: event.location,
            url: event.url?.absoluteString,
            startDate: event.startDate,
            endDate: event.endDate,
            isAllDay: event.isAllDay,
            availability: availability,
            organiser: organiser,
            attendees: attendees,
            recurrenceRule: recurrenceRule,
            recurrenceFrequency: recurrenceFrequency,
            lastModified: event.lastModifiedDate
        )
    }

    private static func personRef(from participant: EKParticipant) -> PrivatePersonRefDTO {
        let url = participant.url
        let email: String?
        if url.scheme == "mailto" {
            email = url.absoluteString.replacingOccurrences(of: "mailto:", with: "")
        } else {
            email = nil
        }
        return PrivatePersonRefDTO(
            display_name: participant.name,
            email: email,
            provider_id: url.absoluteString
        )
    }
}
