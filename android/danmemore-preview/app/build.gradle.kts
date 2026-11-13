plugins {
    id("com.android.application")
}

android {
    namespace = "dev.danmemore.preview"
    compileSdk = 35
    defaultConfig {
        applicationId = "dev.danmemore.preview"
        minSdk = 26
        targetSdk = 32
        versionCode = 1
        versionName = "0.1.0-preview"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
