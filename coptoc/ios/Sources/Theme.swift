import SwiftUI

enum Theme {
    static let bg = Color(red: 0.03, green: 0.04, blue: 0.06)
    static let panel = Color(red: 0.05, green: 0.07, blue: 0.10)
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
            Text(code).font(.system(size: 13, weight: .heavy, design: .monospaced)).foregroundStyle(Theme.blue)
                .padding(.horizontal, 6).padding(.vertical, 2).background(Theme.blue.opacity(0.12), in: RoundedRectangle(cornerRadius: 3))
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
