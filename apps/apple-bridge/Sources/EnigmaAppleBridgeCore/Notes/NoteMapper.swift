import Foundation

public enum NoteMapper {
    public static let provider = "apple_notes"
    public static let quality = "best_effort"

    public static func canonicalID(providerNoteID: String) -> String {
        "\(provider):\(providerNoteID)"
    }

    public static func map(_ snapshot: NoteSnapshot) -> PrivateNoteDTO {
        var metadata: [String: String] = [
            "quality": quality,
            "access": "apple_events",
            "wholesale_body_remote_safe": "false",
            "remote_privacy_default": "high",
        ]
        if let folder = snapshot.folder, !folder.isEmpty {
            metadata["folder"] = folder
        }

        return PrivateNoteDTO(
            id: canonicalID(providerNoteID: snapshot.noteIdentifier),
            provider: provider,
            provider_note_id: snapshot.noteIdentifier,
            folder: snapshot.folder,
            title: snapshot.title,
            body_text: snapshot.bodyText,
            created_at: iso8601(snapshot.createdAt),
            updated_at: iso8601(snapshot.modifiedAt),
            metadata: metadata
        )
    }

    public static func mapAll(_ snapshots: [NoteSnapshot]) -> [PrivateNoteDTO] {
        snapshots.map(map)
    }

    public static func changeBatch(
        from snapshots: [NoteSnapshot],
        cursor: String?,
        authorised: Bool = true
    ) -> NoteChangeBatch {
        guard authorised else {
            return NoteChangeBatch(items: [], next_cursor: nil, exhausted: true, authorised: false)
        }

        let mapped = mapAll(snapshots).sorted { lhs, rhs in
            cursorKey(updatedAt: lhs.updated_at, providerNoteID: lhs.provider_note_id)
                < cursorKey(updatedAt: rhs.updated_at, providerNoteID: rhs.provider_note_id)
        }

        let filtered: [PrivateNoteDTO]
        if let cursor, !cursor.isEmpty {
            filtered = mapped.filter {
                cursorKey(updatedAt: $0.updated_at, providerNoteID: $0.provider_note_id) > cursor
            }
        } else {
            filtered = mapped
        }

        let next: NoteSyncCursor?
        if let last = filtered.last {
            next = NoteSyncCursor(
                value: cursorKey(updatedAt: last.updated_at, providerNoteID: last.provider_note_id),
                source: provider
            )
        } else if let cursor, !cursor.isEmpty {
            next = NoteSyncCursor(value: cursor, source: provider)
        } else {
            next = nil
        }

        return NoteChangeBatch(
            items: filtered,
            next_cursor: next,
            exhausted: true,
            authorised: true
        )
    }

    public static func cursorKey(updatedAt: String?, providerNoteID: String) -> String {
        "\(updatedAt ?? "")|\(providerNoteID)"
    }

    public static func iso8601(_ date: Date?) -> String? {
        guard let date else { return nil }
        return isoFormatter.string(from: date)
    }

    private static let isoFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
