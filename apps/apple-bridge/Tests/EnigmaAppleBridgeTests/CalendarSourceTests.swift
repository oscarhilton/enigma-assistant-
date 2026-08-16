import EnigmaAppleBridgeCore
import XCTest

final class CalendarEventMapperTests: XCTestCase {
    func testMapsRequiredFieldsIncludingAppleAddenda() throws {
        let start = Date(timeIntervalSince1970: 1_787_000_000)
        let end = Date(timeIntervalSince1970: 1_787_003_600)
        let modified = Date(timeIntervalSince1970: 1_786_900_000)

        let snapshot = CalendarEventSnapshot(
            eventIdentifier: "EK-42",
            calendarIdentifier: "cal_work",
            calendarTitle: "Work",
            title: "Design review",
            notes: "Bring mockups",
            location: "Studio",
            url: "https://example.com/meet",
            startDate: start,
            endDate: end,
            isAllDay: false,
            availability: "busy",
            organiser: PrivatePersonRefDTO(display_name: "Ada", email: "ada@example.com"),
            attendees: [
                PrivatePersonRefDTO(display_name: "Bob", email: "bob@example.com", provider_id: "mailto:bob@example.com"),
            ],
            recurrenceRule: "FREQ=WEEKLY;INTERVAL=1",
            recurrenceFrequency: "weekly",
            lastModified: modified
        )

        let dto = CalendarEventMapper.map(snapshot)
        XCTAssertEqual(dto.provider, "apple_calendar")
        XCTAssertEqual(dto.provider_event_id, "EK-42")
        XCTAssertEqual(dto.id, "apple_calendar:EK-42")
        XCTAssertEqual(dto.calendar_id, "cal_work")
        XCTAssertEqual(dto.calendar_name, "Work")
        XCTAssertEqual(dto.title, "Design review")
        XCTAssertEqual(dto.description, "Bring mockups")
        XCTAssertEqual(dto.location, "Studio")
        XCTAssertEqual(dto.url, "https://example.com/meet")
        XCTAssertEqual(dto.availability, "busy")
        XCTAssertEqual(dto.organiser?.email, "ada@example.com")
        XCTAssertEqual(dto.attendees.count, 1)
        XCTAssertEqual(dto.recurrence?.rule, "FREQ=WEEKLY;INTERVAL=1")
        XCTAssertEqual(dto.recurrence?.raw["frequency"], "weekly")
        XCTAssertEqual(dto.updated_at, CalendarEventMapper.format(modified))
        XCTAssertEqual(dto.start_at, CalendarEventMapper.format(start))
        XCTAssertEqual(dto.end_at, CalendarEventMapper.format(end))

        let data = try BridgeJSON.encode(dto)
        let json = String(decoding: data, as: UTF8.self)
        XCTAssertTrue(json.contains("\"provider\":\"apple_calendar\""))
        XCTAssertTrue(json.contains("\"calendar_name\":\"Work\""))
    }
}

final class CalendarSourceTests: XCTestCase {
    func testPermissionDeniedReturnsAuthorisedFalseWithoutCrashing() {
        let source = CalendarSource(
            isAuthorised: { false },
            requestAccess: { false },
            fetchSnapshots: { _, _, _ in
                XCTFail("must not fetch when unauthorised")
                return []
            }
        )

        let response = source.getChanges(cursor: nil, selectedCalendarIDs: ["cal_1"])
        XCTAssertFalse(response.authorised)
        XCTAssertTrue(response.items.isEmpty)
        XCTAssertTrue(response.exhausted)
        XCTAssertNil(response.next_cursor)
        XCTAssertFalse(source.isReady())
    }

