import Foundation

/// Best-effort, opt-in, read-only Notes adapter via Apple Events / AppleScript (M13 / ADR-004).
///
/// Does **not** scrape Notes SQLite. Automation permission is separate from
/// Calendar / Reminders / Contacts. Explicit opt-in is required before any probe.
public final class NotesSource: @unchecked Sendable {
    public static let optInDefaultsKey = "enigma.notes.opt_in"
    public static let optInEnvironmentKey = "ENIGMA_NOTES_OPT_IN"

    private let events: NotesAppleEventsClient
    private let optInProvider: () -> Bool
    private let authorisedProvider: (() -> Bool)?
    private let snapshotProvider: (() -> [NoteSnapshot])?

    public init(
        events: NotesAppleEventsClient = ScriptedNotesAppleEventsClient(),
        optInProvider: (() -> Bool)? = nil,
        authorisedProvider: (() -> Bool)? = nil,
        snapshotProvider: (() -> [NoteSnapshot])? = nil
    ) {
        self.events = events
        self.optInProvider = optInProvider ?? { NotesSource.isOptedIn() }
        self.authorisedProvider = authorisedProvider
        self.snapshotProvider = snapshotProvider
    }

    /// Explicit product opt-in (env `ENIGMA_NOTES_OPT_IN` or UserDefaults).
    public static func isOptedIn(
        defaults: UserDefaults = .standard,
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) -> Bool {
        if let raw = environment[optInEnvironmentKey]?.trimmingCharacters(in: .whitespacesAndNewlines),
           !raw.isEmpty
        {
            return ["1", "true", "yes", "on"].contains(raw.lowercased())
        }
        return defaults.bool(forKey: optInDefaultsKey)
    }

    public func isOptedIn() -> Bool { optInProvider() }

    public func isReady() -> Bool { isAuthorised() }

    /// Authorised only when opted in **and** Notes automation appears available.
    public func isAuthorised() -> Bool {
        if let authorisedProvider {
            return authorisedProvider()
        }
        guard isOptedIn() else { return false }
        return events.probeAutomationAccess()
    }

    /// Request Notes automation access. Returns false when not opted in.
    /// Does not touch Calendar / Reminders / Contacts permission prompts.
    @discardableResult
    public func requestAuthorisation() async -> Bool {
        guard isOptedIn() else { return false }
        return events.probeAutomationAccess()
    }

    public func listNotes() throws -> [NoteReference] {
        try loadSnapshots().map { NoteReference(id: $0.noteIdentifier, title: $0.title) }
    }

    public func readNote(id: String) throws -> RawAppleNote {
        guard let snapshot = try loadSnapshots().first(where: { $0.noteIdentifier == id }) else {
            return RawAppleNote(id: id, title: "", bodyText: "")
        }
        return RawAppleNote(
            id: snapshot.noteIdentifier,
            title: snapshot.title,
            bodyText: snapshot.bodyText,
            folder: snapshot.folder
        )
    }

    public func changes(cursor: String?) -> NoteChangeBatch {
        guard isAuthorised() else {
            return NoteChangeBatch(items: [], next_cursor: nil, exhausted: true, authorised: false)
        }

        let snapshots: [NoteSnapshot]
        if let snapshotProvider {
            snapshots = snapshotProvider()
        } else {
            do {
                snapshots = try events.fetchSnapshots()
            } catch {
                // Best-effort: permission / scripting failures must not abort the bridge.
                return NoteChangeBatch(items: [], next_cursor: nil, exhausted: true, authorised: false)
            }
        }

        return NoteMapper.changeBatch(from: snapshots, cursor: cursor, authorised: true)
    }

    private func loadSnapshots() throws -> [NoteSnapshot] {
        guard isOptedIn() else { throw NotesAppleEventsError.notOptedIn }
        if let snapshotProvider { return snapshotProvider() }
        return try events.fetchSnapshots()
    }
}
