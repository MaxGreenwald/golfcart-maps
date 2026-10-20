#!/bin/bash
# Runs on the macOS CI runner. Boots an iPhone simulator, installs the app, opens the CarPlay
# external display (I/O > External Displays > CarPlay), opens our app on it and screenshots.
set -x
mkdir -p shots-ci
APP=$(ls -d build/Build/Products/Debug-iphonesimulator/App.app | head -1)
otool -L "$APP/App.debug.dylib" "$APP/App" > shots-ci/linked-libs.txt 2>&1
grep -q libswiftWebKit shots-ci/linked-libs.txt && echo "WARNING: links libswiftWebKit" >> shots-ci/linked-libs.txt
brew install cliclick >/dev/null 2>&1 || true
DEV=$(xcrun simctl list devices available -j | python3 -c "import json,sys;d=json.load(sys.stdin)['devices'];print([x['udid'] for k,v in d.items() if 'iOS' in k for x in v if x['name'].startswith('iPhone 16')][0])")
xcrun simctl boot "$DEV"; open -a Simulator; xcrun simctl bootstatus "$DEV" -b
xcrun simctl location "$DEV" set ${DEMO_FROM:-32.8328,-117.2713} || true
xcrun simctl install "$DEV" "$APP"
xcrun simctl privacy "$DEV" grant location-always com.matchimus.golfcartmaps || xcrun simctl privacy "$DEV" grant location com.matchimus.golfcartmaps || true
(xcrun simctl launch --console-pty "$DEV" com.matchimus.golfcartmaps -GCMCarPlayDemo YES -GCMCarPlayDemoTo "${DEMO_TO:-32.7950,-117.2560,Crystal Pier}" -GCMCarPlayDemoDrive ${DEMO_DRIVE:-0} > shots-ci/app-console.txt 2>&1 &)
sleep 25
xcrun simctl io "$DEV" screenshot shots-ci/phone.png
osascript -e 'tell application "Simulator" to activate' -e 'delay 1' -e 'tell application "System Events" to tell process "Simulator" to click menu item "CarPlay" of menu 1 of menu item "External Displays" of menu 1 of menu bar item "I/O" of menu bar 1' 2> shots-ci/osascript.txt
sleep 12
WIN='tell application "System Events" to tell process "Simulator" to set w to (first window whose name contains "CarPlay")'
osascript -e "$WIN" -e 'tell application "System Events" to tell process "Simulator" to set position of w to {0, 40}' >> shots-ci/osascript.txt 2>&1
osascript -e "$WIN" -e 'tell application "System Events" to tell process "Simulator" to get {position, size} of w' > shots-ci/carplay-window.txt 2>&1
sleep 2
screencapture -x shots-ci/carplay-home.png
# Open our app on the CarPlay home screen (screen coords, CARPLAY_TAPS="x,y x,y").
osascript -e "$WIN" -e 'tell application "System Events" to tell process "Simulator" to perform action "AXRaise" of w' >> shots-ci/osascript.txt 2>&1
for xy in ${CARPLAY_TAPS:-}; do cliclick m:$xy w:300 dd:. w:120 du:. ; sleep 4; screencapture -x shots-ci/carplay-tap-$xy.png; done
sleep 20
screencapture -x shots-ci/carplay-preview.png
sleep 35
screencapture -x shots-ci/carplay-guidance.png
# demo drive: one shot every 4 s while the car steps through the maneuvers
if [ "${DEMO_DRIVE:-0}" != "0" ]; then for i in $(seq -w 1 22); do sleep 4; screencapture -x shots-ci/carplay-drive-$i.png; done; fi
xcrun simctl spawn "$DEV" log show --last 6m --predicate 'process == "App"' --style compact > shots-ci/app-log.txt 2>&1
cp ~/Library/Logs/DiagnosticReports/App*.ips shots-ci/ 2>/dev/null
ls -la shots-ci
