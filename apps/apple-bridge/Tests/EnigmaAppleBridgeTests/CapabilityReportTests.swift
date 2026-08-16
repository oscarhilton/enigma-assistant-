import EnigmaAppleBridgeCore
import XCTest

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
        let hooks = PermissionHooks(calendarIsAuthorised: { false })
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
        let denied = CalendarSource(isAuthorised: { false }, requestAccess: { false })
        let hooks = PermissionHooks(calendarIsAuthorised: { false })
        return BridgeHTTPServer(token: token, permissionHooks: hooks, calendarSource: denied)
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
        let port = freeLoopbackPort()
        let token = "integration-token-\(port)"
        let server = BridgeHTTPServer(
            endpoint: .loopback(port: port),
            token: token,
            permissionHooks: PermissionHooks(calendarIsAuthorised: { false }),
            calendarSource: CalendarSource(isAuthorised: { false }, requestAccess: { false })
        )
        try server.start()
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
        XCTAssertTrue(report.reminders.available)
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
            calendarRequestAccess: { false }
        )
        let authorised = await hooks.requestAuthorisation(for: .calendar)
        XCTAssertFalse(authorised)
        let notes = await hooks.requestAuthorisation(for: .notes)
        XCTAssertFalse(notes)
    }

    func testCalendarAuthorisedWhenInjected() {
        let hooks = PermissionHooks(calendarIsAuthorised: { true })
        XCTAssertTrue(hooks.isAuthorised(.calendar))
        XCTAssertFalse(hooks.isAuthorised(.reminders))
        XCTAssertTrue(hooks.capabilities().calendar.authorised)
    }
}
