import Foundation

/// Back-compat helper used by scaffold tests and CLI pretty-print.
public struct LocalTransport: Sendable {
    public init() {}

    public func describe(capabilities: CapabilityReport) throws -> String {
        try BridgeJSON.encodePretty(capabilities)
    }
}

public enum TransportError: Error {
    case encodingFailed
}
