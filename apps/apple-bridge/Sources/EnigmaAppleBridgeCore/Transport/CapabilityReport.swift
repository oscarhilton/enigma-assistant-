import Foundation

/// Capability discovery payload returned to Enigma Core.
public struct CapabilityReport: Codable, Equatable, Sendable {
    public struct SourceCapability: Codable, Equatable, Sendable {
        public var available: Bool
        public var authorised: Bool
        public var quality: String?

        public init(available: Bool, authorised: Bool, quality: String? = nil) {
            self.available = available
            self.authorised = authorised
            self.quality = quality
        }
    }

    public var calendar: SourceCapability
    public var reminders: SourceCapability
    public var contacts: SourceCapability
    public var notes: SourceCapability

    public static func scaffold() -> CapabilityReport {
        CapabilityReport(
            calendar: .init(available: true, authorised: false),
            reminders: .init(available: true, authorised: false),
            contacts: .init(available: true, authorised: false),
            notes: .init(available: true, authorised: false, quality: "best_effort")
        )
    }
}
