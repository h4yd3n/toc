// AGP 9 has BUILT-IN Kotlin — do not apply org.jetbrains.kotlin.android (same as the author's Washi apps).
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "com.toc.coptoc"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.toc.coptoc"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"
        // The emulator reaches the Mac's FastAPI at 10.0.2.2. Override: -PtocApi=http://<lan-ip>:8000
        buildConfigField("String", "TOC_API", "\"${project.findProperty("tocApi") ?: "http://10.0.2.2:8000"}\"")
    }
    buildTypes {
        release { isMinifyEnabled = false }
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    packaging { resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" } }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.compose.material.icons)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.maplibre)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
