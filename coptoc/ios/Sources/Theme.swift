import SwiftUI

enum Theme {
    static let bg = Color(red: 0.03, green: 0.04, blue: 0.06)
    static let panel = Color(red: 0.05, green: 0.07, blue: 0.10)
    static let panel2 = Color(red: 0.08, green: 0.11, blue: 0.15)
    static let line = Color(red: 0.11, green: 0.15, blue: 0.21)
    static let dim = Color(red: 0.42, green: 0.49, blue: 0.56)
    static let blue = Color(red: 0.38, green: 0.65, blue: 0.98)
    static let gold = Color(red: 0.98, green: 0.75, blue: 0.14)
    static let green = Color(red: 0.13, green: 0.77, blue: 0.37)
    static let amber = Color(red: 0.96, green: 0.62, blue: 0.04)
    static let orange = Color(red: 0.98, green: 0.45, blue: 0.09)
    static let red = Color(red: 0.94, green: 0.27, blue: 0.27)
    static let purple = Color(red: 0.75, green: 0.52, blue: 0.99)

    static let lime = Color(red: 0.64, green: 0.90, blue: 0.21)
    static func posture(_ p: String) -> Color { p == "critical" ? red : p == "high" ? orange : p == "elevated" ? amber : p == "guarded" ? lime : green }
    static func severity(_ s: String) -> Color { s == "critical" || s == "elevated" ? red : s == "moderate" ? orange : amber }
    static func confidence(_ c: String) -> Color { c == "high" ? green : c == "moderate" ? amber : c == "low" ? red : dim }
}

struct Chip: View {
    var text: String; var color: Color = Theme.dim; var filled = false
    var body: some View {
        Text(text).font(.system(size: 9, weight: .bold, design: .monospaced)).tracking(0.8).lineLimit(1).fixedSize()
            .padding(.horizontal, 6).padding(.vertical, 3)
            .foregroundStyle(filled ? .white : color)
            .background(filled ? color : color.opacity(0.12), in: RoundedRectangle(cornerRadius: 4))
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(color.opacity(filled ? 0 : 0.5), lineWidth: 1))
    }
}

struct SectionLabel: View {
    var text: String
    var body: some View { Text(text).font(.system(size: 10, weight: .semibold, design: .monospaced)).tracking(1.6).foregroundStyle(Theme.dim).padding(.top, 6) }
}

struct PanelHead: View {
    @Environment(COPStore.self) private var store
    var code: String; var title: String; var hint: String? = nil
    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            if !code.isEmpty {
                Text(code).font(.system(size: 13, weight: .heavy, design: .monospaced)).foregroundStyle(Theme.blue)
                    .padding(.horizontal, 6).padding(.vertical, 2).background(Theme.blue.opacity(0.12), in: RoundedRectangle(cornerRadius: 3))
            }
            Text(title).font(.system(size: 12, weight: .bold, design: .monospaced)).tracking(2)
            Spacer()
            if let hint, !store.leanLabels { Text(hint).font(.system(size: 10)).foregroundStyle(Theme.dim) }
        }
    }
}


/// The running-estimate line under a panel head (§3.1). Read-only on the phone; edited from the wall.
struct EstimateLine: View {
    @Environment(COPStore.self) private var store
    var e: Estimate?
    var body: some View {
        if let e, !(store.leanLabels && e.assessment.isEmpty) {
            VStack(alignment: .leading, spacing: 2) {
                (Text("\(e.section) assesses: ").font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundColor(Theme.blue)
                 + Text(e.assessment.isEmpty ? "no assessment on record" : e.assessment).font(.system(size: 12)).foregroundColor(e.assessment.isEmpty ? Theme.dim : .primary))
                if !e.recommendation.isEmpty { Text("↳ \(e.recommendation)").font(.system(size: 11)).foregroundStyle(.secondary) }
            }
        }
    }
}


extension View {
    /// Feed this container's scroll offset to the dock (iOS 18 scroll geometry — List rows do not report their frames while scrolling).
    func drivesDock(_ store: COPStore) -> some View {
        onScrollGeometryChange(for: CGFloat.self) { $0.contentOffset.y + $0.contentInsets.top } action: { _, y in store.trackBarScroll(-y) }
    }
}


