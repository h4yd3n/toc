# TOC — native iOS COP

SwiftUI + MapKit client for the same `/v1/cop` backend the web wall uses. Contract: `../coptoc/COP_API_CONTRACT.md`.

```sh
brew install xcodegen          # once
xcodegen generate              # → TOC.xcodeproj (git-ignored build artifact)
open TOC.xcodeproj             # or: make ios-build / make ios-run from the repo root
```

The simulator reaches the FastAPI backend on `http://localhost:8000` (override with `TOC_API` in the scheme environment).
Tabs: **COP** (map — sites, travelers, threat rings, routes, event venues), **S1** personnel, **S2** intelligence, **S3** operations + battle log.
Tap anything → detail sheet with the same actions as the wall: set posture, confirm a threat link, draft an S2 assessment, check in.
