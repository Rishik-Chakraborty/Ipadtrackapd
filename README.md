# Ipadtrackapd

iPad-as-Trackpad for Mac. Uses an iPad as a wireless trackpad for a Mac over local Wi-Fi, offering full gesture parity and real haptic feedback.

## Requirements
- Mac with Python 3.14+
- iPad

## Quickstart

### Mac Server
1. Clone the repository to your Mac.
2. Run the server:
   ```bash
   ./scripts/run.sh
   ```
3. A QR code and URL will be displayed in your terminal. You can scan this QR code or navigate to the URL on your iPad.

### iOS App (for real haptics)
If you want to use the native Taptic Engine for haptics, you should build and run the iOS wrapper onto your iPad.
1. Make sure you have Xcode and `xcodegen` installed.
   ```bash
   brew install xcodegen
   ```
2. Navigate to the `ios-app` folder and generate the `.xcodeproj` file:
   ```bash
   cd ios-app
   xcodegen generate
   ```
3. Open `Ipadtrackapd.xcodeproj` in Xcode.
4. Set the Signing Team to your Apple ID.
5. Connect your iPad to your Mac, select it as the run destination, and click Run.
