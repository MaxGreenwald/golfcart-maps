#!/bin/bash
# Runs on the macOS CI runner. Boots an iPhone simulator, installs the app, opens the CarPlay
# external display (I/O > External Displays > CarPlay), opens our app on it and screenshots.
set -x
mkdir -p shots-ci
APP=$(ls -d build/Build/Products/Debug-iphonesimulator/App.app | head -1)
otool -L "$APP/App.debug.dylib" "$APP/App" > shots-ci/linked-libs.txt 2>&1
grep -q libswiftWebKit shots-ci/linked-libs.txt && echo "WARNING: links libswiftWebKit" >> shots-ci/linked-libs.txt
# CARPLAY_SIZE=WxH@S turns on the Simulator's CarPlay size dialog (Apple: CarPlayExtraOptions).
[ -n "$CARPLAY_SIZE" ] && defaults write com.apple.iphonesimulator CarPlayExtraOptions -bool YES
echo "size=${CARPLAY_SIZE:-default}" > shots-ci/size.txt
brew install cliclick >/dev/null 2>&1 || true
DEV=$(xcrun simctl list devices available -j | python3 -c "import json,sys;d=json.load(sys.stdin)['devices'];print([x['udid'] for k,v in d.items() if 'iOS' in k for x in v if x['name'].startswith('iPhone 16')][0])")
xcrun simctl boot "$DEV"; open -a Simulator; xcrun simctl bootstatus "$DEV" -b
xcrun simctl location "$DEV" set ${DEMO_FROM:-32.8328,-117.2713} || true
xcrun simctl install "$DEV" "$APP"
xcrun simctl privacy "$DEV" grant location-always com.matchimus.golfcartmaps || xcrun simctl privacy "$DEV" grant location com.matchimus.golfcartmaps || true
(xcrun simctl launch --console-pty "$DEV" com.matchimus.golfcartmaps -GCMCarPlayDemo YES -GCMCarPlayDemoTo "${DEMO_TO:-32.7950,-117.2560,Crystal Pier}" -GCMCarPlayDemoDrive ${DEMO_DRIVE:-0} -GCMCarPlayCelebrateLoop ${CELEBRATE_LOOP:-NO} > shots-ci/app-console.txt 2>&1 &)
sleep 25
xcrun simctl io "$DEV" screenshot shots-ci/phone.png
# With CarPlayExtraOptions the item is named "CarPlay..." so match by prefix, and log the names.
osascript -e 'tell application "Simulator" to activate' -e 'delay 1' -e 'tell application "System Events" to tell process "Simulator" to get name of every menu item of menu 1 of menu item "External Displays" of menu 1 of menu bar item "I/O" of menu bar 1' > shots-ci/ext-menu.txt 2>&1
osascript -e 'tell application "System Events" to tell process "Simulator" to click (first menu item of menu 1 of menu item "External Displays" of menu 1 of menu bar item "I/O" of menu bar 1 whose name starts with "CarPlay")' 2> shots-ci/osascript.txt
sleep 4
if [ -n "$CARPLAY_SIZE" ]; then
  W=${CARPLAY_SIZE%%x*}; R=${CARPLAY_SIZE#*x}; H=${R%%@*}; S=${R#*@}
  # Dump the dialog so a layout change is easy to see, then fill width/height/scale and confirm.
  osascript -e 'tell application "System Events" to tell process "Simulator" to get entire contents of front window' > shots-ci/size-dialog.txt 2>&1
  screencapture -x shots-ci/size-dialog.png
  osascript -e "tell application \"System Events\" to tell process \"Simulator\"" \
    -e "set w to front window" -e "set tf to every text field of w" \
    -e "if (count of tf) >= 2 then" -e "set value of item 1 of tf to \"$W\"" -e "set value of item 2 of tf to \"$H\"" -e "end if" \
    -e "try" -e "set pb to every pop up button of w" -e "if (count of pb) >= 1 then" -e "click item 1 of pb" -e "delay 1" -e "click menu item (\"@$S\" as text) of menu 1 of item 1 of pb" -e "end if" -e "end try" \
    -e "try" -e "click button \"OK\" of w" -e "on error" -e "try" -e "click button \"Start\" of w" -e "on error" -e "key code 36" -e "end try" -e "end try" -e "end tell" >> shots-ci/size-dialog.txt 2>&1
fi
sleep 10
WIN='tell application "System Events" to tell process "Simulator" to set w to (first window whose name contains "CarPlay")'
osascript -e "$WIN" -e 'tell application "System Events" to tell process "Simulator" to set position of w to {0, 40}' >> shots-ci/osascript.txt 2>&1
osascript -e "$WIN" -e 'tell application "System Events" to tell process "Simulator" to get {position, size} of w' > shots-ci/carplay-window.txt 2>&1
sleep 2
screencapture -x shots-ci/carplay-home.png
# Open our app from the CarPlay sidebar (screen coords, CARPLAY_TAPS="x,y x,y"); the sidebar icon sits at the same spot at every size.
osascript -e "$WIN" -e 'tell application "System Events" to tell process "Simulator" to perform action "AXRaise" of w' >> shots-ci/osascript.txt 2>&1
for xy in ${CARPLAY_TAPS:-}; do cliclick m:$xy w:300 dd:. w:120 du:. ; sleep 4; screencapture -x shots-ci/carplay-tap-$xy.png; done
sleep 20
screencapture -x shots-ci/carplay-preview.png
xcrun simctl io "$DEV" screenshot --display=external shots-ci/cp-ext-preview.png 2>>shots-ci/ext-err.txt || true
sleep 35
if [ "${CELEBRATE_LOOP:-NO}" = "YES" ]; then for i in $(seq -w 1 10); do sleep 2.5; screencapture -x shots-ci/carplay-celebrate-$i.png; xcrun simctl io "$DEV" screenshot --display=external shots-ci/cp-ext-celebrate-$i.png 2>>shots-ci/ext-err.txt || true; done; fi
screencapture -x shots-ci/carplay-guidance.png
# demo drive: one shot every 4 s while the car steps through the maneuvers
if [ "${DEMO_DRIVE:-0}" != "0" ]; then for i in $(seq -w 1 22); do sleep 4; screencapture -x shots-ci/carplay-drive-$i.png; xcrun simctl io "$DEV" screenshot --display=external shots-ci/cp-ext-$i.png 2>>shots-ci/ext-err.txt || true; done; fi
# Off-route check: drive the simulated GPS away from the planned route; the app should log
# "GCMCarPlay reroute" after ~5 s off route and redraw the line and card.
if [ -n "${OFFROUTE_TRACK:-}" ]; then
  xcrun simctl location "$DEV" start --speed=${OFFROUTE_SPEED:-8} --interval=1 $OFFROUTE_TRACK 2>>shots-ci/ext-err.txt
  for i in $(seq -w 1 16); do sleep 5; screencapture -x shots-ci/carplay-off-$i.png; done
  xcrun simctl location "$DEV" clear || true
fi
xcrun simctl spawn "$DEV" log show --last 10m --predicate 'process == "App"' --style compact > shots-ci/app-log.txt 2>&1
cp ~/Library/Logs/DiagnosticReports/App*.ips shots-ci/ 2>/dev/null
ls -la shots-ci