/// §3 the map-first sections: the picture behind, the section's list on a sheet with three rests — peek, half, full.
struct SectionTab<Content: View>: View {
    var section: String
    @ViewBuilder var content: () -> Content
    var body: some View {
        ZStack(alignment: .bottom) {
            // The map is built here and never again while the sheet moves. It used to sit in the same body as the
            // drag state, so every frame of a drag rebuilt a MapKit view carrying every site, traveller, route and
            // threat ring — which is what made a slow drag crawl.
            MapScreen(layer: section)
            SectionSheet(section: section, content: content())
        }
    }
}

/// The sheet: it owns the drag, so a drag invalidates this and nothing else.
private struct SectionSheet<Content: View>: View {
    @Environment(COPStore.self) private var store
    var section: String
    var content: Content
    @State private var rest: CGFloat = 0     // the resting height in points; 0 until the first layout resolves it
    @State private var drag: CGFloat = 0
    private let grip: CGFloat = 52           // the handle is a comfortable target, not a hairline
    private let dock: CGFloat = 104          // the floating tab bar and a thumb of clearance above it

    /// Peek leaves the handle above the tab bar rather than behind it; half and full are fractions of the wall.
    func rests(_ h: CGFloat) -> [CGFloat] { [grip + dock, h * 0.55, h * 0.92] }

    var body: some View {
        GeometryReader { g in
            let stops = rests(g.size.height)
            let base = rest > 0 ? rest : stops[1]
            let visible = min(max(base - drag, stops[0]), stops[2])
            VStack(spacing: 0) {
                VStack(spacing: 5) {
                    Capsule().fill(Theme.dim.opacity(0.6)).frame(width: 48, height: 5)
                    Text(base <= stops[0] + 1 ? "\(section) · pull up" : "\(section)")
                        .font(.system(size: 9, weight: .bold, design: .monospaced)).tracking(1.5).foregroundStyle(Theme.dim)
                }
                .frame(maxWidth: .infinity, minHeight: grip).contentShape(Rectangle())
                // One gesture, not a drag and a tap competing: arbitration between them cost a beat at the start of
                // every drag. High priority, because the map underneath runs UIKit pan recognisers that were winning
                // a touch that started on the handle.
                // Global coordinates, not the sheet's own: the handle moves as the sheet moves, so a drag measured in
                // local space is measured against an origin the drag itself is shifting. That feedback is what made
                // the header shake — push up, the sheet rises, the origin rises with it, the next sample reads short.
                .highPriorityGesture(DragGesture(minimumDistance: 0, coordinateSpace: .global)
                    .onChanged { v in if abs(v.translation.height) > 2 { drag = v.translation.height } }
                    .onEnded { v in
                        let moved = v.translation.height
                        let settled: CGFloat = abs(moved) < 6
                            ? stops[(( stops.firstIndex(of: base) ?? 1) + 1) % stops.count]      // a tap cycles the rests
                            : stops.min(by: { abs($0 - (base - moved)) < abs($1 - (base - moved)) })!
                        withAnimation(.spring(response: 0.32, dampingFraction: 0.86)) { rest = settled; drag = 0 }
                    })
                content.frame(maxHeight: .infinity)
            }
            .frame(height: stops[2], alignment: .top)   // laid out once at full height and slid: resizing it on every
            .background(Theme.bg.opacity(0.96), in: UnevenRoundedRectangle(topLeadingRadius: 16, topTrailingRadius: 16))
            .overlay(alignment: .top) { UnevenRoundedRectangle(topLeadingRadius: 16, topTrailingRadius: 16).stroke(Theme.line, lineWidth: 0.5) }
            .shadow(color: .black.opacity(0.4), radius: 12, y: -4)
            .offset(y: stops[2] - visible)              // frame re-measured the whole list under the finger
            .frame(maxHeight: .infinity, alignment: .bottom)
            .onAppear { if rest == 0 { rest = stops[1] } }
            // Tapping the section's own tab cycles the sheet:
            // Tap 1: switches to that tab (starts at stops[1], medium)
            // Tap 2: increases the size of the overlay to full (stops[2])
            // Tap 3: reduces the size down to the minimum level (stops[0])
            .onChange(of: store.sheetRaise) {
                let i = stops.enumerated().min(by: { abs($0.element - rest) < abs($1.element - rest) })?.offset ?? 1
                let next = stops[(i + 1) % stops.count]
                withAnimation(.spring(response: 0.32, dampingFraction: 0.86)) { rest = next }
            }
        }
    }
}
