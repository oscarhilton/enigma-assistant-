import Foundation

public struct NotePassageCandidate: Equatable, Sendable {
    public var text: String
    public var startOffset: Int?
    public var endOffset: Int?

    public init(text: String, startOffset: Int? = nil, endOffset: Int? = nil) {
        self.text = text
        self.startOffset = startOffset
        self.endOffset = endOffset
    }
}

/// Stub local relevance path (M14 owns the real corpus indexer).
///
/// Select → extract passage → transform → leakage analysis.
/// Never auto-transmits wholesale note bodies remotely.
public enum NotesLocalRelevance {
    /// Detect locally relevant passages. Stub always returns an empty list.
    public static func candidatePassages(for note: PrivateNoteDTO) -> [NotePassageCandidate] {
        _ = note
        return []
    }

    /// Stub detector: returns no passages until the M14 corpus indexer lands.
    public static func detectRelevantPassages(
        bodyText _: String,
        query _: String? = nil
    ) -> [String] {
        []
    }

    /// Wholesale bodies are never remote-safe by default (ADR-004 / HIGH).
    public static func mayAutoTransmitRemotely(_ note: PrivateNoteDTO) -> Bool {
        _ = note
        return false
    }

    /// Never true by default: wholesale bodies (and stub empty passages) stay local.
    public static func mayTransmitRemotely(
        fullBody: String,
        candidatePassage: String?
    ) -> Bool {
        guard let candidatePassage else { return false }
        guard isStrictPassage(bodyText: fullBody, candidate: candidatePassage) else { return false }
        // Auto-ship disabled until an audited passage policy (M04) is enabled.
        return false
    }

    /// True only when `candidate` is a strict substring passage, never the full body.
    public static func isStrictPassage(bodyText: String, candidate: String) -> Bool {
        let wholesale = bodyText.trimmingCharacters(in: .whitespacesAndNewlines)
        let passage = candidate.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !wholesale.isEmpty, !passage.isEmpty else { return false }
        guard passage != wholesale else { return false }
        guard wholesale.contains(passage) else { return false }
        return passage.count < wholesale.count
    }
}
