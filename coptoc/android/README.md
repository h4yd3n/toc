# Coptoc — Android

The wall on a phone or tablet, native Kotlin + Jetpack Compose + MapLibre Native, mirroring the iOS app and the same
`COP_API_CONTRACT.md`. Same toolchain as the author's Washi apps: AGP 9 (built-in Kotlin), Kotlin 2.2, Compose BOM 2026.02.

```bash
# from the repo root; Android Studio's bundled JDK is enough
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" make android-run
```

The emulator reaches the Mac's API at `http://10.0.2.2:8000` (`make run-api`). For a physical device on the same
network: `./gradlew :app:assembleDebug -PtocApi=http://<your-mac-lan-ip>:8000` — cleartext is allowed only for those
dev hosts (`res/xml/network_security_config.xml`).

What it does today: the header strip (posture, watch, counts, role picker), S1 sites and travelers with check-in
freshness, open roll calls with the roster and every contact action, S2 requirements with coverage bars, the latest
INTSUM headline, threats (live vs synthetic) and assessments with approve, S3 events and trips with the operation
chip, the battle log, and the map with sites by posture, travelers, events, and threat rings. Actions are role-gated
exactly as on the wall. Android's `HttpURLConnection` cannot send PATCH; the client sends POST with
`X-HTTP-Method-Override: PATCH`, which the API honours.
