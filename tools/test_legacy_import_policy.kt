package dev.danmemore.launcher

// Run without the Android SDK:
// kotlinc android/danmemore-launcher/app/src/main/kotlin/dev/danmemore/launcher/LegacyImportPolicy.kt \
//   tools/test_legacy_import_policy.kt -include-runtime -d /tmp/danmemore-legacy-policy-test.jar
// java -jar /tmp/danmemore-legacy-policy-test.jar

fun main() {
    val reference = "a".repeat(32)
    val historical = "b".repeat(32)
    val changed = "c".repeat(32)

    fun checkMatch(
        actualSize: Long,
        actualMd5: String,
        expected: LegacyImportPolicy.Match,
    ) {
        val actual = LegacyImportPolicy.classify(
            actualSize, actualMd5, 50, reference, 70, historical
        )
        check(actual == expected) { "Expected $expected but found $actual" }
    }

    checkMatch(50, reference, LegacyImportPolicy.Match.REFERENCE)
    checkMatch(70, historical, LegacyImportPolicy.Match.HISTORICAL)
    checkMatch(50, changed, LegacyImportPolicy.Match.UNKNOWN)
    checkMatch(70, reference, LegacyImportPolicy.Match.UNKNOWN)
    checkMatch(50, historical, LegacyImportPolicy.Match.UNKNOWN)
    checkMatch(70, changed, LegacyImportPolicy.Match.UNKNOWN)
    check(
        LegacyImportPolicy.classify(70, historical, 50, reference, null, null) ==
            LegacyImportPolicy.Match.UNKNOWN
    )

    val knownTitle = "files/ui/title/bg_1.jpg"
    val gachaName = "171000001.png"
    val gacha = setOf(gachaName)
    check(LegacyImportPolicy.permitsMissing(1, knownTitle, true, emptySet()))
    check(!LegacyImportPolicy.permitsMissing(1, knownTitle, false, emptySet()))
    check(!LegacyImportPolicy.permitsMissing(1, "files/ui/title/unlisted.jpg", true, emptySet()))
    check(!LegacyImportPolicy.permitsMissing(2, knownTitle, true, emptySet()))
    check(LegacyImportPolicy.permitsMissing(3, "files/lottery/background/$gachaName", false, gacha))
    check(!LegacyImportPolicy.permitsMissing(3, "files/lottery/background/other.png", false, gacha))
    check(!LegacyImportPolicy.permitsMissing(3, "files/ui/title/bg_1.jpg", true, gacha))
    check(!LegacyImportPolicy.permitsMissing(4, "files/lottery/background/$gachaName", false, gacha))

    println("LegacyImportPolicy: 15 assertions passed")
}
