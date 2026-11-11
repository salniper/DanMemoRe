package dev.danmemore.launcher

/**
 * Pure, Android-independent policy for the opt-in preserved 2024 content snapshot.
 * The policy does not authorize unknown bytes or additional missing files.
 */
internal object LegacyImportPolicy {
    enum class Match { REFERENCE, HISTORICAL, UNKNOWN }

    private val allowedPhase1Missing = setOf(
        "files/lwf/uiLwf/home/lwf_title_effect/lwf_title_effect_1.lwf",
        "files/lwf/uiLwf/home/lwf_title_effect/lwf_title_effect_1.png",
        "files/lwf/uiLwf/home/lwf_title_logo/lwf_title_logo.lwf",
        "files/lwf/uiLwf/home/lwf_title_logo/lwf_title_logo.png",
        "files/lwf/uiLwf/iphone_x/home/lwf_title_effect/lwf_title_effect_1.lwf",
        "files/lwf/uiLwf/iphone_x/home/lwf_title_effect/lwf_title_effect_1.png",
        "files/sound/bgm/bgm_main_theme.ogg",
        "files/ui/title/bg_1.jpg",
        "files/ui/title/iphone_x/bg_1.jpg",
        "files/ui_atlas/home_other/modal_ai_select_confirm.json",
        "files/ui_atlas/home_other/modal_charge.json",
        "files/ui_atlas/home_other/modal_configuration.json",
        "files/ui_atlas/home_other/modal_configuration_scroll_version_parts.json",
        "files/ui_atlas/home_other/modal_confirmation.json",
        "files/ui_atlas/home_other/modal_cp_list.json",
        "files/ui_atlas/home_other/modal_expired.json",
        "files/ui_atlas/home_other/modal_feat_list.json",
        "files/ui_atlas/home_other/modal_feat_list_cell.json",
        "files/ui_atlas/home_other/modal_help_list.json",
        "files/ui_atlas/home_other/modal_input_introduction.json",
        "files/ui_atlas/home_other/modal_news_support.json",
        "files/ui_atlas/home_other/modal_pvp_caution_confirm.json",
        "files/ui_atlas/home_other/modal_receipt_result.json",
        "files/ui_atlas/home_other/modal_social_share.json",
        "files/ui_atlas/home_other/modal_stamina_error.json",
        "files/ui_atlas/home_other/modal_transfer_code_publish_complete.json",
        "files/ui_atlas/home_other/modal_transfer_code_publish_confirm.json",
        "files/ui_atlas/home_other/present_box_received_confirm_error_celll.json",
        "files/ui_atlas/home_other/profile_top_character_name.json",
        "files/ui_atlas/network/modal_maintenance.json",
        "files/ui_atlas/network/modal_network_error.json",
        "files/ui_atlas/network/network_state.json",
        "files/ui_atlas/network/textures.0.plist"
    )

    fun classify(
        actualSize: Long,
        actualMd5: String,
        referenceSize: Long,
        referenceMd5: String,
        historicalSize: Long?,
        historicalMd5: String?,
    ): Match = when {
        actualSize == referenceSize && actualMd5 == referenceMd5 -> Match.REFERENCE
        historicalSize != null && historicalMd5 != null &&
            actualSize == historicalSize && actualMd5 == historicalMd5 -> Match.HISTORICAL
        else -> Match.UNKNOWN
    }

    fun permitsMissing(
        phase: Int,
        relative: String,
        inHistoricalCatalog: Boolean,
        bundledGachaBackgrounds: Set<String>,
    ): Boolean = when (phase) {
        1 -> inHistoricalCatalog && relative in allowedPhase1Missing
        3 -> relative.startsWith("files/lottery/background/") &&
            relative.removePrefix("files/lottery/background/") in bundledGachaBackgrounds
        else -> false
    }
}
