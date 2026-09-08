import SwiftUI
import WebKit

/// Interim shared console, restricted to the configured API origin. Profile IDs are
/// the existing demo identity, not credentials; production SSO remains a separate milestone.
struct WorkspaceBrowser: UIViewRepresentable {
    let baseURL: URL
    let userId: String
    let section: String

    func makeCoordinator() -> Coordinator { Coordinator(baseURL: baseURL) }
    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.isOpaque = false
        view.backgroundColor = .black
        var components = URLComponents(url: baseURL.appending(path: "console/"), resolvingAgainstBaseURL: false)!
        components.queryItems = [URLQueryItem(name: "embedded", value: "1"), URLQueryItem(name: "profile", value: userId)]
        components.fragment = "/workspace/\(section)/overview"
        view.load(URLRequest(url: components.url!))
        return view
    }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
    final class Coordinator: NSObject, WKNavigationDelegate {
        let baseURL: URL
        init(baseURL: URL) { self.baseURL = baseURL }
        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = action.request.url,
                  url.scheme == baseURL.scheme, url.host == baseURL.host, url.port == baseURL.port else {
                decisionHandler(.cancel); return
            }
            decisionHandler(.allow)
        }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            webView.loadHTMLString("<html><body style='background:#121820;color:white;font:18px system-ui;padding:24px'><h2>Workspace unavailable</h2><p>Check your connection. The API server must serve the web build at /console/. Your unsent updates have not been saved.</p></body></html>", baseURL: baseURL)
        }
    }
}
