import Foundation

/// Canonical note payload — mirrors `PrivateNote` (snake_case JSON).
public struct PrivateNoteDTO: Codable, Equatable, Sendable {
    public var id: String
    public var provider: String
    public var provider_note_id: String
    public var folder: String?
    public var title: String
    public var body_text: String
    public var created_at: String?
    public var updated_at: String?
    public var metadata: [String: String]

    public init(
        id: String,
        provider: String = "apple_notes",
        provider_note_id: String,
        folder: String? = nil,
        title: String,
        body_text: String,
        created_at: String? = nil,
        updated_at: String? = nil,
        metadata: [String: String] = [:]
    ) {
        self.id = id
        self.provider = provider
        self.provider_note_id = provider_note_id
        self.folder = folder
        self.title = title
        self.body_text = body_text
        self.created_at = created_at
        self.updated_at = updated_at
        self.metadata = metadata
    }
}

public struct NoteSyncCursor: Codable, Equatable, Sendable {
    public var value: String
    public var source: String?

    public init(value: String, source: String? = "apple_notes") {
        self.value = value
        self.source = source
    }
}

public struct NoteChangeBatch: Codable, Equatable, Sendable {
    public var items: [PrivateNoteDTO]
    public var next_cursor: NoteSyncCursor?
    public var exhausted: Bool
    public var authorised: Bool

    public init(
        items: [PrivateNoteDTO],
        next_cursor: NoteSyncCursor? = nil,
        exhausted: Bool = true,
        authorised: Bool = true
    ) {
        self.items = items
        self.next_cursor = next_cursor
        self.exhausted = exhausted
        self.authorised = authorised
    }
}

/// Raw Apple Events / scripting snapshot before domain mapping.
public struct NoteSnapshot: Equatable, Sendable {
    public var noteIdentifier: String
    public var title: String
    public var bodyText: String
    public var folder: String?
    public var createdAt: Date?
    public var modifiedAt: Date?

    public init(
        noteIdentifier: String,
        title: String,
        bodyText: String,
        folder: String? = nil,
        createdAt: Date? = nil,
        modifiedAt: Date? = nil
    ) {
        self.noteIdentifier = noteIdentifier
        self.title = title
        self.bodyText = bodyText
        self.folder = folder
        self.createdAt = createdAt
        self.modifiedAt = modifiedAt
    }
}

public struct NoteReference: Equatable, Sendable {
    public var id: String
    public var title: String

    public init(id: String, title: String) {
        self.id = id
        self.title = title
    }
}

public struct RawAppleNote: Equatable, Sendable {
    public var id: String
    public var title: String
    public var bodyText: String
    public var folder: String?

    public init(id: String, title: String, bodyText: String, folder: String? = nil) {
        self.id = id
        self.title = title
        self.bodyText = bodyText
        self.folder = folder
    }
}
