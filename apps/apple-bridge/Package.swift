// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EnigmaAppleBridge",
    platforms: [
        .macOS(.v14),
    ],
    products: [
        .library(name: "EnigmaAppleBridgeCore", targets: ["EnigmaAppleBridgeCore"]),
        .executable(name: "enigma-apple-bridge", targets: ["EnigmaAppleBridge"]),
    ],
    targets: [
        .target(
            name: "EnigmaAppleBridgeCore",
            path: "Sources/EnigmaAppleBridgeCore"
        ),
        .executableTarget(
            name: "EnigmaAppleBridge",
            dependencies: ["EnigmaAppleBridgeCore"],
            path: "Sources/EnigmaAppleBridge"
        ),
        .testTarget(
            name: "EnigmaAppleBridgeTests",
            dependencies: ["EnigmaAppleBridgeCore"],
            path: "Tests/EnigmaAppleBridgeTests"
        ),
    ]
)
