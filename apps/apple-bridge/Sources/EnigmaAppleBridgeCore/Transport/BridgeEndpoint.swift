import Foundation

/// Listen address for the Apple Bridge (ADR-002): loopback TCP or Unix domain socket.
public enum BridgeEndpoint: Sendable, Equatable {
    /// Bind `127.0.0.1` only — never `0.0.0.0`.
    case loopback(port: UInt16)
    case unixSocket(path: String)

    public static let defaultLoopback = BridgeEndpoint.loopback(port: 8765)
}

/// JSON helpers shared by the HTTP layer and tests.
public enum BridgeJSON {
    public static func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }

    public static func encodePretty<T: Encodable>(_ value: T) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(value)
        guard let json = String(data: data, encoding: .utf8) else {
            throw BridgeError.encodingFailed
        }
        return json
    }
}
