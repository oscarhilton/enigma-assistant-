import Foundation
import Network

/// Local-only HTTP server for the Apple Bridge.
///
/// Binds to `127.0.0.1` or a Unix domain socket, requires bearer auth, and exposes
/// `GET /health`, `GET /capabilities`, `GET /calendar/*`, `GET /reminders/changes`,
/// and `GET /notes/changes`. Never calls LLM providers.
public final class BridgeHTTPServer: @unchecked Sendable {
    public let endpoint: BridgeEndpoint
    private let auth: BridgeAuth
    private let permissionHooks: PermissionHooks
    private let calendarSource: CalendarSource
    private let remindersSource: RemindersSource
    private let notesSource: NotesSource
    private var listener: NWListener?
    private let queue = DispatchQueue(label: "com.personal-enigma.bridge-http")

    public init(
        endpoint: BridgeEndpoint = .defaultLoopback,
        token: String,
        permissionHooks: PermissionHooks? = nil,
        calendarSource: CalendarSource = CalendarSource(),
        remindersSource: RemindersSource = RemindersSource(),
        notesSource: NotesSource = NotesSource()
    ) {
        self.endpoint = endpoint
        self.auth = BridgeAuth(expectedToken: token)
        self.calendarSource = calendarSource
        self.remindersSource = remindersSource
        self.notesSource = notesSource
        self.permissionHooks = permissionHooks ?? PermissionHooks(
            remindersSource: remindersSource,
            notesSource: notesSource
        )
    }

    public var isRunning: Bool { listener != nil }

    public func start() throws {
        guard listener == nil else { return }

        let parameters: NWParameters
        let nwListener: NWListener

        switch endpoint {
        case let .loopback(port):
            guard let nwPort = NWEndpoint.Port(rawValue: port) else {
                throw BridgeError.bindFailed("invalid port \(port)")
            }
            parameters = NWParameters.tcp
            parameters.requiredLocalEndpoint = NWEndpoint.hostPort(
                host: NWEndpoint.Host("127.0.0.1"),
                port: nwPort
            )
            parameters.allowLocalEndpointReuse = true
            do {
                nwListener = try NWListener(using: parameters)
            } catch {
                throw BridgeError.bindFailed(String(describing: error))
            }

        case let .unixSocket(path):
            if FileManager.default.fileExists(atPath: path) {
                try? FileManager.default.removeItem(atPath: path)
            }
            parameters = NWParameters.tcp
            parameters.requiredLocalEndpoint = NWEndpoint.unix(path: path)
            parameters.allowLocalEndpointReuse = true
            do {
                nwListener = try NWListener(using: parameters)
            } catch {
                throw BridgeError.bindFailed(String(describing: error))
            }
        }

        nwListener.newConnectionHandler = { [weak self] connection in
            self?.handle(connection: connection)
        }

        let started = DispatchSemaphore(value: 0)
        var startError: String?

        nwListener.stateUpdateHandler = { state in
            switch state {
            case .ready:
                started.signal()
            case let .failed(error):
                startError = String(describing: error)
                started.signal()
            case .cancelled:
                break
            default:
                break
            }
        }

        listener = nwListener
        nwListener.start(queue: queue)

        let waitResult = started.wait(timeout: .now() + 5)
        if waitResult == .timedOut {
            stop()
            throw BridgeError.bindFailed("listener start timed out")
        }
        if let startError {
            stop()
            throw BridgeError.bindFailed(startError)
        }
    }

    public func stop() {
        listener?.cancel()
        listener = nil
        if case let .unixSocket(path) = endpoint {
            try? FileManager.default.removeItem(atPath: path)
        }
    }

