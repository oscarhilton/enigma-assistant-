import CryptoKit
import Foundation
@preconcurrency import Contacts

/// Contacts.framework adapter — read-only, maps to PrivatePerson-shaped JSON for Core.
public struct ContactsSource: Sendable {
    private let store: ContactsStore

    public init(store: ContactsStore = SystemContactsStore()) {
        self.store = store
    }

    public func isReady() -> Bool {
        store.authorizationStatus() == .authorized
    }

    public func isAuthorised() -> Bool {
        isReady()
    }

    /// Prompt for Contacts access via `CNContactStore`. Denied access does not abort the bridge.
    @discardableResult
    public func requestAccess() async -> Bool {
        do {
            return try await store.requestAccess()
        } catch {
            return false
        }
    }

    /// Incremental-ish contact export. Cursor is an opaque digest of the last full snapshot.
    public func changes(since cursor: String?) throws -> ContactsChangeBatch {
        guard isAuthorised() else {
            return ContactsChangeBatch(
                items: [],
                nextCursor: nil,
                exhausted: true,
                authorised: false
            )
        }

        let people = try store.fetchPeople().map(ContactPersonDTO.init(from:))
        let snapshot = ContactsSnapshotCursor.digest(for: people)

        if let cursor, cursor == snapshot {
            return ContactsChangeBatch(
                items: [],
                nextCursor: SyncCursorDTO(value: snapshot, source: "apple_contacts"),
                exhausted: true,
                authorised: true
            )
        }

        return ContactsChangeBatch(
            items: people,
            nextCursor: SyncCursorDTO(value: snapshot, source: "apple_contacts"),
            exhausted: true,
            authorised: true
        )
    }
}

// MARK: - DTOs (PrivatePerson wire shape)

public struct SyncCursorDTO: Codable, Equatable, Sendable {
    public var value: String
    public var source: String?

    public init(value: String, source: String? = "apple_contacts") {
        self.value = value
        self.source = source
    }
}

public struct ContactsChangeBatch: Codable, Equatable, Sendable {
    public var items: [ContactPersonDTO]
    public var nextCursor: SyncCursorDTO?
    public var exhausted: Bool
    public var authorised: Bool

    public init(
        items: [ContactPersonDTO],
        nextCursor: SyncCursorDTO?,
        exhausted: Bool,
        authorised: Bool
    ) {
        self.items = items
        self.nextCursor = nextCursor
        self.exhausted = exhausted
        self.authorised = authorised
    }

    enum CodingKeys: String, CodingKey {
        case items
        case nextCursor = "next_cursor"
        case exhausted
        case authorised
    }
}

/// Wire DTO matching `PrivatePerson` fields for Core ingestion.
public struct ContactPersonDTO: Codable, Equatable, Sendable {
    public var id: String
    public var displayName: String?
    public var aliases: [String]
    public var emailAddresses: [String]
    public var phoneNumbers: [String]
    public var organisations: [String]
    public var providerIds: [String: String]

    public init(
        id: String,
        displayName: String?,
        aliases: [String],
        emailAddresses: [String],
        phoneNumbers: [String],
        organisations: [String],
        providerIds: [String: String]
    ) {
        self.id = id
        self.displayName = displayName
        self.aliases = aliases
        self.emailAddresses = emailAddresses
        self.phoneNumbers = phoneNumbers
        self.organisations = organisations
        self.providerIds = providerIds
    }

    public init(from raw: RawContactPerson) {
        self.id = ContactIdentity.uuidString(from: raw.providerContactId)
        self.displayName = raw.displayName
        self.aliases = raw.aliases
        self.emailAddresses = raw.emailAddresses
        self.phoneNumbers = raw.phoneNumbers
        self.organisations = raw.organisations
        self.providerIds = ["apple_contacts": raw.providerContactId]
    }

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case aliases
        case emailAddresses = "email_addresses"
        case phoneNumbers = "phone_numbers"
        case organisations
        case providerIds = "provider_ids"
    }
}

/// Normalised contact fields before UUID / provider_ids wrapping (testable without CNContact).
public struct RawContactPerson: Equatable, Sendable {
    public var providerContactId: String
    public var displayName: String?
    public var aliases: [String]
    public var emailAddresses: [String]
    public var phoneNumbers: [String]
    public var organisations: [String]

