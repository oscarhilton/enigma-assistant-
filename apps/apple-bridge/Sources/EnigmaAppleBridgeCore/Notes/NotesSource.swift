import Foundation

/// Notes automation adapter placeholder — implemented in M13.
/// Best-effort, opt-in, read-only. Do not scrape Notes SQLite databases.
public protocol NotesSource {
    func listNotes() async throws -> [NoteReference]
    func readNote(id: String) async throws -> RawAppleNote
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

public struct UnimplementedNotesSource: NotesSource {
    public init() {}

    public func listNotes() async throws -> [NoteReference] {
        []
    }

    public func readNote(id: String) async throws -> RawAppleNote {
        RawAppleNote(id: id, title: "", bodyText: "")
    }
}
