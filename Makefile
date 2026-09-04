# Use the local venv when it exists (dev), otherwise whatever is on PATH (CI).
VENV_BIN := $(if $(wildcard .venv/bin/python),.venv/bin/,)
PYTHON ?= $(VENV_BIN)python
PYTEST ?= $(VENV_BIN)pytest
UVICORN ?= $(VENV_BIN)uvicorn

.PHONY: test test-coptoc test-sigtoc test-modtoc test-integration diff lint run-api run-mod run-web run-cop ios-gen ios-build ios-run

test:
	$(PYTEST) tests/ -v

test-coptoc:
	$(PYTEST) tests/coptoc/ -v

test-modtoc:
	$(PYTEST) tests/modtoc/ -v

test-sigtoc:
	$(PYTEST) tests/sigtoc/ -v

test-integration:
	$(PYTEST) tests/integration/ -v

diff:
	PYTHONPATH=shared:modtoc $(PYTHON) modtoc/evals/harness.py --policy modtoc/policies/hate_speech.yaml --golden modtoc/evals/golden_sets/hate_speech_golden.json

run-api:
	PYTHONPATH=shared:coptoc/api:sigtoc $(UVICORN) coptoc.app:app --reload --port 8000

run-mod:
	PYTHONPATH=shared:modtoc $(UVICORN) modtoc.api:app --reload --port 8001

run-s2:
	PYTHONPATH=shared:sigtoc:coptoc/api $(UVICORN) sigtoc.api:app --reload --port 8002

run-web:
	npm --prefix coptoc/web run dev

# Both halves of the COP: API on :8000, web app on :5173 (proxies /v1 to the API)
run-cop:
	$(MAKE) -j2 run-api run-web

ios-gen:
	cd coptoc/ios && xcodegen generate

ios-build: ios-gen
	cd coptoc/ios && xcodebuild -project TOC.xcodeproj -scheme TOC -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath build CODE_SIGNING_ALLOWED=NO build | grep -E "error:|BUILD"

ios-run: ios-build
	xcrun simctl boot "iPhone 17 Pro" 2>/dev/null || true
	xcrun simctl install booted coptoc/ios/build/Build/Products/Debug-iphonesimulator/TOC.app
	xcrun simctl launch booted com.h4yd3n.TOC

# ---- Android (coptoc/android) — needs the Android SDK and a JDK 17+; Android Studio's bundled JBR works:
#   JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" make android-build
ANDROID_DIR := coptoc/android
ADB := $(HOME)/Library/Android/sdk/platform-tools/adb
android-build:
	cd $(ANDROID_DIR) && ./gradlew :app:assembleDebug
android-run: android-build
	$(ADB) install -r $(ANDROID_DIR)/app/build/outputs/apk/debug/app-debug.apk && $(ADB) shell am start -n com.toc.coptoc/.MainActivity