    /// Handle a single HTTP request (test helper / in-process routing).
    public func handleHTTP(
        method: String,
        path: String,
        authorization: String?,
        query: [String: String] = [:]
    ) throws -> (
        status: Int,
        contentType: String,
        body: Data
    ) {
        guard auth.authorize(headerValue: authorization) else {
            return (
                401,
                "application/json",
                Data(#"{"error":"unauthorized"}"#.utf8)
            )
        }

        switch (method.uppercased(), path) {
        case ("GET", "/health"):
            return (
                200,
                "application/json",
                Data(#"{"status":"ok","service":"enigma-apple-bridge"}"#.utf8)
            )
        case ("GET", "/capabilities"):
            let report = permissionHooks.capabilities()
            let body = try BridgeJSON.encode(report)
            return (200, "application/json", body)
        case ("GET", "/calendar/changes"):
            let cursor = query["cursor"]
            let selected = Self.parseCalendarIDs(query["calendar_ids"] ?? query["calendars"])
            let response = calendarSource.getChanges(cursor: cursor, selectedCalendarIDs: selected)
            let body = try BridgeJSON.encode(response)
            return (200, "application/json", body)
        case ("GET", "/calendar/calendars"):
            struct CalendarsPayload: Encodable {
                var authorised: Bool
                var calendars: [CalendarInfoDTO]
            }
            let typed = CalendarsPayload(
                authorised: calendarSource.isReady(),
                calendars: calendarSource.listCalendars()
            )
            let body = try BridgeJSON.encode(typed)
            return (200, "application/json", body)
        case ("GET", "/reminders/changes"):
            let cursor = query["cursor"]
            let response = remindersSource.changes(cursor: cursor)
            let body = try BridgeJSON.encode(response)
            return (200, "application/json", body)
        case ("GET", "/notes/changes"):
            let cursor = query["cursor"]
            let response = notesSource.changes(cursor: cursor)
            let body = try BridgeJSON.encode(response)
            return (200, "application/json", body)
        default:
            return (
                404,
                "application/json",
                Data(#"{"error":"not_found"}"#.utf8)
            )
        }
    }

    private func handle(connection: NWConnection) {
        connection.start(queue: queue)
        receive(on: connection, buffer: Data())
    }

    private func receive(on connection: NWConnection, buffer: Data) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 64 * 1024) { [weak self] data, _, isComplete, error in
            guard let self else {
                connection.cancel()
                return
            }
            if error != nil {
                connection.cancel()
                return
            }

            var next = buffer
            if let data, !data.isEmpty {
                next.append(data)
            }

            if let headerEnd = next.range(of: Data("\r\n\r\n".utf8)) {
                let headerData = next.subdata(in: next.startIndex ..< headerEnd.lowerBound)
                let response = self.response(for: headerData)
                self.send(response, on: connection)
                return
            }

            if isComplete {
                connection.cancel()
                return
            }

            if next.count > 64 * 1024 {
                connection.cancel()
                return
            }

            self.receive(on: connection, buffer: next)
        }
    }

    private func response(for headerData: Data) -> Data {
        guard let headerText = String(data: headerData, encoding: .utf8) else {
            return httpResponse(status: 400, contentType: "application/json", body: Data(#"{"error":"bad_request"}"#.utf8))
        }

        let normalized = headerText.replacingOccurrences(of: "\r\n", with: "\n")
        let lines = normalized.split(separator: "\n", omittingEmptySubsequences: false)
        guard let requestLine = lines.first else {
            return httpResponse(status: 400, contentType: "application/json", body: Data(#"{"error":"bad_request"}"#.utf8))
        }

        let parts = requestLine.split(separator: " ")
        guard parts.count >= 2 else {
            return httpResponse(status: 400, contentType: "application/json", body: Data(#"{"error":"bad_request"}"#.utf8))
        }

        let method = String(parts[0])
        let rawTarget = String(parts[1])
        let pathAndQuery = rawTarget.split(separator: "?", maxSplits: 1, omittingEmptySubsequences: false)
        let path = String(pathAndQuery.first ?? Substring(rawTarget))
        let query = Self.parseQuery(pathAndQuery.count > 1 ? String(pathAndQuery[1]) : nil)

        var authorization: String?
        for line in lines.dropFirst() {
            let lower = line.lowercased()
            if lower.hasPrefix("authorization:") {
                let value = line.dropFirst("authorization:".count)
                authorization = value.trimmingCharacters(in: .whitespaces)
            }
        }

        do {
            let result = try handleHTTP(
                method: method,
                path: path,
                authorization: authorization,
                query: query
            )
            return httpResponse(status: result.status, contentType: result.contentType, body: result.body)
        } catch {
            return httpResponse(status: 500, contentType: "application/json", body: Data(#"{"error":"internal"}"#.utf8))
        }
    }

    private func send(_ data: Data, on connection: NWConnection) {
        connection.send(content: data, completion: .contentProcessed { _ in
            connection.cancel()
        })
    }

    private func httpResponse(status: Int, contentType: String, body: Data) -> Data {
        let reason: String
        switch status {
        case 200: reason = "OK"
        case 401: reason = "Unauthorized"
        case 404: reason = "Not Found"
        case 400: reason = "Bad Request"
        default: reason = "Error"
        }
        let header = """
        HTTP/1.1 \(status) \(reason)\r
        Content-Type: \(contentType)\r
        Content-Length: \(body.count)\r
        Connection: close\r
        \r

        """
        var response = Data(header.utf8)
        response.append(body)
        return response
    }

    public static func parseQuery(_ raw: String?) -> [String: String] {
        guard let raw, !raw.isEmpty else { return [:] }
        var result: [String: String] = [:]
        for pair in raw.split(separator: "&") {
            let parts = pair.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
            guard let keyPart = parts.first else { continue }
            let key = String(keyPart).removingPercentEncoding ?? String(keyPart)
            let value: String
            if parts.count > 1 {
                let rawValue = String(parts[1])
                value = rawValue.removingPercentEncoding ?? rawValue
            } else {
                value = ""
            }
            result[key] = value
        }
        return result
    }

    static func parseCalendarIDs(_ raw: String?) -> Set<String> {
        guard let raw, !raw.isEmpty else { return [] }
        return Set(
            raw.split(separator: ",")
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }
        )
    }
}
