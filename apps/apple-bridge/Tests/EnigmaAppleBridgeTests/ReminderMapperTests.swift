import EnigmaAppleBridgeCore
import XCTest

final class ReminderMapperTests: XCTestCase {
    func testMapsPrivateReminderWithAppleRemindersProvider() throws {
        let due = Date(timeIntervalSince1970: 1_724_817_600)
        let created = Date(timeIntervalSince1970: 1_724_800_000)
        let modified = Date(timeIntervalSince1970: 1_724_810_000)

        let snapshot = ReminderSnapshot(
            calendarItemIdentifier: "REM-42",
            listIdentifier: "list-personal",
            title: "Send deployment notes",
            notes: "Include PERSON_81",
            dueAt: due,
            completedAt: nil,
            isCompleted: false,
            priority: 1,
            createdAt: created,
            lastModifiedAt: modified
        )

        let dto = try XCTUnwrap(ReminderMapper.map(snapshot))

        XCTAssertEqual(dto.provider, "apple_reminders")
        XCTAssertEqual(dto.id, "apple_reminders:REM-42")
        XCTAssertEqual(dto.provider_id, "REM-42")
        XCTAssertEqual(dto.list_id, "list-personal")
        XCTAssertEqual(dto.title, "Send deployment notes")
        XCTAssertEqual(dto.notes, "Include PERSON_81")
        XCTAssertEqual(dto.is_completed, false)
        XCTAssertEqual(dto.priority, 1)
        XCTAssertNotNil(dto.due_at)
        XCTAssertNotNil(dto.created_at)
        XCTAssertNotNil(dto.updated_at)

        let data = try BridgeJSON.encode(dto)
        let json = String(decoding: data, as: UTF8.self)
        XCTAssertTrue(json.contains("\"provider\":\"apple_reminders\""))
        XCTAssertTrue(json.contains("\"provider_id\":\"REM-42\""))
        XCTAssertTrue(json.contains("\"due_at\""))
    }

    func testMVPDefaultsKeepIncompleteWithDueDatesOnly() {
        let due = Date(timeIntervalSince1970: 1_724_817_600)

        let incompleteWithDue = ReminderSnapshot(
            calendarItemIdentifier: "a",
            title: "Do the thing",
            dueAt: due,
            isCompleted: false
        )
        let completedWithDue = ReminderSnapshot(
            calendarItemIdentifier: "b",
            title: "Done",
            dueAt: due,
            completedAt: due,
            isCompleted: true
        )
        let incompleteWithoutDue = ReminderSnapshot(
            calendarItemIdentifier: "c",
            title: "Someday",
            dueAt: nil,
            isCompleted: false
        )

        XCTAssertTrue(ReminderMapper.shouldIngest(incompleteWithDue))
        XCTAssertFalse(ReminderMapper.shouldIngest(completedWithDue))
        XCTAssertFalse(ReminderMapper.shouldIngest(incompleteWithoutDue))
        XCTAssertNotNil(ReminderMapper.map(incompleteWithDue))
        XCTAssertNil(ReminderMapper.map(completedWithDue))
        XCTAssertNil(ReminderMapper.map(incompleteWithoutDue))
    }

    func testGetChangesFiltersCompletedAndUndated() {
        let due = Date(timeIntervalSince1970: 1_724_817_600)
        let older = Date(timeIntervalSince1970: 1_724_800_000)
        let newer = Date(timeIntervalSince1970: 1_724_820_000)

        let source = RemindersSource(
            snapshotProvider: {
                [
                    ReminderSnapshot(
                        calendarItemIdentifier: "keep",
                        title: "Explicit reminder",
                        dueAt: due,
                        isCompleted: false,
                        lastModifiedAt: newer
                    ),
                    ReminderSnapshot(
                        calendarItemIdentifier: "done",
                        title: "Completed",
                        dueAt: due,
                        isCompleted: true,
                        lastModifiedAt: newer
                    ),
                    ReminderSnapshot(
                        calendarItemIdentifier: "undated",
                        title: "No due",
                        dueAt: nil,
                        isCompleted: false,
                        lastModifiedAt: newer
                    ),
                    ReminderSnapshot(
                        calendarItemIdentifier: "stale",
                        title: "Before cursor",
                        dueAt: due,
                        isCompleted: false,
                        lastModifiedAt: older
                    ),
                ]
            },
            authorisedProvider: { true }
        )

        let cursor = ReminderMapper.cursorKey(
            updatedAt: ReminderMapper.iso8601(Date(timeIntervalSince1970: 1_724_810_000)),
            providerID: "mid"
        )
        let batch = source.changes(cursor: cursor)

        XCTAssertTrue(batch.authorised)
        XCTAssertEqual(batch.items.count, 1)
        XCTAssertEqual(batch.items[0].provider_id, "keep")
        XCTAssertEqual(batch.items[0].provider, "apple_reminders")
        XCTAssertEqual(batch.next_cursor?.source, "apple_reminders")
        XCTAssertTrue(batch.exhausted)
    }

    func testPermissionDeniedReturnsAuthorisedFalseWithoutCrashing() throws {
        let denied = RemindersSource(
            snapshotProvider: { [] },
            authorisedProvider: { false }
        )

        XCTAssertFalse(denied.isReady())
        let changes = denied.changes(cursor: nil)
        XCTAssertFalse(changes.authorised)
        XCTAssertTrue(changes.items.isEmpty)
        XCTAssertTrue(changes.exhausted)
        XCTAssertNil(changes.next_cursor)

        let hooks = PermissionHooks(remindersSource: denied)
        XCTAssertFalse(hooks.capabilities().reminders.authorised)

        let server = BridgeHTTPServer(token: "test-token", remindersSource: denied)
        let result = try server.handleHTTP(
            method: "GET",
            path: "/reminders/changes",
            authorization: "Bearer test-token",
            query: ["cursor": "2026-01-01T00:00:00Z"]
        )
        XCTAssertEqual(result.status, 200)
        let decoded = try JSONDecoder().decode(ReminderChangeBatch.self, from: result.body)
        XCTAssertFalse(decoded.authorised)
        XCTAssertTrue(decoded.items.isEmpty)
    }

    func testExplicitRemindersAreFirstClassIntentSignals() {
        // Documented contract: Apple Reminders are EXPLICIT_REMINDER signals —
        // stronger than inferred email obligations (see attention kinds).
        XCTAssertEqual(ReminderMapper.intentSignalKind, "explicit_reminder")

        let due = Date(timeIntervalSince1970: 1_724_817_600)
        let snapshot = ReminderSnapshot(
            calendarItemIdentifier: "intent-1",
            title: "Send deployment notes to PERSON_81",
            dueAt: due,
            isCompleted: false
        )

        XCTAssertTrue(
            ReminderMapper.shouldIngest(snapshot),
            "Incomplete dated reminders are first-class explicit intent signals"
        )
        let dto = ReminderMapper.map(snapshot)
        XCTAssertEqual(dto?.provider, "apple_reminders")
        XCTAssertEqual(dto?.is_completed, false)
        XCTAssertNotNil(dto?.due_at)
    }
}
