// Top-level build file — plugin versions come from gradle/libs.versions.toml (same toolchain as the author's Washi apps).
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
}
