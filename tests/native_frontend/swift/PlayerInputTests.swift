import XCTest

final class PlayerInputTests: XCTestCase {
    private var testedApp: XCUIApplication?
    override func tearDown() {
        if (testRun?.failureCount ?? 0) > 0, let app = testedApp {
            print("PLAYER_FAILURE_SNAPSHOT\n" + app.debugDescription)
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
    func testGlassControls() { exercise(plain: false) }
    func testPlainControls() { exercise(plain: true) }
    private func wait(_ element: XCUIElement, label: String) {
        let check = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@", label), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [check], timeout: 5), .completed)
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
        // Observed on the pinned iOS 26 simulator: this is an actionGroupCell,
        // not a button. Match its semantic label, then exercise the real action.
        let copyActivity = app.cells["Copy"].firstMatch
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
        let glassSetting = app.switches["Liquid Glass buttons"]
        XCTAssertTrue(glassSetting.waitForExistence(timeout: 5))
        dismissPopover(glassSetting, in: app)
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
        holdControls.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: 0.5)).tap()
        waitValue(holdControls, value: "1")
        tap(app.buttons["player.close"])
        XCTAssertTrue(app.staticTexts["closed"].waitForExistence(timeout: 5))
    }
}
