import SwiftUI

@main
struct TOCApp: App {
    @State private var store = COPStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(store)
                .preferredColorScheme(.dark)
                .task { await store.start() }
        }
    }
}
