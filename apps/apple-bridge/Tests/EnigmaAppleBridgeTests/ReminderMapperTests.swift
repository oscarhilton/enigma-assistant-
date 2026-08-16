import EnigmaAppleBridgeCore
import XCTest

final class ReminderMapperTests: XCTestCase {
    private let due = Date(timeIntervalSince1970: 1_787_000_000)
    private let updated = Date(timeIntervalSince1970: 1_787_100_000)

    func testMapsIncompleteDueReminderToPrivateReminderShape() throws {
        let snapshot = ReminderSnapshot(
            calendarItemIdentifier: "ek-1",
            listIdentifier: "list-a",
            title: "Send deployment notes",
            notes: "Explicit user intent",
            dueAt: due,
            isCompleted: false,
            priority: 1,
            createdAt: due,
            lastModifiedAt: updated
        )

        let dto = try XCTUnwrap(ReminderMapper.map(snapshot))
        XCTAssertEqual(dto.provider, "apple_reminders")
        XCTAssertEqual(dto.provider_id, "ek-1")
        XCTAssertEqual(dto.id, "apple_reminders:ek-1")
        XCTAssertEqual(dto.title, "Send deployment notes")
        XCTAssertEqual(dto.list_id, "list-a")
        XCTAssertFalse(dto.is_completed)
        XCTAssertNotNil(dto.due_at)
        XCTAssertEqual(dto.priority, 1)
        XCTAssertEqual(ReminderMapper.intentSignalKind, "explicit_reminder")
    }

    func testMVPDefaultsDropCompletedReminders() {
        let completed = ReminderSnapshot(
            calendarItemIdentifier: "done-1",
            title: "Already done",
            dueAt: due,
            completedAt: updated,
            isCompleted: true,
            lastModifiedAt: updated
        )
        XCTAssertNil(ReminderMapper.map(completed))
        XCTAssertFalse(ReminderMapper.shouldIngest(completed))
    }

    func testMVPDefaultsDropIncompleteRemindersWithoutDueDate() {
        let noDue = ReminderSnapshot(
            calendarItemIdentifier: "someday-1",
            title: "Someday / maybe",
            dueAt: nil,
            isCompleted: false
        )
        XCTAssertNil(ReminderMapper.map(noDue))
        XCTAssertFalse(ReminderMapper.shouldIngest(noDue))
    }

    func testRelaxedDefaultsKeepCompletedAndUndated() {
        let defaults = ReminderIngestDefaults(incompleteOnly: false, requireDueDate: false)
        let completed = ReminderSnapshot(
            calendarItemIdentifier: "done-2",
            title: "Done",
            dueAt: nil,
            isCompleted: true
        )
        XCTAssertNotNil(ReminderMapper.map(completed, defaults: defaults))
    }

    func testExplicitRemindersAreFirstClassIntentSignals() {
        let snapshots = [
            ReminderSnapshot(
                calendarItemIdentifier: "intent-1",
                title: "Review proposal",
                dueAt: due,
                isCompleted: false,
                lastModifiedAt: updated
            ),
            ReminderSnapshot(
                calendarItemIdentifier: "intent-2",
                title: "Completed noise",
                dueAt: due,
                isCompleted: true,
                lastModifiedAt: updated
            ),
        ]

        let batch = ReminderMapper.changeBatch(from: snapshots, cursor: nil)
        XCTAssertEqual(batch.items.count, 1)
        XCTAssertEqual(batch.items[0].title, "Review proposal")
        XCTAssertEqual(batch.items[0].provider, ReminderMapper.provider)
        XCTAssertEqual(ReminderMapper.intentSignalKind, "explicit_reminder")
        XCTAssertTrue(batch.exhausted)
        XCTAssertTrue(batch.authorised)
        XCTAssertNotNil(batch.next_cursor)
    }

