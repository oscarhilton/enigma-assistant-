import Contacts
import EnigmaAppleBridgeCore
import XCTest

private struct DeniedContactsStore: ContactsStore {
    func authorizationStatus() -> CNAuthorizationStatus { .denied }
    func requestAccess() async throws -> Bool { false }
    func fetchPeople() throws -> [RawContactPerson] { [] }
}

final class CapabilityReportTests: XCTestCase {
    func testScaffoldCapabilities() throws {
        let report = CapabilityReport.scaffold()
        XCTAssertTrue(report.calendar.available)
        // Live EventKit status varies by machine; scaffold still encodes notes quality.
        XCTAssertEqual(report.notes.quality, "best_effort")

        let json = try LocalTransport().describe(capabilities: report)
        XCTAssertTrue(json.contains("\"calendar\""))
        XCTAssertTrue(json.contains("best_effort"))
    }

    func testUnauthorisedSourcesStillEncodedIndependently() throws {
        let hooks = PermissionHooks(
            calendarIsAuthorised: { false },
            remindersSource: RemindersSource(authorisedProvider: { false }),
            contactsSource: ContactsSource(store: DeniedContactsStore())
        )
        let report = hooks.capabilities()
        XCTAssertFalse(report.calendar.authorised)
        XCTAssertFalse(report.reminders.authorised)
        XCTAssertFalse(report.contacts.authorised)
        XCTAssertFalse(report.notes.authorised)

        let data = try BridgeJSON.encode(report)
        let decoded = try JSONDecoder().decode(CapabilityReport.self, from: data)
        XCTAssertEqual(decoded, report)
    }
}

final class BridgeAuthTests: XCTestCase {
    func testBearerAuthAcceptsMatchingToken() {
        let auth = BridgeAuth(expectedToken: "secret-token")
        XCTAssertTrue(auth.authorize(headerValue: "Bearer secret-token"))
    }

    func testBearerAuthRejectsMissingWrongOrMalformed() {
        let auth = BridgeAuth(expectedToken: "secret-token")
        XCTAssertFalse(auth.authorize(headerValue: nil))
        XCTAssertFalse(auth.authorize(headerValue: "Bearer wrong"))
        XCTAssertFalse(auth.authorize(headerValue: "secret-token"))
        XCTAssertFalse(auth.authorize(headerValue: "Basic secret-token"))
    }
}

final class BridgeHTTPServerTests: XCTestCase {
    private func deniedServer(token: String = "test-token") -> BridgeHTTPServer {
        let deniedCalendar = CalendarSource(isAuthorised: { false }, requestAccess: { false })
        let deniedReminders = RemindersSource(authorisedProvider: { false })
        let deniedContacts = ContactsSource(store: DeniedContactsStore())
        let hooks = PermissionHooks(
            calendarIsAuthorised: { false },
            remindersSource: deniedReminders,
            contactsSource: deniedContacts
        )
        return BridgeHTTPServer(
            token: token,
            permissionHooks: hooks,
            calendarSource: deniedCalendar,
            remindersSource: deniedReminders,
            contactsSource: deniedContacts
        )
    }

    func testCapabilitiesRequiresBearerToken() throws {
        let server = deniedServer()
        let denied = try server.handleHTTP(method: "GET", path: "/capabilities", authorization: nil)
        XCTAssertEqual(denied.status, 401)

        let allowed = try server.handleHTTP(
            method: "GET",
            path: "/capabilities",
            authorization: "Bearer test-token"
        )
        XCTAssertEqual(allowed.status, 200)
        let report = try JSONDecoder().decode(CapabilityReport.self, from: allowed.body)
        XCTAssertTrue(report.calendar.available)
        XCTAssertFalse(report.calendar.authorised)
        XCTAssertEqual(report.notes.quality, "best_effort")
    }

    func testHealthEndpoint() throws {
        let server = deniedServer()
        let result = try server.handleHTTP(
            method: "GET",
            path: "/health",
            authorization: "Bearer test-token"
        )
        XCTAssertEqual(result.status, 200)
        let json = String(decoding: result.body, as: UTF8.self)
        XCTAssertTrue(json.contains("enigma-apple-bridge"))
    }

    func testLoopbackServerRoundTrip() throws {
        var lastError: Error?
        for _ in 0 ..< 8 {
            let port = freeLoopbackPort()
            let token = "integration-token-\(port)"
            let deniedReminders = RemindersSource(authorisedProvider: { false })
            let deniedContacts = ContactsSource(store: DeniedContactsStore())
            let server = BridgeHTTPServer(
                endpoint: .loopback(port: port),
                token: token,
                permissionHooks: PermissionHooks(
                    calendarIsAuthorised: { false },
                    remindersSource: deniedReminders,
                    contactsSource: deniedContacts
                ),
                calendarSource: CalendarSource(isAuthorised: { false }, requestAccess: { false }),
                remindersSource: deniedReminders,
                contactsSource: deniedContacts
            )
            do {
                try server.start()
            } catch let error as BridgeError {
                if case .bindFailed = error {
                    lastError = error
                    continue
                }
                throw error
            }
            defer { server.stop() }

            let url = URL(string: "http://127.0.0.1:\(port)/capabilities")!
            var request = URLRequest(url: url)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            let expectation = expectation(description: "capabilities")
            var statusCode = 0
            var body = Data()

            let task = URLSession.shared.dataTask(with: request) { data, response, error in
                XCTAssertNil(error)
                statusCode = (response as? HTTPURLResponse)?.statusCode ?? -1
                body = data ?? Data()
                expectation.fulfill()
            }
            task.resume()
            wait(for: [expectation], timeout: 5)

            XCTAssertEqual(statusCode, 200)
            let report = try JSONDecoder().decode(CapabilityReport.self, from: body)
            XCTAssertTrue(report.contacts.available)
            return
        }
        XCTFail("Failed to bind loopback server after retries: \(String(describing: lastError))")
    }

    private func freeLoopbackPort() -> UInt16 {
        // Ephemeral range; uniqueness across parallel tests is best-effort.
        UInt16.random(in: 18_000 ... 28_000)
    }
}

final class PermissionHooksTests: XCTestCase {
    func testRequestAuthorisationStubDoesNotThrow() async {
        let hooks = PermissionHooks(
            calendarIsAuthorised: { false },
            calendarRequestAccess: { false },
            remindersSource: RemindersSource(authorisedProvider: { false }),
            contactsSource: ContactsSource(store: DeniedContactsStore())
        )
        let authorised = await hooks.requestAuthorisation(for: .calendar)
        XCTAssertFalse(authorised)
        let notes = await hooks.requestAuthorisation(for: .notes)
        XCTAssertFalse(notes)
    }

    func testCalendarAuthorisedWhenInjected() {
        let hooks = PermissionHooks(
            calendarIsAuthorised: { true },
            remindersSource: RemindersSource(authorisedProvider: { false }),
            contactsSource: ContactsSource(store: DeniedContactsStore())
        )
        XCTAssertTrue(hooks.isAuthorised(.calendar))
        XCTAssertFalse(hooks.isAuthorised(.reminders))
        XCTAssertFalse(hooks.isAuthorised(.contacts))
        XCTAssertTrue(hooks.capabilities().calendar.authorised)
    }
}
