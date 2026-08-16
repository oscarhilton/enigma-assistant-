import EnigmaAppleBridgeCore
import Foundation

@main
struct EnigmaAppleBridgeMain {
    static func main() async throws {
        let args = Array(CommandLine.arguments.dropFirst())
        let endpoint = try parseEndpoint(args: args)
        let token = try BridgeTokenStore.load()
        let server = BridgeHTTPServer(endpoint: endpoint, token: token)

        try server.start()
        fputs("enigma-apple-bridge listening on \(describe(endpoint)) (local only)\n", stderr)

        // Keep the process alive until terminated.
        while true {
            try await Task.sleep(nanoseconds: 60 * 1_000_000_000)
        }
    }

    private static func parseEndpoint(args: [String]) throws -> BridgeEndpoint {
        if let idx = args.firstIndex(of: "--unix-socket") {
            guard args.indices.contains(idx + 1) else {
                throw BridgeError.bindFailed("--unix-socket requires a path argument")
            }
            return .unixSocket(path: args[idx + 1])
        }
        if let idx = args.firstIndex(of: "--port") {
            guard args.indices.contains(idx + 1) else {
                throw BridgeError.bindFailed("--port requires a numeric argument")
            }
            guard let port = UInt16(args[idx + 1]) else {
                throw BridgeError.bindFailed("invalid --port value \(args[idx + 1])")
            }
            return .loopback(port: port)
        }
        return .defaultLoopback
    }

    private static func describe(_ endpoint: BridgeEndpoint) -> String {
        switch endpoint {
        case let .loopback(port):
            return "127.0.0.1:\(port)"
        case let .unixSocket(path):
            return "unix:\(path)"
        }
    }
}