    func testCursorSkipsAlreadySeenReminders() {
        let older = ReminderSnapshot(
            calendarItemIdentifier: "a",
            title: "Older",
            dueAt: due,
            isCompleted: false,
            lastModifiedAt: Date(timeIntervalSince1970: 1_000)
        )
        let newer = ReminderSnapshot(
            calendarItemIdentifier: "b",
            title: "Newer",
            dueAt: due,
            isCompleted: false,
            lastModifiedAt: Date(timeIntervalSince1970: 2_000)
        )
        let first = ReminderMapper.changeBatch(from: [older, newer], cursor: nil)
        let cursor = try! XCTUnwrap(first.next_cursor?.value)
        let second = ReminderMapper.changeBatch(from: [older, newer], cursor: cursor)
        XCTAssertTrue(second.items.isEmpty)

        let olderKey = ReminderMapper.cursorKey(
            updatedAt: ReminderMapper.iso8601(older.lastModifiedAt),
            providerID: older.calendarItemIdentifier
        )
        let afterOlder = ReminderMapper.changeBatch(from: [older, newer], cursor: olderKey)
        XCTAssertEqual(afterOlder.items.map(\.provider_id), ["b"])
    }
}

final class RemindersHTTPRouteTests: XCTestCase {
    func testRemindersChangesRequiresBearerToken() throws {
        let source = RemindersSource(
            snapshotProvider: { [] },
            authorisedProvider: { true }
        )
        let server = BridgeHTTPServer(token: "test-token", remindersSource: source)
        let denied = try server.handleHTTP(method: "GET", path: "/reminders/changes", authorization: nil)
        XCTAssertEqual(denied.status, 401)
    }

    func testRemindersChangesReturnsMappedItemsWithCursor() throws {
        let due = Date(timeIntervalSince1970: 1_787_000_000)
        let source = RemindersSource(
            snapshotProvider: {
                [
                    ReminderSnapshot(
                        calendarItemIdentifier: "r1",
                        title: "Pay invoice",
                        dueAt: due,
                        isCompleted: false,
                        lastModifiedAt: due
                    ),
                    ReminderSnapshot(
                        calendarItemIdentifier: "r2",
                        title: "Completed",
                        dueAt: due,
                        isCompleted: true,
                        lastModifiedAt: due
                    ),
                ]
            },
            authorisedProvider: { true }
        )
        let server = BridgeHTTPServer(token: "test-token", remindersSource: source)
        let result = try server.handleHTTP(
            method: "GET",
            path: "/reminders/changes",
            authorization: "Bearer test-token"
        )
        XCTAssertEqual(result.status, 200)
        let batch = try JSONDecoder().decode(ReminderChangeBatch.self, from: result.body)
        XCTAssertTrue(batch.authorised)
        XCTAssertEqual(batch.items.count, 1)
        XCTAssertEqual(batch.items[0].provider, "apple_reminders")
        XCTAssertEqual(batch.items[0].title, "Pay invoice")
        XCTAssertNotNil(batch.next_cursor)
    }

    func testRemindersChangesUnauthorisedDoesNotCrash() throws {
        let source = RemindersSource(
            snapshotProvider: {
                XCTFail("should not fetch when unauthorised")
                return []
            },
            authorisedProvider: { false }
        )
        let server = BridgeHTTPServer(token: "test-token", remindersSource: source)
        let result = try server.handleHTTP(
            method: "GET",
            path: "/reminders/changes",
            authorization: "Bearer test-token",
            query: ["cursor": "anything"]
        )
        XCTAssertEqual(result.status, 200)
        let batch = try JSONDecoder().decode(ReminderChangeBatch.self, from: result.body)
        XCTAssertFalse(batch.authorised)
        XCTAssertTrue(batch.items.isEmpty)
        XCTAssertTrue(batch.exhausted)
    }

    func testQueryParserExtractsCursor() {
        let query = BridgeHTTPServer.parseQuery("cursor=abc%7Cdef&other=1")
        XCTAssertEqual(query["cursor"], "abc|def")
        XCTAssertEqual(query["other"], "1")
    }
}
