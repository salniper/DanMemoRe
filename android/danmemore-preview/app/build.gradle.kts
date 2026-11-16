plugins {
    id("com.android.application")
}

android {
    namespace = "dev.danmemore.preview"
    compileSdk = 35
    defaultConfig {
        applicationId = "dev.danmemore.preview.v2"
        minSdk = 26
        targetSdk = 32
        versionCode = 2
        versionName = "0.2.0-preview"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
