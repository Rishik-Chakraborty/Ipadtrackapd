import SwiftUI
import WebKit

struct WebViewContainer: UIViewRepresentable {
    let url: String
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.userContentController.add(context.coordinator, name: "haptics")
        
        // Improve gesture recognition by disabling some default webview behaviors
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []
        
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.scrollView.isScrollEnabled = false // We handle scrolling ourself in JS
        webView.scrollView.bounces = false
        webView.isMultipleTouchEnabled = true
        
        return webView
    }
    
    func updateUIView(_ webView: WKWebView, context: Context) {
        if let u = URL(string: url) {
            let request = URLRequest(url: u)
            webView.load(request)
        }
    }
    
    class Coordinator: NSObject, WKScriptMessageHandler {
        var parent: WebViewContainer
        let hapticsBridge = HapticsBridge()
        
        init(_ parent: WebViewContainer) {
            self.parent = parent
        }
        
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            hapticsBridge.userContentController(userContentController, didReceive: message)
        }
    }
}
