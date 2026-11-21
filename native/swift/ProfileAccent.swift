import SwiftUI
import UIKit

enum ProfileAccent {
    static let key = "dev.streamside.profile.accent"
    static let defaultRGB = -1

    static func color(_ rgb: Int) -> Color {
        guard (0...0xFFFFFF).contains(rgb) else { return .purple }
        return Color(red: Double((rgb >> 16) & 255) / 255,
                     green: Double((rgb >> 8) & 255) / 255,
                     blue: Double(rgb & 255) / 255)
    }

    static func encode(_ color: Color) -> Int {
        var red: CGFloat = 0, green: CGFloat = 0, blue: CGFloat = 0, alpha: CGFloat = 0
        guard UIColor(color).getRed(&red, green: &green, blue: &blue, alpha: &alpha) else { return defaultRGB }
        func byte(_ component: CGFloat) -> Int { Int((min(1, max(0, component)) * 255).rounded()) }
        return (byte(red) << 16) | (byte(green) << 8) | byte(blue)
    }
}
