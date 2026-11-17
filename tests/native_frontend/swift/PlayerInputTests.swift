import XCTest
import UIKit

final class PlayerInputTests: XCTestCase {
    private var testedApp: XCUIApplication?
    override func tearDown() {
        if (testRun?.failureCount ?? 0) > 0, let app = testedApp {
            print("PLAYER_FAILURE_SNAPSHOT\n" + app.debugDescription)
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = "Owned fixture failure"; screenshot.lifetime = .keepAlways
            add(screenshot)
        }
        super.tearDown()
    }
    private func dismissPopover(_ element: XCUIElement, in app: XCUIApplication) {
        // Tap actual empty space below the fixture. An obscured underlying
        // label can have a {-1,-1} accessibility hit point while modal.
        app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.9)).tap()
        let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [dismissed], timeout: 5), .completed)
    }
    private func contextApp(_ arguments: [String] = []) -> XCUIApplication {
        let app = XCUIApplication(); testedApp = app
        app.launchArguments = ["--thumbnail"] + arguments; app.launch()
        wait(app.staticTexts["fixture-ready"], label: "Video ready", timeout: 30)
        return app
    }
    private func openContext(_ app: XCUIApplication) {
        let source = app.descendants(matching: .any)["preview-thumbnail"].firstMatch
        XCTAssertTrue(source.waitForExistence(timeout: 5))
        source.press(forDuration: 0.7)
        XCTAssertTrue(app.buttons["Watch stream"].waitForExistence(timeout: 5))
        // press() has released the finger. The native preview must persist.
        Thread.sleep(forTimeInterval: 0.5)
        XCTAssertTrue(app.buttons["Watch stream"].exists)
        XCTAssertFalse(app.buttons["View profile"].isEnabled)
        XCTAssertFalse(app.buttons["quicklook.close"].exists)
        XCTAssertFalse(app.buttons["Close preview"].exists)
    }
    func testThumbnailHoldAndTap() {
        continueAfterFailure = false
        let app = contextApp()
        verifyBadgeSettings(in: app)
        let thumbnail = app.descendants(matching: .any)["preview-thumbnail"].firstMatch
        let source = thumbnail.frame
        openContext(app)
        dismissPopover(app.buttons["Watch stream"], in: app)
        wait(app.staticTexts["thumbnail-previews"], label: "Previews: 1")
        wait(app.staticTexts["hold-motion"], label: "Visible centered expansion before preview")
        wait(app.staticTexts["preview-stops"], label: "Stops: 1")
        wait(app.staticTexts["source-target"], label: "Returned to source")
        wait(app.staticTexts["source-motion"], label: "Animated source")
        XCTAssertEqual(thumbnail.frame.minY, source.minY, accuracy: 1)
        XCTAssertEqual(thumbnail.frame.width, source.width, accuracy: 1)
        XCTAssertEqual(app.staticTexts["thumbnail-watches"].label, "Watches: 0", "A hold must not also watch on release")
        thumbnail.tap()
        wait(app.staticTexts["thumbnail-watches"], label: "Watches: 1")
        let drag = thumbnail.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        drag.press(forDuration: 0.26, thenDragTo: drag.withOffset(CGVector(dx: 0, dy: -90)))
        XCTAssertEqual(app.staticTexts["thumbnail-previews"].label, "Previews: 1", "Scrolling must not preview")
        XCTAssertEqual(app.staticTexts["thumbnail-watches"].label, "Watches: 1", "Scrolling must not watch")
        app.terminate()
        let background = contextApp()
        openContext(background)
        XCUIDevice.shared.press(.home); background.activate()
        wait(background.staticTexts["preview-stops"], label: "Stops: 1")
        XCTAssertFalse(background.buttons["Watch stream"].exists)
        XCTAssertEqual(background.staticTexts["thumbnail-watches"].label, "Watches: 0")
        background.terminate()
        let account = contextApp(["--cancel-preview"])
        openContext(account)
        wait(account.staticTexts["preview-stops"], label: "Stops: 1", timeout: 10)
        XCTAssertFalse(account.buttons["Watch stream"].exists)
        XCTAssertEqual(account.staticTexts["thumbnail-watches"].label, "Watches: 0")
        print("THUMBNAIL_LIFT PASS: slight centered expansion; rendered artwork outside clip; held scroll cancels without playback")
        print("THUMBNAIL_COORDINATES PASS: source lift/return; outside dismissal; hold/tap/scroll; background/account cancellation")
    }
    private func verifyBadgeSettings(in app: XCUIApplication) {
        XCTAssertTrue(app.images["verification.twitch"].waitForExistence(timeout: 5))
        let ordinary = app.descendants(matching: .any)["fixture.unverified"].firstMatch
        XCTAssertTrue(ordinary.waitForExistence(timeout: 5))
        XCTAssertEqual(ordinary.images.count, 0, "Ordinary channels must never receive a verification icon")
        for (option, identifier) in [("VERIFIEDBTW", "verification.verifiedbtw"), ("Off", ""), ("Twitch", "verification.twitch")] {
            app.buttons["General settings"].tap()
            let picker = app.buttons["verification.style"].firstMatch
            XCTAssertTrue(picker.waitForExistence(timeout: 5)); picker.tap()
            let choice = app.buttons[option].firstMatch
            XCTAssertTrue(choice.waitForExistence(timeout: 5)); choice.tap()
            app.buttons["Done"].tap()
            if identifier.isEmpty {
                XCTAssertFalse(app.images["verification.twitch"].exists); XCTAssertFalse(app.images["verification.verifiedbtw"].exists)
            } else { XCTAssertTrue(app.images[identifier].waitForExistence(timeout: 5), "Selected bundled artwork must render") }
        }
        print("VERIFICATION_SETTINGS PASS: official artwork; custom artwork; Off; default; unverified suppression")
    }
    // Classify an actual screen pixel from AVPlayerLayer's decoded movie. A
    // static image or readyForDisplay alone cannot satisfy the changing frames.
    private func videoColor(_ point: CGPoint, in app: XCUIApplication) -> Int? {
        guard let image = app.screenshot().image.cgImage else { return nil }
        let x = (point.x - app.frame.minX) / app.frame.width * CGFloat(image.width)
        let y = (point.y - app.frame.minY) / app.frame.height * CGFloat(image.height)
        guard let pixel = image.cropping(to: CGRect(x: x, y: y, width: 1, height: 1)) else { return nil }
        var bytes = [UInt8](repeating: 0, count: 4)
        let valid = bytes.withUnsafeMutableBytes { buffer -> Bool in
            guard let context = CGContext(data: buffer.baseAddress, width: 1, height: 1, bitsPerComponent: 8,
                bytesPerRow: 4, space: CGColorSpaceCreateDeviceRGB(),
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue) else { return false }
            context.draw(pixel, in: CGRect(x: 0, y: 0, width: 1, height: 1)); return true
        }
        guard valid else { return nil }
        if bytes[0] > 140 && bytes[1] < 70 && bytes[2] < 70 { return 0 }
        if bytes[2] > 140 && bytes[1] < 70 && bytes[0] < 70 { return 1 }
        return nil
    }
    func testPreviewPanelLayoutAndActions() {
        continueAfterFailure = false
        for (long, commit) in [(false, false), (false, true), (true, false)] {
            let app = contextApp(long ? ["--long-panel"] : [])
            openContext(app)
            let card = app.otherElements["quicklook.card"].firstMatch
            let watch = app.buttons["Watch stream"]
            let video = app.descendants(matching: .any)["fixture.preview-video"].firstMatch
            XCTAssertTrue(card.waitForExistence(timeout: 5))
            XCTAssertTrue(video.waitForExistence(timeout: 5))
            let frame = video.frame
            XCTAssertEqual(frame.height, frame.width * 9 / 16, accuracy: 1, "Preview video must remain landscape")
            XCTAssertGreaterThan(watch.frame.minY, card.frame.maxY, "Separate glass action menu must be below the preview")
            XCTAssertLessThan(watch.frame.width, card.frame.width, "Glass action menu should be compact")
            XCTAssertGreaterThanOrEqual(card.frame.minY, app.frame.minY + 10)
            var colors = Set<Int>()
            for _ in 0..<24 {
                if let color = videoColor(CGPoint(x: frame.midX, y: frame.midY), in: app) { colors.insert(color) }
                if colors.count == 2 { break }
                Thread.sleep(forTimeInterval: 0.15)
            }
            XCTAssertEqual(colors.count, 2, "Real decoded video must advance in the interactive preview after releasing the hold")
            XCTAssertNil(videoColor(CGPoint(x: frame.minX + 1, y: frame.minY + 1), in: app), "The real upper-left video corner must be clipped")
            XCTAssertNil(videoColor(CGPoint(x: frame.maxX - 1, y: frame.minY + 1), in: app), "The real upper-right video corner must be clipped")
            if !long {
                XCTAssertLessThan(card.frame.height, frame.height + 230, "Short details must not produce a tall empty panel")
            } else {
                for _ in 0..<8 {
                    if app.staticTexts["preview-last-detail"].isHittable { break }
                    card.scrollViews.firstMatch.swipeUp()
                }
                XCTAssertTrue(app.staticTexts["preview-last-detail"].isHittable, "Full details and all tags must remain reachable")
                XCTAssertTrue(app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", "Tag19")).firstMatch.exists, "The last tag must be present after scrolling")
                XCTAssertEqual(video.frame.minY, frame.minY, accuracy: 1, "Scrolling details must not move the video")
            }
            if commit {
                let point = CGVector(dx: (frame.midX - app.frame.minX) / app.frame.width, dy: (frame.midY - app.frame.minY) / app.frame.height)
                app.coordinate(withNormalizedOffset: point).tap()
            } else { watch.tap() }
            let watched = app.staticTexts["preview-watched"]
            XCTAssertTrue(watched.waitForExistence(timeout: 5), "Watch action must transfer into theatre")
            XCTAssertEqual(watched.label, "Same player: 1", "Watch must reuse the decoded preview player")
            let theatreVideo = app.descendants(matching: .any)["fixture.theatre-video"].firstMatch
            XCTAssertTrue(theatreVideo.waitForExistence(timeout: 5))
            var transferredColors = Set<Int>()
            for _ in 0..<24 {
                let frame = theatreVideo.frame
                if let color = videoColor(CGPoint(x: frame.midX, y: frame.midY), in: app) { transferredColors.insert(color) }
                if transferredColors.count == 2 { break }
                Thread.sleep(forTimeInterval: 0.15)
            }
            XCTAssertEqual(transferredColors.count, 2, "The same video surface must keep decoding in theatre after reparenting")
            app.buttons["Close fixture theatre"].tap()
            wait(app.staticTexts["preview-stops"], label: "Stops: 1")
            wait(app.staticTexts["thumbnail-previews"], label: "Previews: 1")
            wait(app.staticTexts["thumbnail-watches"], label: "Watches: 1")
            app.terminate()
        }
        for direction in [CGVector(dx: -115, dy: 0), CGVector(dx: 115, dy: 0), CGVector(dx: 0, dy: -115), CGVector(dx: 0, dy: 115)] {
            let app = contextApp(); openContext(app)
            let video = app.descendants(matching: .any)["fixture.preview-video"].firstMatch
            let start = video.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            start.press(forDuration: 0.05, thenDragTo: start.withOffset(direction))
            wait(app.staticTexts["preview-stops"], label: "Stops: 1")
            XCTAssertFalse(app.buttons["Watch stream"].exists)
            XCTAssertEqual(app.staticTexts["thumbnail-watches"].label, "Watches: 0", "Swipe must cancel the video-tap action")
            XCTAssertEqual(app.staticTexts["thumbnail-previews"].label, "Previews: 1")
            app.terminate()
        }
        print("PREVIEW_SWIPES PASS: left/right/up/down dismiss once; video button never watches; details scroll retained")
        print("CONTEXT_VIDEO PASS: changing decoded frames; 16:9; real upper-corner clipping; one player into theatre")
        print("PREVIEW_PANEL PASS: source-anchored preview; scrollable full details; no X; Watch action; teardown")
    }
    func testGlassControls() { exercise(plain: false) }
    func testPlainControls() { exercise(plain: true) }
    private func wait(_ element: XCUIElement, label: String, timeout: TimeInterval = 5) {
        let check = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@", label), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [check], timeout: timeout), .completed)
    }
    private func waitValue(_ element: XCUIElement, value: String) {
        let check = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", value), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [check], timeout: 5), .completed)
    }
    private func tap(_ element: XCUIElement) {
        XCTAssertTrue(element.waitForExistence(timeout: 5))
        // Tap within the padded hit target, outside the central glyph pixels.
        element.coordinate(withNormalizedOffset: CGVector(dx: 0.18, dy: 0.18)).tap()
    }
    private func exercise(plain: Bool) {
        continueAfterFailure = false
        let app = XCUIApplication()
        testedApp = app
        if plain { app.launchArguments = ["--plain"] }
        app.launch()
        let mute = app.buttons["player.mute"], pause = app.buttons["player.pause"]
        for _ in 0..<3 {
            tap(mute); wait(mute, label: "Unmute stream")
            tap(mute); wait(mute, label: "Mute stream")
            tap(pause); wait(pause, label: "Play")
            tap(pause); wait(pause, label: "Pause")
            tap(app.buttons["player.share"])
            tap(app.buttons["player.copy"])
            app.buttons["read-clipboard"].tap()
            wait(app.staticTexts["copied-link"], label: "https://www.twitch.tv/fixture_channel")
            app.buttons["resize"].tap()
        }
        app.buttons["clear-clipboard"].tap()
        tap(app.buttons["player.share"])
        tap(app.buttons["player.system-share"])
        // Cold share-sheet startup can expose the Copy child text before UIKit
        // aggregates that label onto its action cell. Scope the actual cell by
        // its visible child, then still tap it and verify the clipboard URL.
        let copyActivity = app.otherElements["ActivityListView"].cells
            .containing(.staticText, identifier: "Copy").firstMatch
        let systemShareAppeared = copyActivity.waitForExistence(timeout: 10)
        if !systemShareAppeared { print("SYSTEM_SHARE_SNAPSHOT\n" + app.debugDescription) }
        XCTAssertTrue(systemShareAppeared, "System activity Copy cell did not appear")
        XCTAssertTrue(copyActivity.isHittable)
        copyActivity.tap()
        let dismissedShare = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: copyActivity)
        XCTAssertEqual(XCTWaiter.wait(for: [dismissedShare], timeout: 5), .completed)
        dismissPopover(app.buttons["player.system-share"], in: app)
        app.buttons["read-clipboard"].tap()
        wait(app.staticTexts["copied-link"], label: "https://www.twitch.tv/fixture_channel")
        tap(app.buttons["player.settings"])
        let glassSetting = app.switches["Liquid Glass"]
        XCTAssertTrue(glassSetting.waitForExistence(timeout: 5))
        dismissPopover(glassSetting, in: app)
        tap(app.buttons["motion-checks"])
        let renderedMotion = app.staticTexts["motion-check-result"]
        let sampled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == 'Passed'"), object: renderedMotion)
        let samplingResult = XCTWaiter.wait(for: [sampled], timeout: 35)
        let frameDetail = renderedMotion.value as? String ?? "No frame detail"
        print("PLAYER_MOTION_CHECKS sampling_scale=3; action/reversal scale=1")
        print("PLAYER_MOTION_CHECKS RESULT: " + renderedMotion.label + ": " + frameDetail)
        XCTAssertEqual(samplingResult, .completed, "Rendered motion checks failed: " + frameDetail)
        print("PLAYER_MOTION_CHECKS PASS: " + frameDetail)
        let pixels = app.staticTexts["opacity-pixel-result"]
        let pixelDetail = pixels.value as? String ?? "No pixel detail"
        print("PLAYER_OPACITY_PIXELS RESULT: " + pixels.label + ": " + pixelDetail)
        XCTAssertEqual(pixels.label, "Passed", "Rendered opacity pixels failed: " + pixelDetail)
        print("PLAYER_OPACITY_PIXELS PASS: " + pixelDetail)
        // The fixture ends with a reversed fly transition. A stale hide
        // completion must not remove its controls or swallow the next action.
        tap(mute); wait(mute, label: "Unmute stream")
        tap(mute); wait(mute, label: "Mute stream")
        let holdControls = app.switches["hold-controls"]
        XCTAssertEqual(holdControls.value as? String, "1")
        // The merged accessibility switch spans its label row. Hit the actual
        // trailing thumb, observed at x=341...404 within its 402-point row.
        holdControls.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: 0.5)).tap()
        waitValue(holdControls, value: "0")
        let hidden = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: mute)
        XCTAssertEqual(XCTWaiter.wait(for: [hidden], timeout: 7), .completed, "Controls did not auto-hide")
        // Empty video area, away from top/bottom bars and the central play button.
        app.coordinate(withNormalizedOffset: CGVector(dx: 0.25, dy: 0.16)).tap()
        XCTAssertTrue(mute.waitForExistence(timeout: 5), "Video tap did not reveal controls")
        // The separate auto-hide check above runs with the real four-second
        // deadline. Hold visible controls during action checks: XCTest's idle
        // waits must not race a fresh deadline between existence and touch-up.
        holdControls.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: 0.5)).tap()
        waitValue(holdControls, value: "1")
        for style in ["horizontal", "fade", "vertical"] {
            app.buttons["next-animation"].tap()
            wait(app.staticTexts["animation-style"], label: style)
            app.coordinate(withNormalizedOffset: CGVector(dx: 0.25, dy: 0.16)).tap()
            let removed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: mute)
            XCTAssertEqual(XCTWaiter.wait(for: [removed], timeout: 5), .completed)
            app.coordinate(withNormalizedOffset: CGVector(dx: 0.25, dy: 0.16)).tap()
            XCTAssertTrue(mute.waitForExistence(timeout: 5))
            tap(mute); wait(mute, label: "Unmute stream")
            tap(mute); wait(mute, label: "Mute stream")
        }
        XCTAssertEqual(holdControls.value as? String, "1")
        tap(app.buttons["player.close"])
        XCTAssertTrue(app.staticTexts["closed"].waitForExistence(timeout: 5))
    }
}
