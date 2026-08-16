import Contacts
import EnigmaAppleBridgeCore
import XCTest

final class ContactsSourceTests: XCTestCase {
    func testMapsRawContactToPrivatePersonShape() throws {
        let raw = RawContactPerson(
            providerContactId: "AB-joseph-1",
            displayName: "Joseph Atkinson",
            aliases: ["Joe"],
            emailAddresses: ["joe@example.com"],
            phoneNumbers: ["+1-555-0100"],
            organisations: ["Example Org"]
        )
        let dto = ContactPersonDTO(from: raw)

        XCTAssertEqual(dto.displayName, "Joseph Atkinson")
        XCTAssertEqual(dto.aliases, ["Joe"])
        XCTAssertEqual(dto.emailAddresses, ["joe@example.com"])
        XCTAssertEqual(dto.providerIds["apple_contacts"], "AB-joseph-1")
        XCTAssertEqual(dto.id, ContactIdentity.uuidString(from: "AB-joseph-1"))

        let data = try BridgeJSON.encode(dto)
        let json = String(decoding: data, as: UTF8.self)
        XCTAssertTrue(json.contains("\"display_name\""))
        XCTAssertTrue(json.contains("\"email_addresses\""))
        XCTAssertTrue(json.contains("\"provider_ids\""))
    }

    func testDeniedAccessReturnsAuthorisedFalseWithoutItems() throws {
        let source = ContactsSource(store: MockContactsStore(status: .denied, people: [
            RawContactPerson(providerContactId: "should-not-appear", displayName: "Hidden"),
        ]))
        let batch = try source.changes(since: nil)
        XCTAssertFalse(batch.authorised)
        XCTAssertTrue(batch.items.isEmpty)
        XCTAssertTrue(batch.exhausted)
    }

    func testChangesReturnsPeopleAndStableCursor() throws {
        let people = [
            RawContactPerson(
                providerContactId: "c1",
                displayName: "Joseph Atkinson",
                aliases: ["Joe"],
                emailAddresses: ["joe@example.com"]
            ),
        ]
        let source = ContactsSource(store: MockContactsStore(status: .authorized, people: people))

        let first = try source.changes(since: nil)
        XCTAssertTrue(first.authorised)
        XCTAssertEqual(first.items.count, 1)
        XCTAssertEqual(first.items[0].displayName, "Joseph Atkinson")
        let cursor = try XCTUnwrap(first.nextCursor?.value)

        let second = try source.changes(since: cursor)
        XCTAssertTrue(second.authorised)
        XCTAssertTrue(second.items.isEmpty)
        XCTAssertEqual(second.nextCursor?.value, cursor)
    }

    func testContactsChangesRouteRequiresBearerAndReturnsBatch() throws {
        let store = MockContactsStore(status: .authorized, people: [
            RawContactPerson(
                providerContactId: "route-1",
                displayName: "Ada",
                emailAddresses: ["ada@example.com"]
            ),
        ])
        let server = BridgeHTTPServer(
            token: "contacts-token",
            contactsSource: ContactsSource(store: store)
        )

        let denied = try server.handleHTTP(
            method: "GET",
            path: "/contacts/changes",
            authorization: nil
        )
        XCTAssertEqual(denied.status, 401)

        let allowed = try server.handleHTTP(
            method: "GET",
            path: "/contacts/changes",
            authorization: "Bearer contacts-token"
        )
        XCTAssertEqual(allowed.status, 200)
        let batch = try JSONDecoder().decode(ContactsChangeBatch.self, from: allowed.body)
        XCTAssertTrue(batch.authorised)
        XCTAssertEqual(batch.items.count, 1)
        XCTAssertEqual(batch.items[0].emailAddresses, ["ada@example.com"])
    }
}

private struct MockContactsStore: ContactsStore {
    let status: CNAuthorizationStatus
    let people: [RawContactPerson]

    func authorizationStatus() -> CNAuthorizationStatus { status }

    func requestAccess() async throws -> Bool { status == .authorized }

    func fetchPeople() throws -> [RawContactPerson] { people }
}
