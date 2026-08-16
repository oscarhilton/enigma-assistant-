import EventKit
import Foundation

public enum CalendarAuthorizationStatus: String, Sendable, Equatable {
    case notDetermined
    case denied
    case restricted
    case authorised
    case writeOnly
}

/// Read-only EventKit calendar access (macOS 14+ fullAccess for reads).
public struct EventKitCalendarAccess: Sendable {
    public init() {}

    public func authorizationStatus() -> CalendarAuthorizationStatus {
        Self.map(EKEventStore.authorizationStatus(for: .event))
    }

    /// Requests read access. EventKit's modern API grants fullAccess for reading;
    /// this bridge never writes calendar events.
    public func requestReadAccess() async -> Bool {
        let store = EKEventStore()
        do {
            let granted = try await store.requestFullAccessToEvents()
            return granted
        } catch {
            return false
        }
    }

    public static func map(_ status: EKAuthorizationStatus) -> CalendarAuthorizationStatus {
        switch status {
        case .notDetermined:
            return .notDetermined
        case .restricted:
            return .restricted
        case .denied:
            return .denied
        case .fullAccess:
            return .authorised
        case .writeOnly:
            return .writeOnly
        case .authorized:
            // Pre-macOS 14 / older EventKit: `.authorized` means readable.
            return .authorised
        @unknown default:
            return .denied
        }
    }
}
