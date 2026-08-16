import EnigmaAppleBridgeCore
import XCTest

final class CapabilityReportTests: XCTestCase {
    func testScaffoldCapabilities() throws {
        let report = CapabilityReport.scaffold()
        XCTAssertTrue(report.calendar.available)
        XCTAssertFalse(report.calendar.authorised)
        XCTAssertEqual(report.notes.quality, "best_effort")

        let json = try LocalTransport().describe(capabilities: report)
        XCTAssertTrue(json.contains("\"calendar\""))
        XCTAssertTrue(json.contains("best_effort"))
    }
}
