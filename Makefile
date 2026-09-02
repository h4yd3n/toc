# Use the local venv when it exists (dev), otherwise whatever is on PATH (CI).
VENV_BIN := $(if $(wildcard .venv/bin/python),.venv/bin/,)
PYTHON ?= $(VENV_BIN)python
PYTEST ?= $(VENV_BIN)pytest
UVICORN ?= $(VENV_BIN)uvicorn

.PHONY: test test-coptoc test-sigtoc test-integration diff lint run-api run-web run-cop ios-gen ios-build ios-run

test:
	$(PYTEST) tests/ -v

test-coptoc:
	$(PYTEST) tests/coptoc/ -v

test-sigtoc:
	$(PYTEST) tests/sigtoc/ -v

test-integration:
	$(PYTEST) tests/integration/ -v

diff:
	PYTHONPATH=packages/shared/src:apps/coptoc/src $(PYTHON) apps/coptoc/evals/harness.py --policy apps/coptoc/policies/hate_speech.yaml --golden apps/coptoc/evals/golden_sets/hate_speech_golden.json

run-api:
	PYTHONPATH=packages/shared/src:apps/coptoc/src:apps/sigtoc/src $(UVICORN) coptoc.api.server:app --reload --port 8000

run-web:
	npm --prefix apps/cop-web run dev

# Both halves of the COP: API on :8000, web app on :5173 (proxies /v1 to the API)
run-cop:
	$(MAKE) -j2 run-api run-web

ios-gen:
	cd apps/cop-ios && xcodegen generate

ios-build: ios-gen
	cd apps/cop-ios && xcodebuild -project TOC.xcodeproj -scheme TOC -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath build CODE_SIGNING_ALLOWED=NO build | grep -E "error:|BUILD"

ios-run: ios-build
	xcrun simctl boot "iPhone 17 Pro" 2>/dev/null || true
	xcrun simctl install booted apps/cop-ios/build/Build/Products/Debug-iphonesimulator/TOC.app
	xcrun simctl launch booted com.h4yd3n.TOC
