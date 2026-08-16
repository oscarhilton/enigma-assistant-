import Foundation

/// Apple Events / AppleScript access for Notes — never SQLite.
///
/// Automation permission is distinct from Calendar / Reminders / Contacts.
public protocol NotesAppleEventsClient: Sendable {
    /// Best-effort probe: returns true when Notes automation appears available.
    func probeAutomationAccess() -> Bool

    /// Fetch note snapshots via Apple Events. Failures are surfaced as throws.
    func fetchSnapshots() throws -> [NoteSnapshot]
}

public enum NotesAppleEventsError: Error, Equatable, Sendable {
    case scriptingFailed(String)
    case invalidPayload(String)
    case notOptedIn
}

/// Runs `osascript` against Notes.app. Read-only, best-effort.
public struct ScriptedNotesAppleEventsClient: NotesAppleEventsClient {
    private let runner: @Sendable (String) throws -> String

    public init(runner: (@Sendable (String) throws -> String)? = nil) {
        self.runner = runner ?? { try Self.runOsascript($0) }
    }

    public func probeAutomationAccess() -> Bool {
        do {
            let output = try runner(Self.probeScript).trimmingCharacters(in: .whitespacesAndNewlines)
            return output == "ok"
        } catch {
            return false
        }
    }

    public func fetchSnapshots() throws -> [NoteSnapshot] {
        let raw = try runner(Self.listScript)
        return try Self.parseSnapshots(from: raw)
    }

    /// Minimal automation probe — does not dump note bodies.
    public static let probeScript = """
    try
      tell application "Notes"
        if (count of notes) >= 0 then
          return "ok"
        end if
      end tell
    on error
      return "denied"
    end try
    """

    /// Emits NDJSON lines: id, title, folder, created, modified, body (tab-separated after a type tag).
    /// Attachments / rich content are intentionally omitted (ADR-004).
    public static let listScript = """
    set recordSep to ASCII character 30
    set fieldSep to ASCII character 31
    set output to ""
    try
      tell application "Notes"
        repeat with theNote in notes
          set noteId to id of theNote as string
          set noteTitle to name of theNote as string
          set noteBody to ""
          try
            set noteBody to plaintext of theNote as string
          end try
          set noteFolder to ""
          try
            set noteFolder to name of container of theNote as string
          end try
          set createdStamp to ""
          try
            set createdStamp to (creation date of theNote) as string
          end try
          set modifiedStamp to ""
          try
            set modifiedStamp to (modification date of theNote) as string
          end try
          set output to output & noteId & fieldSep & noteTitle & fieldSep & noteFolder & fieldSep & createdStamp & fieldSep & modifiedStamp & fieldSep & noteBody & recordSep
        end repeat
      end tell
    on error errMsg
      error errMsg
    end try
    return output
    """

    public static func parseSnapshots(from raw: String) throws -> [NoteSnapshot] {
        let recordSep = Character(UnicodeScalar(30)!)
        let fieldSep = Character(UnicodeScalar(31)!)
        var snapshots: [NoteSnapshot] = []

        for record in raw.split(separator: recordSep, omittingEmptySubsequences: true) {
            let fields = record.split(separator: fieldSep, omittingEmptySubsequences: false)
            guard fields.count >= 6 else {
                throw NotesAppleEventsError.invalidPayload("expected ≥6 fields, got \(fields.count)")
            }
            let id = String(fields[0])
            guard !id.isEmpty else { continue }
            snapshots.append(
                NoteSnapshot(
                    noteIdentifier: id,
                    title: String(fields[1]),
                    bodyText: String(fields[5]),
                    folder: fields[2].isEmpty ? nil : String(fields[2]),
                    createdAt: Self.parseAppleScriptDate(String(fields[3])),
                    modifiedAt: Self.parseAppleScriptDate(String(fields[4]))
                )
            )
        }
        return snapshots
    }

    /// Best-effort parse of AppleScript `(date) as string` stamps. Empty → nil.
    public static func parseAppleScriptDate(_ raw: String) -> Date? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = iso.date(from: trimmed) {
            return date
        }
        iso.formatOptions = [.withInternetDateTime]
        if let date = iso.date(from: trimmed) {
            return date
        }

        let formatter = DateFormatter()
        formatter.locale = .current
        formatter.timeZone = .current
        for dateStyle in [DateFormatter.Style.full, .long, .medium] {
            for timeStyle in [DateFormatter.Style.full, .long, .medium, .short] {
                formatter.dateStyle = dateStyle
                formatter.timeStyle = timeStyle
                if let date = formatter.date(from: trimmed) {
                    return date
                }
            }
        }
        return nil
    }

    private static func runOsascript(_ source: String) throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        process.arguments = ["-e", source]

        let stdout = Pipe()
        let stderr = Pipe()
        process.standardOutput = stdout
        process.standardError = stderr

        do {
            try process.run()
        } catch {
            throw NotesAppleEventsError.scriptingFailed(String(describing: error))
        }
        process.waitUntilExit()

        let outData = stdout.fileHandleForReading.readDataToEndOfFile()
        let errData = stderr.fileHandleForReading.readDataToEndOfFile()
        if process.terminationStatus != 0 {
            let message = String(data: errData, encoding: .utf8) ?? "osascript failed"
            throw NotesAppleEventsError.scriptingFailed(message)
        }
        return String(data: outData, encoding: .utf8) ?? ""
    }
}

/// Test double for Apple Events results.
public struct MockNotesAppleEventsClient: NotesAppleEventsClient, Sendable {
    public var automationAllowed: Bool
    public var snapshots: [NoteSnapshot]
    public var fetchError: NotesAppleEventsError?

    public init(
        automationAllowed: Bool = true,
        snapshots: [NoteSnapshot] = [],
        fetchError: NotesAppleEventsError? = nil
    ) {
        self.automationAllowed = automationAllowed
        self.snapshots = snapshots
        self.fetchError = fetchError
    }

    public func probeAutomationAccess() -> Bool {
        automationAllowed
    }

    public func fetchSnapshots() throws -> [NoteSnapshot] {
        if let fetchError { throw fetchError }
        return snapshots
    }
}
