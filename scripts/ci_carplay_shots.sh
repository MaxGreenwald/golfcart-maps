#!/bin/bash
# Runs on the macOS CI runner. Boots an iPhone simulator, installs the app, opens the CarPlay
# external display through the Simulator menu (I/O > External Displays > CarPlay) and screenshots.
set -x
mkdir -p shots-ci
APP=$(ls -d build/Build/Products/Debug-iphonesimulator/App.app | head -1)
codesign -d --entitlements - --xml "$APP" > shots-ci/entitlements.txt 2>&1; (otool -X -s __TEXT __entitlements "$APP/App" | xxd -r -p) >> shots-ci/entitlements.txt 2>&1; (cd build && find . -name "*.xcent" -exec sh -c "echo {}; cat {}" \; ) >> shots-ci/entitlements.txt 2>&1
DEV=$(xcrun simctl list devices available -j | python3 -c "import json,sys;d=json.load(sys.stdin)['devices'];print([x['udid'] for k,v in d.items() if 'iOS' in k for x in v if x['name'].startswith('iPhone 16')][0])")
xcrun simctl boot "$DEV"; open -a Simulator; xcrun simctl bootstatus "$DEV" -b
xcrun simctl privacy "$DEV" grant location com.matchimus.golfcartmaps || true
xcrun simctl location "$DEV" set 32.8328,-117.2713 || true
xcrun simctl install "$DEV" "$APP"
(xcrun simctl launch --console-pty "$DEV" com.matchimus.golfcartmaps > shots-ci/app-console.txt 2>&1 &)
sleep 25
xcrun simctl io "$DEV" screenshot shots-ci/phone.png
osascript -e 'tell application "Simulator" to activate' -e 'delay 1' -e 'tell application "System Events" to tell process "Simulator" to click menu item "CarPlay" of menu 1 of menu item "External Displays" of menu 1 of menu bar item "I/O" of menu bar 1' 2> shots-ci/osascript.txt
sleep 15
screencapture -x shots-ci/desktop-carplay-1.png
# tap our app icon on the CarPlay home screen if visible is not scriptable; capture window list for debugging
osascript -e 'tell application "System Events" to get name of every window of process "Simulator"' >> shots-ci/osascript.txt 2>&1
sleep 10
screencapture -x shots-ci/desktop-carplay-2.png
xcrun simctl spawn "$DEV" log show --last 2m --predicate 'process == "App"' > shots-ci/app-log.txt 2>&1
cp ~/Library/Logs/DiagnosticReports/App*.ips shots-ci/ 2>/dev/null; cp ~/Library/Logs/DiagnosticReports/*/App*.ips shots-ci/ 2>/dev/null; ls ~/Library/Logs/DiagnosticReports > shots-ci/diag-list.txt 2>&1
ls -la shots-ci
