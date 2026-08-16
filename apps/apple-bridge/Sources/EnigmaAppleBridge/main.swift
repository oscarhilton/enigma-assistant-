import EnigmaAppleBridgeCore
import Foundation

@main
struct EnigmaAppleBridgeMain {
    static func main() async throws {
        let transport = LocalTransport()
        let capabilities = CapabilityReport.scaffold()
        print(try transport.describe(capabilities: capabilities))
    }
}
