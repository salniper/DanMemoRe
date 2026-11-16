plugins {
    kotlin("jvm") version "2.3.0"
    application
}

repositories {
    mavenCentral()
}

// Minimal JVM-only validation: do not configure the Android launcher project.
// That project requires a separately supplied Node Mobile libnode distribution.
kotlin {
    jvmToolchain(17)
    sourceSets {
        main {
            kotlin.srcDir("../../android/danmemore-launcher/app/src/main/kotlin/dev/danmemore/launcher")
            kotlin.srcDir("..")
            kotlin.include("LegacyImportPolicy.kt", "test_legacy_import_policy.kt")
        }
    }
}

application {
    mainClass.set("dev.danmemore.launcher.Test_legacy_import_policyKt")
}
