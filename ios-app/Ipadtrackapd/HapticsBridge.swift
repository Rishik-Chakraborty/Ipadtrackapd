import Foundation
import WebKit
import UIKit

class HapticsBridge: NSObject, WKScriptMessageHandler {
    // Keep generators around for performance (pre-warming)
    private var impactGenerators: [UIImpactFeedbackGenerator.FeedbackStyle: UIImpactFeedbackGenerator] = [:]
    private var selectionGenerator: UISelectionFeedbackGenerator?
    private var notificationGenerator: UINotificationFeedbackGenerator?
    
    private var idleTimer: Timer?
    
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any],
              let type = body["type"] as? String else { return }
        
        switch type {
        case "impact":
            let styleStr = body["style"] as? String ?? "light"
            let style = impactStyle(from: styleStr)
            
            let generator = getImpactGenerator(for: style)
            generator.impactOccurred()
            
        case "selection":
            let generator = getSelectionGenerator()
            generator.selectionChanged()
            
        case "notification":
            let styleStr = body["style"] as? String ?? "success"
            let type = notificationType(from: styleStr)
            
            let generator = getNotificationGenerator()
            generator.notificationOccurred(type)
            
        case "prepare":
            // Pre-warm the most common generators
            getImpactGenerator(for: .light).prepare()
            getImpactGenerator(for: .medium).prepare()
            getSelectionGenerator().prepare()
            
            resetIdleTimer()
            
        default:
            print("Unknown haptic type: \(type)")
        }
    }
    
    private func impactStyle(from string: String) -> UIImpactFeedbackGenerator.FeedbackStyle {
        switch string {
        case "light": return .light
        case "medium": return .medium
        case "heavy": return .heavy
        case "rigid": return .rigid
        case "soft": return .soft
        default: return .light
        }
    }
    
    private func notificationType(from string: String) -> UINotificationFeedbackGenerator.FeedbackType {
        switch string {
        case "success": return .success
        case "warning": return .warning
        case "error": return .error
        default: return .success
        }
    }
    
    private func getImpactGenerator(for style: UIImpactFeedbackGenerator.FeedbackStyle) -> UIImpactFeedbackGenerator {
        if let gen = impactGenerators[style] { return gen }
        let gen = UIImpactFeedbackGenerator(style: style)
        impactGenerators[style] = gen
        return gen
    }
    
    private func getSelectionGenerator() -> UISelectionFeedbackGenerator {
        if let gen = selectionGenerator { return gen }
        let gen = UISelectionFeedbackGenerator()
        selectionGenerator = gen
        return gen
    }
    
    private func getNotificationGenerator() -> UINotificationFeedbackGenerator {
        if let gen = notificationGenerator { return gen }
        let gen = UINotificationFeedbackGenerator()
        notificationGenerator = gen
        return gen
    }
    
    private func resetIdleTimer() {
        idleTimer?.invalidate()
        idleTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: false) { [weak self] _ in
            self?.releaseGenerators()
        }
    }
    
    private func releaseGenerators() {
        impactGenerators.removeAll()
        selectionGenerator = nil
        notificationGenerator = nil
    }
}