    func testSelectedCalendarsOnlyAndCursorFiltering() {
        let older = Date(timeIntervalSince1970: 1_000)
        let newer = Date(timeIntervalSince1970: 2_000)
        let snapshots = [
            CalendarEventSnapshot(
                eventIdentifier: "old",
                calendarIdentifier: "cal_a",
                calendarTitle: "A",
                title: "Old",
                startDate: older,
                endDate: older.addingTimeInterval(3600),
                lastModified: older
            ),
            CalendarEventSnapshot(
                eventIdentifier: "new",
                calendarIdentifier: "cal_a",
                calendarTitle: "A",
                title: "New",
                startDate: newer,
                endDate: newer.addingTimeInterval(3600),
                lastModified: newer
            ),
            CalendarEventSnapshot(
                eventIdentifier: "other",
                calendarIdentifier: "cal_b",
                calendarTitle: "B",
                title: "Other",
                startDate: newer,
                endDate: newer.addingTimeInterval(3600),
                lastModified: newer
            ),
        ]

        let source = CalendarSource(
            isAuthorised: { true },
            requestAccess: { true },
            fetchSnapshots: { _, _, _ in snapshots }
        )

        let cursor = CalendarEventMapper.format(older)
        let response = source.getChanges(cursor: cursor, selectedCalendarIDs: ["cal_a"])
        XCTAssertTrue(response.authorised)
        XCTAssertEqual(response.items.count, 1)
        XCTAssertEqual(response.items[0].provider_event_id, "new")
        XCTAssertEqual(response.next_cursor?.value, CalendarEventMapper.format(newer))
    }

    func testEmptySelectionYieldsNoEvents() {
        let source = CalendarSource(
            isAuthorised: { true },
            requestAccess: { true },
            fetchSnapshots: { _, _, _ in
                XCTFail("should not fetch when nothing selected")
                return []
            }
        )
        let response = source.getChanges(cursor: nil, selectedCalendarIDs: [])
        XCTAssertTrue(response.authorised)
        XCTAssertTrue(response.items.isEmpty)
    }
}

final class CalendarRouteTests: XCTestCase {
    func testCalendarChangesRouteWithCursor() throws {
        let snapshot = CalendarEventSnapshot(
            eventIdentifier: "EK-9",
            calendarIdentifier: "cal_1",
            calendarTitle: "Personal",
            title: "Coffee",
            startDate: Date(timeIntervalSince1970: 3_000),
            endDate: Date(timeIntervalSince1970: 3_600),
            availability: "tentative",
            lastModified: Date(timeIntervalSince1970: 2_500)
        )
        let calendarSource = CalendarSource(
            isAuthorised: { true },
            requestAccess: { true },
            fetchSnapshots: { _, _, _ in [snapshot] }
        )
        let hooks = PermissionHooks(calendarIsAuthorised: { true })
        let server = BridgeHTTPServer(
            token: "test-token",
            permissionHooks: hooks,
            calendarSource: calendarSource
        )

        let result = try server.handleHTTP(
            method: "GET",
            path: "/calendar/changes",
            authorization: "Bearer test-token",
            query: ["calendar_ids": "cal_1", "cursor": "1970-01-01T00:00:00Z"]
        )
        XCTAssertEqual(result.status, 200)
        let decoded = try JSONDecoder().decode(CalendarChangesResponse.self, from: result.body)
        XCTAssertTrue(decoded.authorised)
        XCTAssertEqual(decoded.items.count, 1)
        XCTAssertEqual(decoded.items[0].provider, "apple_calendar")
        XCTAssertEqual(decoded.items[0].calendar_name, "Personal")
        XCTAssertEqual(decoded.items[0].availability, "tentative")
    }

    func testCalendarChangesPermissionDenied() throws {
        let calendarSource = CalendarSource(isAuthorised: { false }, requestAccess: { false })
        let hooks = PermissionHooks(calendarIsAuthorised: { false })
        let server = BridgeHTTPServer(
            token: "test-token",
            permissionHooks: hooks,
            calendarSource: calendarSource
        )
        let result = try server.handleHTTP(
            method: "GET",
            path: "/calendar/changes",
            authorization: "Bearer test-token",
            query: ["calendar_ids": "cal_1"]
        )
        XCTAssertEqual(result.status, 200)
        let decoded = try JSONDecoder().decode(CalendarChangesResponse.self, from: result.body)
        XCTAssertFalse(decoded.authorised)
        XCTAssertTrue(decoded.items.isEmpty)

        let caps = try server.handleHTTP(
            method: "GET",
            path: "/capabilities",
            authorization: "Bearer test-token"
        )
        let report = try JSONDecoder().decode(CapabilityReport.self, from: caps.body)
        XCTAssertFalse(report.calendar.authorised)
    }
}