    public init(
        providerContactId: String,
        displayName: String? = nil,
        aliases: [String] = [],
        emailAddresses: [String] = [],
        phoneNumbers: [String] = [],
        organisations: [String] = []
    ) {
        self.providerContactId = providerContactId
        self.displayName = displayName
        self.aliases = aliases
        self.emailAddresses = emailAddresses
        self.phoneNumbers = phoneNumbers
        self.organisations = organisations
    }
}

public enum ContactIdentity {
    /// Deterministic UUID string from an Apple contact identifier (stable across syncs).
    public static func uuidString(from providerContactId: String) -> String {
        let digest = SHA256.hash(data: Data("enigma.apple_contacts:\(providerContactId)".utf8))
        var bytes = Array(digest.prefix(16))
        bytes[6] = (bytes[6] & 0x0F) | 0x40
        bytes[8] = (bytes[8] & 0x3F) | 0x80
        let uuid = UUID(
            uuid: (
                bytes[0], bytes[1], bytes[2], bytes[3],
                bytes[4], bytes[5], bytes[6], bytes[7],
                bytes[8], bytes[9], bytes[10], bytes[11],
                bytes[12], bytes[13], bytes[14], bytes[15]
            )
        )
        return uuid.uuidString.lowercased()
    }
}

enum ContactsSnapshotCursor {
    static func digest(for people: [ContactPersonDTO]) -> String {
        let material = people
            .map { person in
                let emails = person.emailAddresses.sorted().joined(separator: ",")
                return "\(person.providerIds["apple_contacts"] ?? person.id)|\(person.displayName ?? "")|\(emails)"
            }
            .sorted()
            .joined(separator: "\n")
        let digest = SHA256.hash(data: Data(material.utf8))
        return digest.map { String(format: "%02x", $0) }.joined()
    }
}

// MARK: - Store abstraction

public protocol ContactsStore: Sendable {
    func authorizationStatus() -> CNAuthorizationStatus
    func requestAccess() async throws -> Bool
    func fetchPeople() throws -> [RawContactPerson]
}

public final class SystemContactsStore: ContactsStore, @unchecked Sendable {
    private let store = CNContactStore()

    public init() {}

    public func authorizationStatus() -> CNAuthorizationStatus {
        CNContactStore.authorizationStatus(for: .contacts)
    }

    public func requestAccess() async throws -> Bool {
        try await store.requestAccess(for: .contacts)
    }

    public func fetchPeople() throws -> [RawContactPerson] {
        let keys: [CNKeyDescriptor] = [
            CNContactIdentifierKey as CNKeyDescriptor,
            CNContactGivenNameKey as CNKeyDescriptor,
            CNContactFamilyNameKey as CNKeyDescriptor,
            CNContactNicknameKey as CNKeyDescriptor,
            CNContactOrganizationNameKey as CNKeyDescriptor,
            CNContactEmailAddressesKey as CNKeyDescriptor,
            CNContactPhoneNumbersKey as CNKeyDescriptor,
        ]
        let request = CNContactFetchRequest(keysToFetch: keys)
        var people: [RawContactPerson] = []
        try store.enumerateContacts(with: request) { contact, _ in
            people.append(Self.map(contact))
        }
        return people
    }

    public static func map(_ contact: CNContact) -> RawContactPerson {
        let given = contact.givenName.trimmingCharacters(in: .whitespacesAndNewlines)
        let family = contact.familyName.trimmingCharacters(in: .whitespacesAndNewlines)
        let nickname = contact.nickname.trimmingCharacters(in: .whitespacesAndNewlines)
        let org = contact.organizationName.trimmingCharacters(in: .whitespacesAndNewlines)

        let fullName = [given, family].filter { !$0.isEmpty }.joined(separator: " ")
        let displayName: String? = {
            if !fullName.isEmpty { return fullName }
            if !nickname.isEmpty { return nickname }
            if !org.isEmpty { return org }
            return nil
        }()

        var aliases: [String] = []
        if !nickname.isEmpty, nickname.caseInsensitiveCompare(displayName ?? "") != .orderedSame {
            aliases.append(nickname)
        }
        if !given.isEmpty, given.caseInsensitiveCompare(displayName ?? "") != .orderedSame {
            aliases.append(given)
        }

        let emails = contact.emailAddresses.map { $0.value as String }
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        let phones = contact.phoneNumbers.map(\.value.stringValue)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        var organisations: [String] = []
        if !org.isEmpty {
            organisations.append(org)
        }

        return RawContactPerson(
            providerContactId: contact.identifier,
            displayName: displayName,
            aliases: aliases,
            emailAddresses: emails,
            phoneNumbers: phones,
            organisations: organisations
        )
    }
}
