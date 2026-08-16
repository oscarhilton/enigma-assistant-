import Foundation
import Security

/// Bearer-token gate for the local bridge (ADR-002).
public struct BridgeAuth: Sendable {
    public let expectedToken: String

    public init(expectedToken: String) {
        self.expectedToken = expectedToken
    }

    /// Returns true when `Authorization: Bearer <token>` matches the expected secret.
    public func authorize(headerValue: String?) -> Bool {
        guard let headerValue else { return false }
        let prefix = "Bearer "
        guard headerValue.hasPrefix(prefix) else { return false }
        let presented = String(headerValue.dropFirst(prefix.count))
        return constantTimeEquals(presented, expectedToken)
    }

    private func constantTimeEquals(_ lhs: String, _ rhs: String) -> Bool {
        let left = Array(lhs.utf8)
        let right = Array(rhs.utf8)
        guard left.count == right.count else { return false }
        var diff: UInt8 = 0
        for i in left.indices {
            diff |= left[i] ^ right[i]
        }
        return diff == 0
    }
}

/// Where the bridge loads its shared secret.
///
/// Core generates the token at install time and stores it in the macOS Keychain
/// (see `personal_enigma.api.bridge`). The bridge reads that same secret; for
/// local tests, `ENIGMA_BRIDGE_TOKEN` overrides Keychain lookup.
public enum BridgeTokenStore {
    public static let keychainService = "com.personal-enigma.apple-bridge"
    public static let keychainAccount = "bridge-bearer-token"
    public static let environmentKey = "ENIGMA_BRIDGE_TOKEN"

    public static func load() throws -> String {
        if let env = ProcessInfo.processInfo.environment[environmentKey], !env.isEmpty {
            return env
        }
        if let keychain = try readKeychainToken() {
            return keychain
        }
        throw BridgeError.tokenNotConfigured
    }

    /// Best-effort Keychain read. Returns nil when the item is missing.
    public static func readKeychainToken() throws -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess else {
            throw BridgeError.keychainReadFailed(status)
        }
        guard let data = item as? Data, let token = String(data: data, encoding: .utf8), !token.isEmpty else {
            return nil
        }
        return token
    }
}

public enum BridgeError: Error, Equatable {
    case tokenNotConfigured
    case keychainReadFailed(OSStatus)
    case bindFailed(String)
    case encodingFailed
    case invalidRequest
}
