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
        assertDismissed(element)
    }
    private func assertDismissed(_ element: XCUIElement, file: StaticString = #filePath, line: UInt = #line) {
        let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [dismissed], timeout: 5), .completed,
            "The dismissed control must leave the accessibility hierarchy", file: file, line: line)
    }
    func testChannelProfile() {
        continueAfterFailure = false
        let app = XCUIApplication(); testedApp = app;app.launchArguments = ["--profile"];app.launch()
        let openProfile = app.buttons["Open fixture profile"]
        XCTAssertTrue(openProfile.waitForExistence(timeout: 5))
        openProfile.tap()
        let following = app.buttons["Following"]
        XCTAssertTrue(following.waitForExistence(timeout: 8))
        let subscribe = app.buttons["Subscription"]
        XCTAssertTrue(subscribe.isEnabled)
        XCTAssertEqual(subscribe.value as? String, "Subscribed")
        let followers = app.staticTexts["profile.followers"]
        XCTAssertTrue(followers.exists)
        XCTAssertLessThan(followers.frame.maxX, following.frame.minX)
        XCTAssertEqual(followers.frame.midY, following.frame.midY, accuracy: 4)
        let notifications = app.buttons["Channel notifications"]
        XCTAssertLessThan(notifications.frame.maxX, subscribe.frame.minX)
        XCTAssertEqual(following.frame.midY, subscribe.frame.midY, accuracy: 1)
        XCTAssertEqual(notifications.frame.midY, subscribe.frame.midY, accuracy: 1)
        subscribe.tap()
        let manage = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Manage on Twitch")).firstMatch
        XCTAssertTrue(manage.waitForExistence(timeout: 3))
        dismissPopover(manage, in: app)
        let preview = app.descendants(matching: .any)["profile.fixture-preview"].firstMatch
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        for frame in [following.frame, subscribe.frame, app.segmentedControls["profile.tabs"].frame, preview.frame] {
            XCTAssertGreaterThan(frame.width, 0)
            XCTAssertGreaterThanOrEqual(frame.minX, app.frame.minX)
            XCTAssertLessThanOrEqual(frame.maxX, app.frame.maxX)
        }
        XCTAssertEqual(preview.frame.width / preview.frame.height, 16.0 / 9.0, accuracy: 0.02)
        let streamDetails = app.staticTexts["profile.stream-details"]
        XCTAssertTrue(streamDetails.exists)
        XCTAssertTrue(streamDetails.label.contains("A long live category name"))
        XCTAssertGreaterThan(streamDetails.frame.minY, preview.frame.maxY)
        following.tap()
        let confirm = app.buttons["profile.unfollow-confirm"]
        XCTAssertTrue(confirm.waitForExistence(timeout: 3))
        dismissPopover(confirm, in: app)
        XCTAssertTrue(following.exists)
        app.buttons["Channel notifications"].tap()
        for title in ["Personalized", "Always", "Go Live Only", "Off"] { XCTAssertTrue(app.buttons[title].waitForExistence(timeout: 3)) }
        app.buttons["Always"].tap()
        following.tap();XCTAssertTrue(confirm.waitForExistence(timeout: 3));confirm.tap()
        XCTAssertTrue(app.buttons["Follow"].waitForExistence(timeout: 5))
        let tabs = app.segmentedControls["profile.tabs"]
        let right = app.coordinate(withNormalizedOffset: CGVector(dx: 0.82, dy: 0.56))
        let left = app.coordinate(withNormalizedOffset: CGVector(dx: 0.18, dy: 0.56))
        let partial = app.coordinate(withNormalizedOffset: CGVector(dx: 0.76, dy: 0.56))
        right.press(forDuration: 0.05, thenDragTo: partial)
        XCTAssertTrue(tabs.buttons["Home"].isSelected, "A short drag must settle back on Home")
        XCTAssertTrue(preview.isHittable, "Cancelled swipe must restore Home interaction")
        right.press(forDuration: 0.05, thenDragTo: left)
        XCTAssertTrue(tabs.buttons["About"].isSelected, "Swipe left must select About")
        left.press(forDuration: 0.05, thenDragTo: right)
        XCTAssertTrue(tabs.buttons["Home"].isSelected, "Swipe right must select Home")
        tabs.buttons["About"].tap()
        app.swipeUp()
        XCTAssertTrue(app.staticTexts["Fixture panel"].waitForExistence(timeout: 3))
        let credits = app.descendants(matching: .any)["profile.markdown-link-text"].firstMatch
        XCTAssertTrue(credits.exists)
        let heading = app.staticTexts["profile.panel-heading"]
        XCTAssertTrue(heading.exists)
        XCTAssertEqual(heading.label, "Panel notes")
        let artwork = app.descendants(matching: .any)["profile.panel-image-link"].firstMatch
        XCTAssertTrue(artwork.waitForExistence(timeout: 5))
        let artworkFrame = artwork.frame
        XCTAssertGreaterThan(artworkFrame.width, 0)
        XCTAssertEqual(artworkFrame.width / max(1, artworkFrame.height), 2.0 / 3.0, accuracy: 0.03)
        XCTAssertFalse(app.buttons["Open panel link"].exists)
        let destination = app.staticTexts["profile.opened-link"]
        XCTAssertTrue(artwork.isHittable)
        artwork.tap()
        wait(destination, label: "Opened 1: https://example.invalid/artwork")
        artwork.press(forDuration: 1.2)
        let openLink = app.buttons["Open link"]
        XCTAssertTrue(openLink.waitForExistence(timeout: 5))
        XCTAssertEqual(destination.label, "Opened 1: https://example.invalid/artwork", "Holding must not open the browser")
        openLink.tap()
        wait(destination, label: "Opened 2: https://example.invalid/artwork")
        for _ in 0..<3 {
            if credits.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(credits.isHittable)
        let creditLink = credits.coordinate(withNormalizedOffset: CGVector(dx: 0.1, dy: 0.5))
        creditLink.tap()
        wait(destination, label: "Opened 3: https://example.invalid/credits")
        creditLink.press(forDuration: 1.2)
        XCTAssertTrue(openLink.waitForExistence(timeout: 5))
        XCTAssertEqual(destination.label, "Opened 3: https://example.invalid/credits")
        openLink.tap()
        wait(destination, label: "Opened 4: https://example.invalid/credits")
        app.buttons["Close profile"].tap()
        XCTAssertTrue(openProfile.waitForExistence(timeout: 5))
        openProfile.tap()
        XCTAssertTrue(app.buttons["Close profile"].waitForExistence(timeout: 5))
        let edge = app.coordinate(withNormalizedOffset: CGVector(dx: 0.008, dy: 0.42))
        edge.press(forDuration: 0.05, thenDragTo: app.coordinate(withNormalizedOffset: CGVector(dx: 0.80, dy: 0.42)))
        XCTAssertTrue(openProfile.waitForExistence(timeout: 5), "An edge swipe must pop the profile")
        app.terminate()
        app.launchArguments = ["--profile", "--profile-relationship-failure"]
        app.launch()
        XCTAssertTrue(openProfile.waitForExistence(timeout: 5))
        openProfile.tap()
        XCTAssertTrue(app.staticTexts["Follow and notification settings could not be loaded."].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Fixture biography"].exists)
        XCTAssertFalse(app.buttons["Follow"].isEnabled)
        XCTAssertFalse(app.buttons["Channel notifications"].isEnabled)
        app.segmentedControls["profile.tabs"].buttons["About"].tap()
        app.swipeUp()
        XCTAssertTrue(app.staticTexts["Fixture panel"].waitForExistence(timeout: 3))
        print("CHANNEL_PROFILE_UI PASS: production Home/About, web subscription popover, compact header, stream details, decoded tall panel artwork, image link tap and context menu, Markdown block styling, link tap and context menu, tab swipes, notification menu, confirmed unfollow and navigation pop")
    }
    func testMarkedContentConsent() {
        continueAfterFailure = false
        let editor = XCUIApplication(); testedApp = editor
        editor.launchArguments = ["--local-test-editor"]; editor.launch()
        XCTAssertTrue(editor.buttons["Local test stream"].waitForExistence(timeout: 5))
        editor.buttons["Local test stream"].tap()
        let enabled = editor.switches["Show local test stream"]
        XCTAssertTrue(enabled.waitForExistence(timeout: 5))
        enabled.coordinate(withNormalizedOffset: CGVector(dx: 0.94, dy: 0.5)).tap()
        editor.buttons["Save"].tap()
        XCTAssertTrue(editor.staticTexts["local-fixture-name"].waitForExistence(timeout: 5))
        XCTAssertEqual(editor.staticTexts["local-fixture-name"].label, "Local test · Test channel")
        editor.buttons["Local test stream"].tap()
        let remove = editor.buttons["Remove local test stream"]
        for _ in 0..<5 {
            if remove.isHittable { break }
            editor.swipeUp()
        }
        XCTAssertTrue(remove.isHittable); remove.tap()
        XCTAssertTrue(editor.staticTexts["No local test stream"].waitForExistence(timeout: 5))
        editor.terminate()
        print("LOCAL_TEST_EDITOR PASS: development create, followed-entry projection and removal")
        // Preview acceptance is checked both before and after Watch handoff.
        // The first path must restore the real video tap target on admission.
        let cases = [(false, false, false, false), (false, true, false, false),
                     (true, false, false, false), (true, true, false, false), (true, true, true, false),
                     (false, true, false, true), (true, true, false, true)]
        for (preview, accept, pendingWatch, thumbnailsEnabled) in cases {
            let app = XCUIApplication(); testedApp = app
            app.launchArguments = ["--marked-content"] + (preview ? ["--marked-preview"] : [])
                + (thumbnailsEnabled ? ["--marked-thumbnails-enabled"] : [])
            app.launch()
            if preview {
                let source = app.descendants(matching: .any)["Marked stream thumbnail"].firstMatch
                XCTAssertTrue(source.waitForExistence(timeout: 5)); source.press(forDuration: 1.2)
                XCTAssertTrue(app.buttons["Watch stream"].waitForExistence(timeout: 5))
            }
            let warning = app.staticTexts["This stream has been marked as containing:"]
            XCTAssertTrue(warning.waitForExistence(timeout: 5))
            XCTAssertTrue(app.staticTexts["Fixture content label, Second fixture label"].exists)
            let slot = app.descendants(matching: .any)["marked.video-slot"].firstMatch
            XCTAssertTrue(slot.waitForExistence(timeout: 5))
            XCTAssertEqual(slot.frame.width, preview ? 360 : app.frame.width, accuracy: 1,
                "Warning must fill the actual video canvas, not shrink to its ideal size")
            XCTAssertEqual(slot.frame.width / slot.frame.height, 16.0 / 9.0, accuracy: 0.03)
            XCTAssertTrue(slot.frame.insetBy(dx: -2, dy: -2).contains(warning.frame))
            XCTAssertEqual(app.staticTexts["marked.media-starts"].label, "starts=0")
            let remember = app.descendants(matching: .any)["marked.dontShowAgain"].firstMatch
            XCTAssertTrue(remember.waitForExistence(timeout: 5)); XCTAssertTrue(remember.isHittable)
            XCTAssertTrue(slot.frame.insetBy(dx: -2, dy: -2).contains(remember.frame))
            let proceed = app.buttons["Continue"]
            XCTAssertTrue(slot.frame.insetBy(dx: -2, dy: -2).contains(proceed.frame))
            XCTAssertGreaterThanOrEqual(proceed.frame.height, 28)
            let question = app.staticTexts["Do you want to continue?"]
            XCTAssertLessThan(remember.frame.minY - question.frame.maxY, 24, "Warning should have a compact message/action gap")
            let group = warning.frame.union(proceed.frame)
            XCTAssertLessThan(abs(group.midY - slot.frame.midY), 30, "The warning group should be centered in the video")
            if preview {
                XCTAssertFalse(app.buttons["quicklook.play-preview"].exists,
                    "Video Watch must not cover consent controls or appear to VoiceOver")
            }
            remember.tap()
            // The button action can complete before XCTest receives the updated accessibility snapshot.
            waitValue(remember, value: "Selected")
            XCTAssertFalse(app.staticTexts["Admitted"].exists)
            if accept {
                // Pending Watch must move the same gate into the theatre,
                // not bypass consent or create a second media request.
                if pendingWatch {
                    app.buttons["Watch stream"].tap()
                    XCTAssertTrue(app.staticTexts["Theatre"].waitForExistence(timeout: 5))
                    XCTAssertTrue(warning.exists)
                    XCTAssertEqual(app.staticTexts["marked.media-starts"].label, "starts=0")
                }
                app.buttons["Continue"].tap()
                if thumbnailsEnabled {
                    XCTAssertFalse(app.staticTexts["Show thumbnails for marked streams?"].exists)
                } else {
                    XCTAssertTrue(app.staticTexts["Show thumbnails for marked streams?"].waitForExistence(timeout: 5))
                    XCTAssertFalse(app.staticTexts["Admitted"].exists)
                    XCTAssertEqual(app.staticTexts["marked.media-starts"].label, "starts=0")
                    app.buttons["Show thumbnails"].tap()
                }
                XCTAssertTrue(app.staticTexts["Admitted"].waitForExistence(timeout: 5))
                XCTAssertEqual(app.staticTexts["marked.media-starts"].label, "starts=1")
                XCTAssertEqual(app.staticTexts["marked.preferences"].label, "warnings=false thumbnails=true")
                if preview && !pendingWatch {
                    let videoWatch = app.buttons["quicklook.play-preview"]
                    XCTAssertTrue(videoWatch.waitForExistence(timeout: 5)); XCTAssertTrue(videoWatch.isHittable)
                    videoWatch.tap()
                    XCTAssertTrue(app.staticTexts["Theatre"].waitForExistence(timeout: 5))
                    XCTAssertEqual(app.staticTexts["marked.media-starts"].label, "starts=1")
                }
            } else {
                app.buttons["Close"].tap()
                XCTAssertTrue(app.staticTexts["Closed"].waitForExistence(timeout: 5))
                XCTAssertFalse(app.buttons["Watch stream"].exists, "Close must dismiss the preview itself")
                XCTAssertEqual(app.staticTexts["marked.media-starts"].label, "starts=0")
                XCTAssertEqual(app.staticTexts["marked.preferences"].label, "warnings=true thumbnails=false")
            }
            app.terminate()
        }
        print("MARKED_CONTENT_UI PASS: inline 16:9 warning; interactive preview controls; Close dismisses owner; choices before one media start")
        print("MARKED_PENDING_WATCH PASS: same pending consent into theatre; zero starts until thumbnail choice")
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
        // Leave scheduling headroom above the production 0.45s threshold on
        // loaded simulators. One hold, no retry or accessibility activation.
        source.press(forDuration: 1.2)
        XCTAssertTrue(app.buttons["Watch stream"].waitForExistence(timeout: 5))
        // press() has released the finger. The native preview must persist.
        Thread.sleep(forTimeInterval: 0.5)
        XCTAssertTrue(app.buttons["Watch stream"].exists)
        let profile = app.buttons["quicklook.profile"]
        XCTAssertTrue(profile.exists, "An unavailable profile action must remain visible")
        XCTAssertFalse(profile.isEnabled, "The profile action must be exposed as disabled when it has no handler")
        XCTAssertFalse(app.buttons["quicklook.close"].exists)
        XCTAssertFalse(app.buttons["Close preview"].exists)
    }
    func testThumbnailHoldAndTap() {
        continueAfterFailure = false
        let app = contextApp(["--check-hold-motion"])
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
        assertDismissed(background.buttons["quicklook.watch"])
        XCTAssertEqual(background.staticTexts["thumbnail-watches"].label, "Watches: 0")
        background.terminate()
        let account = contextApp(["--cancel-preview"])
        openContext(account)
        wait(account.staticTexts["preview-stops"], label: "Stops: 1", timeout: 10)
        // Stopping the player releases media ownership before the passive
        // return animation finishes. Check both outcomes independently.
        assertDismissed(account.buttons["quicklook.watch"])
        XCTAssertTrue(account.buttons["preview-thumbnail"].isHittable)
        XCTAssertEqual(account.staticTexts["preview-stops"].label, "Stops: 1")
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
            XCTAssertFalse(app.descendants(matching: .any)["profile.accent-picker"].firstMatch.exists)
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
        // One coherent bounds snapshot, not four separate accessibility-tree
        // queries per pixel. Repeated remote queries can dominate frame sampling.
        let bounds = app.frame
        guard bounds.width > 0, bounds.height > 0,
              let image = app.screenshot().image.cgImage else { return nil }
        let x = (point.x - bounds.minX) / bounds.width * CGFloat(image.width)
        let y = (point.y - bounds.minY) / bounds.height * CGFloat(image.height)
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
    private func assertPreviewStatus(_ status: XCUIElement, spinner: XCUIElement, inside bounds: CGRect,
                                     file: StaticString = #filePath, line: UInt = #line) {
        // Actual clipping boundary, not the accessibility union of text glyphs.
        // Require the real bottom inset as well as full text/spinner containment.
        for element in [status, spinner] {
            XCTAssertTrue(bounds.contains(element.frame), "Status must be fully inside the rounded card", file: file, line: line)
            XCTAssertGreaterThanOrEqual(bounds.maxY - element.frame.maxY, 10,
                "Footer must retain its bottom padding", file: file, line: line)
        }
    }
    func testPreviewPanelLayoutAndActions() {
        continueAfterFailure = false
        for (long, commit) in [(false, false), (false, true), (true, false)] {
            let app = contextApp(long ? ["--long-panel"] : [])
            openContext(app)
            let card = app.otherElements["quicklook.card"].firstMatch
            let boundary = app.otherElements["quicklook.bounds"].firstMatch
            let watch = app.buttons["Watch stream"]
            let video = app.descendants(matching: .any)["fixture.preview-video"].firstMatch
            XCTAssertTrue(card.waitForExistence(timeout: 5))
            XCTAssertTrue(boundary.waitForExistence(timeout: 5))
            XCTAssertTrue(video.waitForExistence(timeout: 5))
            let status = app.staticTexts["Buffering…"]
            let spinner = app.descendants(matching: .any)["quicklook.buffering-spinner"].firstMatch
            XCTAssertTrue(status.waitForExistence(timeout: 5)); XCTAssertTrue(status.isHittable)
            XCTAssertTrue(spinner.waitForExistence(timeout: 5))
            assertPreviewStatus(status, spinner: spinner, inside: boundary.frame)
            let statusFrame = status.frame
            let frame = video.frame
            XCTAssertEqual(boundary.frame.width, frame.width, accuracy: 1)
            XCTAssertEqual(boundary.frame.height, frame.height + (long ? 220 : 150), accuracy: 1,
                "Status containment must use the actual sized, rounded UIKit card")
            XCTAssertEqual(frame.height, frame.width * 9 / 16, accuracy: 1, "Preview video must remain landscape")
            XCTAssertGreaterThan(watch.frame.minY, boundary.frame.maxY, "Separate glass action menu must be below the preview")
            XCTAssertLessThan(watch.frame.width, boundary.frame.width, "Glass action menu should be compact")
            XCTAssertGreaterThanOrEqual(boundary.frame.minY, app.frame.minY + 10)
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
                XCTAssertLessThan(boundary.frame.height, frame.height + 230, "Short details must not produce a tall empty panel")
            } else {
                for _ in 0..<8 {
                    if app.staticTexts["preview-last-detail"].isHittable { break }
                    card.scrollViews.firstMatch.swipeUp()
                }
                XCTAssertTrue(app.staticTexts["preview-last-detail"].isHittable, "Full details and all tags must remain reachable")
                XCTAssertTrue(app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", "Tag19")).firstMatch.exists, "The last tag must be present after scrolling")
                XCTAssertEqual(video.frame.minY, frame.minY, accuracy: 1, "Scrolling details must not move the video")
                XCTAssertTrue(status.isHittable)
                XCTAssertEqual(status.frame.minY, statusFrame.minY, accuracy: 1, "Buffering status stays outside the scrolling details")
                assertPreviewStatus(status, spinner: spinner, inside: boundary.frame)
            }
            if commit {
                let point = CGVector(dx: (frame.midX - app.frame.minX) / app.frame.width, dy: (frame.midY - app.frame.minY) / app.frame.height)
                app.coordinate(withNormalizedOffset: point).tap()
            } else {
                XCTAssertTrue(watch.isHittable)
                // One tap in the trailing padding must reach the actual row,
                // including after the independent details scroll view moves.
                watch.coordinate(withNormalizedOffset: CGVector(dx: 0.84, dy: 0.5)).tap()
            }
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
            let decoder = app.descendants(matching: .any)["fixture.decoder-state"].firstMatch
            let decoderState = decoder.exists ? String(describing: decoder.value) : "Decoder surface is absent from the theatre hierarchy"
            print("CONTEXT_VIDEO_HANDOFF: long=\(long); videoTap=\(commit); colors=\(transferredColors.count); " + decoderState)
            XCTAssertEqual(transferredColors.count, 2,
                "The same video surface must keep decoding in theatre after reparenting: " + decoderState)
            app.buttons["Close fixture theatre"].tap()
            wait(app.staticTexts["preview-stops"], label: "Stops: 1")
            wait(app.staticTexts["thumbnail-previews"], label: "Previews: 1")
            wait(app.staticTexts["thumbnail-watches"], label: "Watches: 1")
            app.terminate()
        }
        for direction in [CGVector(dx: -115, dy: 0), CGVector(dx: 115, dy: 0), CGVector(dx: 0, dy: -115), CGVector(dx: 0, dy: 115)] {
            print("PREVIEW_SWIPE BEGIN: dx=\(direction.dx) dy=\(direction.dy)")
            let app = contextApp(); openContext(app)
            let video = app.descendants(matching: .any)["fixture.preview-video"].firstMatch
            let start = video.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            start.press(forDuration: 0.05, thenDragTo: start.withOffset(direction))
            wait(app.staticTexts["preview-stops"], label: "Stops: 1")
            assertDismissed(app.buttons["quicklook.watch"])
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
    private func readCopiedLink(in app: XCUIApplication) {
        let paste = app.buttons["read-clipboard"]
        let enabled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND enabled == true"), object: paste)
        XCTAssertEqual(XCTWaiter.wait(for: [enabled], timeout: 5), .completed)
        paste.tap()
        wait(app.staticTexts["copied-link"], label: "https://www.twitch.tv/fixture_channel")
    }
    private func clearCopiedLink(in app: XCUIApplication) {
        app.buttons["clear-clipboard"].tap()
        wait(app.staticTexts["copied-link"], label: "Missing URL")
    }
    private func exercise(plain: Bool) {
        continueAfterFailure = false
        let app = XCUIApplication()
        testedApp = app
        if plain { app.launchArguments = ["--plain"] }
        app.launch()
        let mute = app.buttons["player.mute"], pause = app.buttons["player.pause"]
        for _ in 0..<3 {
            clearCopiedLink(in: app)
            tap(mute); wait(mute, label: "Unmute stream")
            tap(mute); wait(mute, label: "Mute stream")
            tap(pause); wait(pause, label: "Play")
            tap(pause); wait(pause, label: "Pause")
            tap(app.buttons["player.share"])
            tap(app.buttons["player.copy"])
            readCopiedLink(in: app)
            app.buttons["resize"].tap()
        }
        clearCopiedLink(in: app)
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
        readCopiedLink(in: app)
        print("PLAYER_CLIPBOARD PASS: three fresh production Copy Link round trips and UIKit Share Copy through system Paste")
        tap(app.buttons["player.settings"])
        let glassSetting = app.switches["Liquid Glass"]
        XCTAssertTrue(glassSetting.waitForExistence(timeout: 5))
        XCTAssertFalse(app.switches["Show marked stream warnings"].exists)
        let resolution = app.buttons["player.resolution"]
        guard resolution.waitForExistence(timeout: 5), resolution.isHittable else {
            XCTFail("Resolution dropdown must be visible and hittable"); return
        }
        resolution.tap()
        let choice = app.buttons["480p"].firstMatch
        guard choice.waitForExistence(timeout: 5), choice.isHittable else {
            XCTFail("Resolution menu option must be visible and hittable"); return
        }
        choice.tap()
        wait(app.staticTexts["resolution-choice"], label: "480p")
        print("PLAYER_RESOLUTION PASS: native menu selects SDK quality")
        dismissPopover(glassSetting, in: app)
        tap(app.buttons["motion-checks"])
        let renderedMotion = app.staticTexts["motion-check-result"]
        let sampled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label IN {'Passed', 'Failed'}"), object: renderedMotion)
        let samplingResult = XCTWaiter.wait(for: [sampled], timeout: 65)
        let frameDetail = renderedMotion.value as? String ?? "No frame detail"
        print("PLAYER_MOTION_CHECKS sampling_scale=3; action/reversal scale=1")
        print("PLAYER_MOTION_CHECKS RESULT: " + renderedMotion.label + ": " + frameDetail)
        XCTAssertEqual(samplingResult, .completed, "Rendered motion checks never completed: " + frameDetail)
        XCTAssertEqual(renderedMotion.label, "Passed", "Rendered motion checks failed: " + frameDetail)
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
