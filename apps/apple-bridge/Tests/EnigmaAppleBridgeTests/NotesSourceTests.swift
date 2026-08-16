import EnigmaAppleBridgeCore
import XCTest

final class NoteMapperTests: XCTestCase {
    private let modified = Date(timeIntervalSince1970: 1_787_100_000)

    func testMapsSnapshotToPrivateNoteShape() {
        let snapshot = NoteSnapshot(
            noteIdentifier: "note-1",
            title: "Project ideas",
            bodyText: "Keep this local.\n\nSecond paragraph.",
            folder: "Work",
            createdAt: modified,
            modifiedAt: modified
        )

        let dto = NoteMapper.map(snapshot)
        XCTAssertEqual(dto.provider, "apple_notes")
        XCTAssertEqual(dto.provider_note_id, "note-1")
        XCTAssertEqual(dto.id, "apple_notes:note-1")
        XCTAssertEqual(dto.title, "Project ideas")
        XCTAssertEqual(dto.folder, "Work")
        XCTAssertEqual(dto.body_text, "Keep this local.\n\nSecond paragraph.")
        XCTAssertEqual(dto.metadata["quality"], "best_effort")
        XCTAssertEqual(dto.metadata["access"], "apple_events")
        XCTAssertEqual(dto.metadata["wholesale_body_remote_safe"], "false")
        XCTAssertEqual(dto.metadata["remote_privacy_default"], "high")
        XCTAssertEqual(NoteMapper.quality, "best_effort")
    }

    func testChangeBatchCursorSkipsAlreadySeenNotes() {
        let older = NoteSnapshot(
            noteIdentifier: "a",
            title: "Older",
            bodyText: "a",
            modifiedAt: Date(timeIntervalSince1970: 1_000)
        )
        let newer = NoteSnapshot(
            noteIdentifier: "b",
            title: "Newer",
            bodyText: "b",
            modifiedAt: Date(timeIntervalSince1970: 2_000)
        )
        let first = NoteMapper.changeBatch(from: [older, newer], cursor: nil)
        let cursor = try! XCTUnwrap(first.next_cursor?.value)
        let second = NoteMapper.changeBatch(from: [older, newer], cursor: cursor)
        XCTAssertTrue(second.items.isEmpty)

        let olderKey = NoteMapper.cursorKey(
            updatedAt: NoteMapper.iso8601(older.modifiedAt),
            providerNoteID: older.noteIdentifier
        )
        let afterOlder = NoteMapper.changeBatch(from: [older, newer], cursor: olderKey)
        XCTAssertEqual(afterOlder.items.map(\.provider_note_id), ["b"])
    }
}

final class NotesSourceTests: XCTestCase {
    func testOptInRequiredBeforeAuthorisation() async {
        let events = MockNotesAppleEventsClient(automationAllowed: true, snapshots: [])
        let source = NotesSource(
            events: events,
            optInProvider: { false }
        )
        XCTAssertFalse(source.isOptedIn())
        XCTAssertFalse(source.isAuthorised())
        let authorised = await source.requestAuthorisation()
        XCTAssertFalse(authorised)
    }

    func testAutomationPermissionSeparateFromOptIn() {
        let denied = MockNotesAppleEventsClient(automationAllowed: false, snapshots: [])
        let source = NotesSource(
            events: denied,
            optInProvider: { true }
        )
        XCTAssertTrue(source.isOptedIn())
        XCTAssertFalse(source.isAuthorised())
    }

    func testListAndReadViaMockedAppleEvents() throws {
        let snapshots = [
            NoteSnapshot(
                noteIdentifier: "n1",
                title: "Alpha",
                bodyText: "Body one",
                folder: "Inbox"
            ),
            NoteSnapshot(
                noteIdentifier: "n2",
                title: "Beta",
                bodyText: "Body two"
            ),
        ]
        let events = MockNotesAppleEventsClient(automationAllowed: true, snapshots: snapshots)
        let source = NotesSource(events: events, optInProvider: { true })

        let refs = try source.listNotes()
        XCTAssertEqual(refs.map(\.id), ["n1", "n2"])
        XCTAssertEqual(refs.map(\.title), ["Alpha", "Beta"])

        let note = try source.readNote(id: "n1")
        XCTAssertEqual(note.title, "Alpha")
        XCTAssertEqual(note.bodyText, "Body one")
        XCTAssertEqual(note.folder, "Inbox")
    }

    func testChangesMapsPrivateNotesWhenAuthorised() {
        let snapshots = [
            NoteSnapshot(
                noteIdentifier: "n1",
                title: "Local diary",
                bodyText: "Never ship wholesale.",
                modifiedAt: Date(timeIntervalSince1970: 1_787_000_000)
            ),
        ]
        let source = NotesSource(
            events: MockNotesAppleEventsClient(automationAllowed: true, snapshots: snapshots),
            optInProvider: { true },
            authorisedProvider: { true },
            snapshotProvider: { snapshots }
        )
        let batch = source.changes(cursor: nil)
        XCTAssertTrue(batch.authorised)
        XCTAssertEqual(batch.items.count, 1)
        XCTAssertEqual(batch.items[0].provider, "apple_notes")
        XCTAssertEqual(batch.items[0].body_text, "Never ship wholesale.")
        XCTAssertEqual(batch.items[0].metadata["wholesale_body_remote_safe"], "false")
    }

