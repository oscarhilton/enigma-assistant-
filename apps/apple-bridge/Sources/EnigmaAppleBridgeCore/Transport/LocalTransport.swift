import Foundation

/// Local-only transport stub.
/// Production work (Unix domain socket + bearer auth) lives in ticket M07.
public struct LocalTransport: Sendable {
    public init() {}

    public func describe(capabilities: CapabilityReport) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(capabilities)
        guard let json = String(data: data, encoding: .utf8) else {
            throw TransportError.encodingFailed
        }
        return json
    }
}

public enum TransportError: Error {
    case encodingFailed
}
