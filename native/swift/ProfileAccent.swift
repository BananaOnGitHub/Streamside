import SwiftUI
import UIKit

enum ProfileAccent {
    private struct Bucket {
        var count = 0
        var red = 0
        var green = 0
        var blue = 0

        var rgb: UInt32 {
            (UInt32(red / count) << 16) | (UInt32(green / count) << 8) | UInt32(blue / count)
        }
    }

    static func dominantRGB(_ image: UIImage) -> UInt32? {
        let side = 24
        guard let source = image.cgImage,
              let space = CGColorSpace(name: CGColorSpace.sRGB),
              let context = CGContext(data: nil, width: side, height: side, bitsPerComponent: 8,
                bytesPerRow: side * 4, space: space,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue),
              let data = context.data else { return nil }
        context.interpolationQuality = .low
        context.draw(source, in: CGRect(x: 0, y: 0, width: CGFloat(side), height: CGFloat(side)))
        let pixels = data.assumingMemoryBound(to: UInt8.self)
        var buckets = Array(repeating: Bucket(), count: 512)
        for offset in stride(from: 0, to: side * side * 4, by: 4) {
            let alpha = Int(pixels[offset + 3])
            guard alpha >= 128 else { continue }
            let red = min(255, Int(pixels[offset]) * 255 / alpha)
            let green = min(255, Int(pixels[offset + 1]) * 255 / alpha)
            let blue = min(255, Int(pixels[offset + 2]) * 255 / alpha)
            let index = ((red >> 5) << 6) | ((green >> 5) << 3) | (blue >> 5)
            buckets[index].count += 1
            buckets[index].red += red
            buckets[index].green += green
            buckets[index].blue += blue
        }
        guard let dominant = buckets.max(by: { $0.count < $1.count }), dominant.count > 0 else { return nil }
        return dominant.rgb
    }

    static func color(_ rgb: UInt32?) -> Color {
        guard let rgb else { return .primary }
        let red = Double((rgb >> 16) & 255) / 255
        let green = Double((rgb >> 8) & 255) / 255
        let blue = Double(rgb & 255) / 255
        return Color(uiColor: UIColor { traits in
            // Keep the source hue and adjust lightness only as needed for
            // controls and text against the profile's light or dark surface.
            let dark = traits.userInterfaceStyle == .dark
            let foreground = dark ? 1.0 : 0.0
            let background = dark ? 0.0 : 1.0
            func luminance(_ channel: Double) -> Double {
                channel <= 0.04045 ? channel / 12.92 : pow((channel + 0.055) / 1.055, 2.4)
            }
            var weight = 0.0
            while true {
                let r = red + (foreground - red) * weight
                let g = green + (foreground - green) * weight
                let b = blue + (foreground - blue) * weight
                let level = 0.2126 * luminance(r) + 0.7152 * luminance(g) + 0.0722 * luminance(b)
                let contrast = (max(background, level) + 0.05) / (min(background, level) + 0.05)
                if contrast >= 4.5 || weight >= 1 {
                    return UIColor(red: CGFloat(r), green: CGFloat(g), blue: CGFloat(b), alpha: 1)
                }
                weight = min(1, weight + 0.05)
            }
        })
    }
}