    func testUnauthorisedChangesDoNotFetch() {
        let source = NotesSource(
            events: MockNotesAppleEventsClient(
                automationAllowed: false,
                snapshots: [
                    NoteSnapshot(noteIdentifier: "x", title: "x", bodyText: "x"),
                ]
            ),
            optInProvider: { true },
            authorisedProvider: { false },
            snapshotProvider: {
                XCTFail("should not fetch when unauthorised")
                return []
            }
        )
        let batch = source.changes(cursor: nil)
        XCTAssertFalse(batch.authorised)
        XCTAssertTrue(batch.items.isEmpty)
        XCTAssertTrue(batch.exhausted)
    }

    func testParseAppleEventsPayload() throws {
        let rs = String(UnicodeScalar(30)!)
        let fs = String(UnicodeScalar(31)!)
        let raw = "id-1\(fs)Title\(fs)Folder\(fs)\(fs)\(fs)Hello body\(rs)"
        let snapshots = try ScriptedNotesAppleEventsClient.parseSnapshots(from: raw)
        XCTAssertEqual(snapshots.count, 1)
        XCTAssertEqual(snapshots[0].noteIdentifier, "id-1")
        XCTAssertEqual(snapshots[0].title, "Title")
        XCTAssertEqual(snapshots[0].folder, "Folder")
        XCTAssertEqual(snapshots[0].bodyText, "Hello body")
    }
}

final class NotesRelevanceTests: XCTestCase {
    func testLocalRelevanceStubNeverAutoShipsWholesaleBody() {
        let body = "Secret diary line that must stay local."
        XCTAssertEqual(NotesLocalRelevance.detectRelevantPassages(bodyText: body), [])
        XCTAssertFalse(
            NotesLocalRelevance.mayTransmitRemotely(fullBody: body, candidatePassage: body)
        )
        XCTAssertFalse(
            NotesLocalRelevance.mayTransmitRemotely(
                fullBody: body,
                candidatePassage: "Secret diary"
            )
        )
        XCTAssertFalse(
            NotesLocalRelevance.mayTransmitRemotely(fullBody: body, candidatePassage: nil)
        )
    }
}

final class NotesHTTPRouteTests: XCTestCase {
    func testNotesChangesRequiresBearerToken() throws {
        let source = NotesSource(
            events: MockNotesAppleEventsClient(),
            optInProvider: { true },
            authorisedProvider: { true },
            snapshotProvider: { [] }
        )
        let server = BridgeHTTPServer(token: "test-token", notesSource: source)
        let denied = try server.handleHTTP(method: "GET", path: "/notes/changes", authorization: nil)
        XCTAssertEqual(denied.status, 401)
    }

    func testNotesChangesReturnsMappedItemsWithCursor() throws {
        let modified = Date(timeIntervalSince1970: 1_787_000_000)
        let source = NotesSource(
            events: MockNotesAppleEventsClient(),
            optInProvider: { true },
            authorisedProvider: { true },
            snapshotProvider: {
                [
                    NoteSnapshot(
                        noteIdentifier: "n1",
                        title: "Ship checklist",
                        bodyText: "Local only body",
                        modifiedAt: modified
                    ),
                ]
            }
        )
        let server = BridgeHTTPServer(token: "test-token", notesSource: source)
        let result = try server.handleHTTP(
            method: "GET",
            path: "/notes/changes",
            authorization: "Bearer test-token"
        )
        XCTAssertEqual(result.status, 200)
        let batch = try JSONDecoder().decode(NoteChangeBatch.self, from: result.body)
        XCTAssertTrue(batch.authorised)
        XCTAssertEqual(batch.items.count, 1)
        XCTAssertEqual(batch.items[0].provider, "apple_notes")
        XCTAssertEqual(batch.items[0].title, "Ship checklist")
        XCTAssertNotNil(batch.next_cursor)
    }

    func testNotesChangesUnauthorisedDoesNotCrash() throws {
        let source = NotesSource(
            events: MockNotesAppleEventsClient(),
            optInProvider: { false },
            authorisedProvider: { false },
            snapshotProvider: {
                XCTFail("should not fetch when unauthorised")
                return []
            }
        )
        let server = BridgeHTTPServer(token: "test-token", notesSource: source)
        let result = try server.handleHTTP(
            method: "GET",
            path: "/notes/changes",
            authorization: "Bearer test-token",
            query: ["cursor": "anything"]
        )
        XCTAssertEqual(result.status, 200)
        let batch = try JSONDecoder().decode(NoteChangeBatch.self, from: result.body)
        XCTAssertFalse(batch.authorised)
        XCTAssertTrue(batch.items.isEmpty)
        XCTAssertTrue(batch.exhausted)
    }

    func testCapabilitiesMarkNotesBestEffortAndSeparateAuth() throws {
        let source = NotesSource(
            events: MockNotesAppleEventsClient(automationAllowed: true),
            optInProvider: { true },
            authorisedProvider: { true }
        )
        let server = BridgeHTTPServer(token: "test-token", notesSource: source)
        let result = try server.handleHTTP(
            method: "GET",
            path: "/capabilities",
            authorization: "Bearer test-token"
        )
        let report = try JSONDecoder().decode(CapabilityReport.self, from: result.body)
        XCTAssertEqual(report.notes.quality, "best_effort")
        XCTAssertTrue(report.notes.authorised)
        XCTAssertFalse(report.calendar.authorised)
        XCTAssertFalse(report.reminders.authorised)
        XCTAssertFalse(report.contacts.authorised)
    }

    func testQueryParserExtractsCursor() {
        let query = BridgeHTTPServer.parseQuery("cursor=abc%7Cdef&other=1")
        XCTAssertEqual(query["cursor"], "abc|def")
        XCTAssertEqual(query["other"], "1")
    }
}
