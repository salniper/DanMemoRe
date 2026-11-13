package dev.danmemore.preview;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

import java.security.SecureRandom;
import java.util.Locale;

/**
 * Original offline demo, NOT a revived original DanMemo / Memoria Freese app.
 *
 * 0.2: Landscape game layout, self-drawn fantasy scenery, controller support
 * and clearer prototype game flows. Keeps the original 0.1 preference schema,
 * but uses a separate Android package to avoid destroying the 0.1 save when
 * GitHub runner-generated debug signing keys change.
 *
 * Does not request networking/storage access or import proprietary assets.
 */
public final class MainActivity extends Activity {
    private static final int BG = Color.rgb(7, 14, 25);
    private static final int RAIL = Color.rgb(13, 26, 39);
    private static final int PANEL = Color.rgb(18, 36, 51);
    private static final int PANEL_BRIGHT = Color.rgb(25, 49, 62);
    private static final int BORDER = Color.rgb(49, 76, 85);
    private static final int INK = Color.rgb(237, 243, 246);
    private static final int SOFT = Color.rgb(160, 185, 194);
    private static final int GOLD = Color.rgb(235, 189, 117);
    private static final int TEAL = Color.rgb(92, 210, 190);
    private static final int RED = Color.rgb(241, 133, 124);

    private static final String[] TABS = {"首頁", "劇情", "戰鬥", "抽卡", "存檔"};
    private static final String[] SCENES = {
        "一封沒有署名的委託，出現在安靜的冒險者公會。\n\n窗外的街燈還未點亮，你卻已經聽見遠處傳來的鐘聲。",
        "你走進迷宮入口，牆面上的火把照亮了陌生的足跡。\n\n有人比你更早來到這裡。那個人，究竟在尋找什麼？",
        "轉角傳來沉重的腳步聲，一隻守衛獸擋住通往下一層的階梯。\n\n你握緊武器，決定先找出牠的弱點。",
        "擊退守衛獸後，你拾起刻著星紋的石片。\n\n石片在掌心微微發光。冒險，才剛開始。"
    };
    private static final String[] HEROES = {
        "見習劍士", "風之術師", "遺跡射手", "迷宮守護者", "星紋旅者"
    };
    private static final String[] ROLES = {
        "近戰 · 劍", "魔法 · 風", "遠程 · 弓", "防禦 · 盾", "支援 · 星"
    };

    private final SecureRandom rng = new SecureRandom();
    private SharedPreferences prefs;
    private LinearLayout content;
    private int page;
    private boolean wide;
    private Button defaultButton;
    private String notice = "離線系統就緒。這是獨立測試版，不含原版遊戲資產。";

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        prefs = getSharedPreferences("danmemore-preview-v1", MODE_PRIVATE);
        render(saved == null ? 0 : Math.max(0, Math.min(4, saved.getInt("page", 0))));
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        state.putInt("page", page);
        super.onSaveInstanceState(state);
    }

    private int get(String key, int fallback) {
        return prefs.getInt(key, fallback);
    }

    private void put(String key, int value) {
        prefs.edit().putInt(key, value).apply();
    }

    private int dp(float amount) {
        return (int) (getResources().getDisplayMetrics().density * amount + .5f);
    }

    private GradientDrawable shape(int color, int radius, boolean border) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radius));
        if (border) drawable.setStroke(dp(1), BORDER);
        return drawable;
    }

    private GradientDrawable heroShape() {
        GradientDrawable drawable = new GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                new int[]{Color.rgb(26, 55, 65), Color.rgb(14, 29, 44),
                          Color.rgb(21, 31, 45)});
        drawable.setCornerRadius(dp(19));
        drawable.setStroke(dp(1), BORDER);
        return drawable;
    }

    private TextView text(String value, float sp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextColor(color);
        t.setTextSize(sp);
        t.setGravity(Gravity.CENTER_VERTICAL);
        if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        t.setLineSpacing(dp(2), 1.05f);
        return t;
    }

    private LinearLayout column() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        return l;
    }

    private LinearLayout row() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.HORIZONTAL);
        l.setGravity(Gravity.CENTER_VERTICAL);
        return l;
    }

    private void gap(LinearLayout parent, int height) {
        View spacer = new View(this);
        parent.addView(spacer, new LinearLayout.LayoutParams(dp(1), dp(height)));
    }

    private void addText(LinearLayout parent, String value, float size,
                         int color, boolean bold, int below) {
        TextView t = text(value, size, color, bold);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.bottomMargin = dp(below);
        parent.addView(t, params);
    }

    private LinearLayout panel() {
        LinearLayout pane = column();
        pane.setPadding(dp(19), dp(16), dp(19), dp(16));
        pane.setBackground(shape(PANEL, 17, true));
        LinearLayout.LayoutParams margins = new LinearLayout.LayoutParams(-1, -2);
        margins.bottomMargin = dp(13);
        content.addView(pane, margins);
        return pane;
    }

    private void card(String heading, String description) {
        LinearLayout pane = panel();
        addText(pane, heading, 18, GOLD, true, 8);
        addText(pane, description, 15, INK, false, 0);
    }

    private void note(String value) {
        addText(content, value, 12, SOFT, false, 12);
    }

    private Button makeButton(String label, boolean primary, Runnable action) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(14);
        b.setAllCaps(false);
        b.setSingleLine(true);
        b.setTextColor(primary ? BG : INK);
        b.setPadding(dp(13), 0, dp(13), 0);
        b.setBackground(shape(primary ? TEAL : PANEL_BRIGHT, 12, !primary));
        b.setOnClickListener(v -> action.run());
        b.setFocusable(true);
        if (primary && defaultButton == null) defaultButton = b;
        return b;
    }

    private void action(String label, boolean primary, Runnable run) {
        Button b = makeButton(label, primary, run);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, dp(51));
        params.bottomMargin = dp(9);
        content.addView(b, params);
    }

    private void actionsHorizontal(String[] labels, Runnable[] handlers) {
        LinearLayout band = row();
        LinearLayout.LayoutParams bandParams =
                new LinearLayout.LayoutParams(-1, -2);
        bandParams.bottomMargin = dp(12);
        content.addView(band, bandParams);
        for (int i = 0; i < labels.length; i++) {
            Button b = makeButton(labels[i], i == 0, handlers[i]);
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                    0, dp(52), 1);
            params.rightMargin = i + 1 < labels.length ? dp(9) : 0;
            band.addView(b, params);
        }
    }

    private void sectionTitle(String kicker, String heading) {
        addText(content, kicker, 12, TEAL, true, 5);
        addText(content, heading, wide ? 24 : 21, INK, true, 13);
    }

    private void render(int destination) {
        page = destination;
        defaultButton = null;
        Configuration configuration = getResources().getConfiguration();
        wide = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE
                && configuration.screenWidthDp >= 600;

        LinearLayout root = wide ? row() : column();
        root.setGravity(Gravity.TOP);
        root.setBackgroundColor(BG);
        root.setPadding(dp(12), dp(10), dp(12), dp(10));
        setContentView(root);

        LinearLayout stage = column();
        if (wide) {
            LinearLayout rail = column();
            rail.setPadding(dp(14), dp(17), dp(14), dp(12));
            rail.setBackground(shape(RAIL, 18, true));
            root.addView(rail, new LinearLayout.LayoutParams(dp(208), -1));
            buildRail(rail);
            LinearLayout.LayoutParams stageParams = new LinearLayout.LayoutParams(
                    0, -1, 1);
            stageParams.leftMargin = dp(14);
            root.addView(stage, stageParams);
        } else {
            root.addView(stage, new LinearLayout.LayoutParams(-1, -1));
            buildPortraitHeader(stage);
        }

        LinearLayout top = row();
        stage.addView(top, new LinearLayout.LayoutParams(-1, dp(wide ? 49 : 44)));
        LinearLayout topTitle = column();
        top.addView(topTitle, new LinearLayout.LayoutParams(0, -2, 1));
        addText(topTitle, "CHAPTER 00  /  OFFLINE PREVIEW 0.2", 10, TEAL, true, 2);
        addText(topTitle, TABS[page] + "  ·  試作遊戲", wide ? 19 : 17, INK, true, 0);
        TextView wallet = text("✦ " + get("iris", 1000), 14, GOLD, true);
        wallet.setPadding(dp(12), dp(7), dp(12), dp(7));
        wallet.setBackground(shape(RAIL, 14, true));
        top.addView(wallet);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(false);
        scroll.setVerticalScrollBarEnabled(false);
        stage.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        content = column();
        content.setPadding(0, dp(7), dp(3), dp(12));
        scroll.addView(content);

        switch (page) {
            case 0: showHome(); break;
            case 1: showStory(); break;
            case 2: showBattle(); break;
            case 3: showGacha(); break;
            default: showSave(); break;
        }

        TextView footer = text(notice, 12, SOFT, false);
        footer.setBackground(shape(RAIL, 10, false));
        footer.setPadding(dp(11), dp(8), dp(11), dp(8));
        stage.addView(footer, new LinearLayout.LayoutParams(-1, -2));
        if (wide) {
            // Touch remains unrestricted; gamepad DPAD focuses the selected tab.
            // No forced focus, so the primary story/button never steals taps.
        }
    }

    private void buildRail(LinearLayout rail) {
        addText(rail, "✦ DANMEMORE", 17, GOLD, true, 4);
        addText(rail, "迷宮記憶  /  PREVIEW", 10, SOFT, true, 15);
        View line = new View(this);
        line.setBackgroundColor(BORDER);
        rail.addView(line, new LinearLayout.LayoutParams(-1, dp(1)));
        gap(rail, 14);

        for (int i = 0; i < TABS.length; i++) {
            final int target = i;
            boolean selected = page == i;
            Button b = makeButton(String.format(Locale.ROOT, "%02d   %s", i + 1, TABS[i]),
                    selected, () -> open(target));
            b.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                    -1, dp(49));
            params.bottomMargin = dp(8);
            rail.addView(b, params);
        }
        // Navigation highlight is not the primary in-page controller action.
        defaultButton = null;

        rail.addView(new View(this), new LinearLayout.LayoutParams(1, 0, 1));
        addText(rail, "L1 / R1  切換頁面", 11, SOFT, false, 4);
        addText(rail, "A  確認    B  返回", 11, SOFT, false, 8);
        addText(rail, "完全離線 · 原創測試", 10, TEAL, false, 0);
    }

    private void buildPortraitHeader(LinearLayout stage) {
        addText(stage, "✦ DANMEMORE  /  OFFLINE PREVIEW", 13, GOLD, true, 4);
        addText(stage, "迷宮記憶 · 測試版 0.2", 23, INK, true, 4);
        HorizontalScrollView scroller = new HorizontalScrollView(this);
        scroller.setHorizontalScrollBarEnabled(false);
        LinearLayout strip = row();
        strip.setPadding(0, dp(5), 0, dp(8));
        scroller.addView(strip);
        for (int i = 0; i < TABS.length; i++) {
            final int target = i;
            Button b = makeButton(TABS[i], i == page, () -> open(target));
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                    dp(78), dp(43));
            params.rightMargin = dp(6);
            strip.addView(b, params);
        }
        stage.addView(scroller);
        defaultButton = null;
    }

    private void open(int next) {
        render(Math.max(0, Math.min(4, next)));
    }

    private void showHome() {
        sectionTitle("THE LOST ENTRY", "歡迎回到迷宮的入口");

        LinearLayout hero = column();
        hero.setPadding(dp(14), dp(13), dp(14), dp(13));
        hero.setBackground(heroShape());
        LinearLayout.LayoutParams margins = new LinearLayout.LayoutParams(-1, -2);
        margins.bottomMargin = dp(14);
        content.addView(hero, margins);
        PortalView art = new PortalView(this);
        hero.addView(art, new LinearLayout.LayoutParams(-1, dp(wide ? 172 : 142)));
        gap(hero, 12);
        addText(hero, "『即使記憶消散，故事仍能重新開始。』", 17, INK, true, 6);
        addText(hero, "完全離線的互動原型：四節原創短篇、訓練戰鬥、模擬召喚。",
                13, SOFT, false, 0);

        LinearLayout summary = row();
        LinearLayout.LayoutParams statsParams = new LinearLayout.LayoutParams(-1, -2);
        statsParams.bottomMargin = dp(14);
        content.addView(summary, statsParams);
        metric(summary, "閱讀進度", (get("chapter", 0) + 1) + " / 4", true);
        metric(summary, "勝利場次", String.valueOf(get("wins", 0)), false);
        metric(summary, "模擬召喚", String.valueOf(get("draws", 0)), false);

        if (wide) {
            actionsHorizontal(new String[]{"繼續閱讀", "進入訓練場", "進行召喚"},
                    new Runnable[]{() -> open(1), () -> open(2), () -> open(3)});
        } else {
            action("繼續閱讀劇情", true, () -> open(1));
            action("進入戰鬥", false, () -> open(2));
            action("前往抽卡", false, () -> open(3));
        }
        note("這不是已復原的原版 Memoria Freese；原版劇情、角色素材與完整戰鬥系統尚未接入。");
    }

    private void metric(LinearLayout parent, String title, String value, boolean left) {
        LinearLayout pane = column();
        pane.setPadding(dp(11), dp(11), dp(9), dp(11));
        pane.setBackground(shape(PANEL, 12, true));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, -2, 1);
        params.rightMargin = dp(left ? 8 : 7);
        parent.addView(pane, params);
        addText(pane, title, 11, SOFT, false, 4);
        addText(pane, value, wide ? 19 : 16, GOLD, true, 0);
    }

    private void showStory() {
        int chapter = Math.max(0, Math.min(SCENES.length - 1, get("chapter", 0)));
        sectionTitle("ORIGINAL TEST STORY", "第一章  ·  星紋的邀請");
        LinearLayout panel = panel();
        addText(panel, String.format(Locale.ROOT, "EPISODE  %02d  /  04", chapter + 1),
                12, TEAL, true, 13);
        addText(panel, "第 " + (chapter + 1) + " 節", 20, GOLD, true, 14);
        addText(panel, SCENES[chapter], wide ? 19 : 17, INK, false, 26);
        addText(panel, "●  原創測試敘事  ·  進度自動儲存", 11, SOFT, false, 0);
        ProgressBar progress = progress(TEAL, (chapter + 1) * 25);
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(
                -1, dp(8));
        progressParams.bottomMargin = dp(17);
        content.addView(progress, progressParams);

        if (chapter < SCENES.length - 1) {
            if (wide) {
                actionsHorizontal(new String[]{"閱讀下一節", "上一節"},
                    new Runnable[]{() -> advanceStory(chapter), () -> previousStory(chapter)});
            } else {
                action("閱讀下一節", true, () -> advanceStory(chapter));
                action("上一節", false, () -> previousStory(chapter));
            }
        } else {
            action("完成本篇並領取測試晶石", true, this::completeStory);
            action("上一節", false, () -> previousStory(chapter));
        }
        note("目前僅使用獨立編寫的短篇測試文字，並非原版遊戲劇情。");
    }

    private void advanceStory(int chapter) {
        put("chapter", Math.min(3, chapter + 1));
        notice = "已儲存劇情進度。";
        render(1);
    }

    private void previousStory(int chapter) {
        put("chapter", Math.max(0, chapter - 1));
        notice = "已移至上一節。";
        render(1);
    }

    private void completeStory() {
        if (!prefs.getBoolean("storyRewarded", false)) {
            prefs.edit().putBoolean("storyRewarded", true)
                    .putInt("iris", get("iris", 1000) + 50).apply();
            notice = "原創測試篇章完成！首次獎勵 50 測試晶石。";
        } else {
            notice = "本篇已完成，首次獎勵不會重複發放。";
        }
        render(1);
    }

    private ProgressBar progress(int color, int percentage) {
        ProgressBar bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        bar.setMax(100);
        bar.setProgress(Math.max(0, Math.min(100, percentage)));
        bar.setProgressTintList(ColorStateList.valueOf(color));
        bar.setProgressBackgroundTintList(ColorStateList.valueOf(BORDER));
        return bar;
    }

    private void healthLine(LinearLayout parent, String label, int current,
                            int total, int color) {
        LinearLayout line = row();
        TextView name = text(label, 14, INK, true);
        line.addView(name, new LinearLayout.LayoutParams(0, -2, 1));
        TextView hp = text(current + " / " + total, 14, color, true);
        line.addView(hp);
        parent.addView(line);
        gap(parent, 5);
        ProgressBar bar = progress(color, (current * 100) / total);
        LinearLayout.LayoutParams lineParams = new LinearLayout.LayoutParams(-1, dp(8));
        lineParams.bottomMargin = dp(15);
        parent.addView(bar, lineParams);
    }

    private void startBattle() {
        prefs.edit()
                .putInt("hp", 100).putInt("enemyHp", 85)
                .putInt("heals", 2).putBoolean("battleActive", true)
                .putString("battleLog", "你踏入訓練場。守衛獸正在觀察你。")
                .apply();
        notice = "新一場訓練戰鬥開始。";
        render(2);
    }

    private void showBattle() {
        sectionTitle("TACTICAL TRAINING", "訓練場  ·  守衛獸");
        boolean active = prefs.getBoolean("battleActive", false);
        LinearLayout gauges = panel();
        healthLine(gauges, "冒險者", get("hp", 100), 100, TEAL);
        healthLine(gauges, "守衛獸", get("enemyHp", 85), 85, RED);
        addText(gauges, "剩餘治療藥劑   " + get("heals", 2)
                + " / 2", 13, SOFT, false, 0);

        LinearLayout logPanel = panel();
        addText(logPanel, "戰鬥紀錄  /  BATTLE LOG", 12, GOLD, true, 8);
        addText(logPanel,
                prefs.getString("battleLog", "尚未進入訓練場。"),
                15, INK, false, 0);

        if (!active) {
            action("開始新戰鬥", true, this::startBattle);
        } else if (wide) {
            actionsHorizontal(new String[]{"攻擊", "防禦", "治療 +30"},
                    new Runnable[]{
                        () -> fight("attack"),
                        () -> fight("guard"),
                        () -> fight("heal")
                    });
            action("結束本場戰鬥", false, this::stopBattle);
        } else {
            action("普通攻擊", true, () -> fight("attack"));
            action("防禦", false, () -> fight("guard"));
            action("治療 +30", false, () -> fight("heal"));
            action("結束本場戰鬥", false, this::stopBattle);
        }
        note("技能、敵人、數值、勝負判定皆為原創測試規則，不等於原版戰鬥。");
    }

    private void stopBattle() {
        prefs.edit().putBoolean("battleActive", false)
                .putString("battleLog", "你已離開訓練場。").apply();
        notice = "已結束本場戰鬥。";
        render(2);
    }

    private void fight(String move) {
        int heroHp = get("hp", 100);
        int enemyHp = get("enemyHp", 85);
        int heals = get("heals", 2);
        boolean guarded = "guard".equals(move);
        String message;

        if ("attack".equals(move)) {
            int dealt = 16 + rng.nextInt(11);
            enemyHp = Math.max(0, enemyHp - dealt);
            message = "你的攻擊造成 " + dealt + " 點傷害。";
        } else if ("heal".equals(move)) {
            if (heals == 0) {
                notice = "治療藥劑已用完。";
                render(2);
                return;
            }
            heals--;
            int restored = Math.min(30, 100 - heroHp);
            heroHp += restored;
            message = "使用藥劑，恢復 " + restored + " 點生命。";
        } else {
            message = "你架起防禦姿態，準備迎接攻擊。";
        }

        SharedPreferences.Editor editor = prefs.edit();
        if (enemyHp == 0) {
            editor.putBoolean("battleActive", false)
                    .putInt("iris", get("iris", 1000) + 80)
                    .putInt("wins", get("wins", 0) + 1);
            message += "\n★ 勝利！獲得 80 測試晶石。";
        } else {
            int received = guarded ? 2 + rng.nextInt(5) :
                    9 + rng.nextInt(11);
            heroHp = Math.max(0, heroHp - received);
            message += "\n守衛獸反擊，造成 " + received + " 點傷害。";
            if (heroHp == 0) {
                editor.putBoolean("battleActive", false);
                message += "\n戰鬥失敗。可以重新挑戰。";
            }
        }
        editor.putInt("hp", heroHp).putInt("enemyHp", enemyHp)
                .putInt("heals", heals)
                .putString("battleLog", message).apply();
        notice = "本回合已完成並自動儲存。";
        render(2);
    }

    private void showGacha() {
        sectionTitle("MEMORY SUMMON", "星紋召喚  ·  模擬卡池");
        LinearLayout summon = column();
        summon.setPadding(dp(20), dp(17), dp(20), dp(17));
        summon.setBackground(heroShape());
        LinearLayout.LayoutParams margins = new LinearLayout.LayoutParams(-1, -2);
        margins.bottomMargin = dp(13);
        content.addView(summon, margins);
        addText(summon, "✦  THE ASTRAL ARCHIVE", 12, TEAL, true, 8);
        addText(summon, "星辰不會忘記旅人的名字。", wide ? 23 : 19,
                INK, true, 10);
        addText(summon, "5★  5%   ·   4★  19%   ·   3★  76%\n"
                + "單抽 100 晶石  /  十連 1,000 晶石",
                13, SOFT, false, 0);

        if (wide) {
            actionsHorizontal(new String[]{"召喚 1 次", "召喚 10 次", "調整晶石"},
                    new Runnable[]{() -> draw(1), () -> draw(10), this::changeIris});
        } else {
            action("單抽 · 100", true, () -> draw(1));
            action("十連 · 1,000", false, () -> draw(10));
            action("調整測試晶石", false, this::changeIris);
        }
        card("最新召喚結果  ·  " + get("draws", 0) + " 抽",
                prefs.getString("lastDraw", "尚未召喚。\n選擇單抽或十連即可看到結果。"));
        note("抽卡名稱及機率均為原創測試資料；僅使用虛擬晶石，沒有任何交易。");
    }

    private void draw(int count) {
        int iris = get("iris", 1000);
        int cost = count * 100;
        if (iris < cost) {
            notice = "晶石不足，請先調整測試晶石數量。";
            render(3);
            return;
        }
        int[] increments = new int[HEROES.length];
        StringBuilder result = new StringBuilder();
        for (int n = 0; n < count; n++) {
            int roll = rng.nextInt(100);
            int index = roll < 5 ? 4 : roll < 24 ? 3 : rng.nextInt(3);
            int rarity = index == 4 ? 5 : index == 3 ? 4 : 3;
            increments[index]++;
            if (n > 0) result.append('\n');
            result.append(rarity == 5 ? "✦✦ " : rarity == 4 ? "✦ " : "· ")
                    .append(rarity).append("★ ")
                    .append(HEROES[index]);
        }
        SharedPreferences.Editor editor = prefs.edit()
                .putInt("iris", iris - cost)
                .putInt("draws", get("draws", 0) + count)
                .putString("lastDraw", result.toString());
        for (int i = 0; i < increments.length; i++) {
            if (increments[i] != 0) {
                editor.putInt("hero_" + i, get("hero_" + i, 0) + increments[i]);
            }
        }
        editor.apply();
        notice = count + " 次模擬召喚完成；結果和角色數量已存檔。";
        render(3);
    }

    private void changeIris() {
        final String[] options = {"增加 1,000", "直接設為 10,000",
                "自訂數量（0～1億）", "設為 0"};
        new AlertDialog.Builder(this).setTitle("調整模擬晶石")
                .setItems(options, (dialog, selected) -> {
                    if (selected == 2) {
                        editCustomIris();
                        return;
                    }
                    int amount = selected == 0 ?
                            (int)Math.min(100000000L, (long)get("iris", 1000) + 1000L)
                            : selected == 1 ? 10000 : 0;
                    put("iris", amount);
                    notice = "測試晶石已更新為 " + amount + "。";
                    render(3);
                }).setNegativeButton("取消", null).show();
    }

    private void editCustomIris() {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_NUMBER);
        input.setSingleLine(true);
        input.setText(String.valueOf(get("iris", 1000)));
        input.setSelectAllOnFocus(true);
        input.setPadding(dp(19), dp(12), dp(19), dp(12));
        new AlertDialog.Builder(this)
                .setTitle("設定測試晶石 · 0 至 100,000,000")
                .setView(input)
                .setPositiveButton("保存", (dialog, which) -> {
                    try {
                        long amount = Long.parseLong(input.getText().toString().trim());
                        if (amount < 0 || amount > 100000000L) {
                            notice = "輸入超出範圍：請填入 0 至 1 億。";
                        } else {
                            put("iris", (int)amount);
                            notice = "自訂晶石數量已儲存。";
                        }
                    } catch (NumberFormatException invalid) {
                        notice = "晶石數量無效，請輸入整數。";
                    }
                    render(3);
                })
                .setNegativeButton("取消", null).show();
    }

    private void showSave() {
        sectionTitle("LOCAL SAVE FILE", "冒險者紀錄");
        card("本機進度",
                "劇情  " + (get("chapter", 0) + 1) + " / 4" +
                "\n戰鬥勝場  " + get("wins", 0) +
                "\n模擬召喚  " + get("draws", 0) + " 次" +
                "\n測試晶石  " + get("iris", 1000));

        LinearLayout pane = panel();
        addText(pane, "冒險者收藏  /  COLLECTION", 17, GOLD, true, 10);
        boolean hasHeroes = false;
        for (int i = 0; i < HEROES.length; i++) {
            int amount = get("hero_" + i, 0);
            if (amount == 0) continue;
            hasHeroes = true;
            String star = i == 4 ? "5★" : i == 3 ? "4★" : "3★";
            addText(pane, star + "  " + HEROES[i] + "     × " + amount +
                    "\n       " + ROLES[i], 14, INK, false, 9);
        }
        if (!hasHeroes) {
            addText(pane, "目前尚無角色。試試模擬召喚，看看會出現誰。",
                    14, SOFT, false, 0);
        }
        if (wide) {
            actionsHorizontal(new String[]{"返回首頁", "清除本版測試存檔"},
                    new Runnable[]{() -> open(0), this::confirmReset});
        } else {
            action("返回首頁", true, () -> open(0));
            action("清除本版測試存檔", false, this::confirmReset);
        }
        note("存檔只儲存在本機的 0.2 測試 App 中；舊版 0.1 和原版遊戲不受影響。");
    }

    private void confirmReset() {
        new AlertDialog.Builder(this)
                .setTitle("清除 0.2 版測試存檔？")
                .setMessage("此操作只重設目前這個離線測試版。"
                        + "\n原版遊戲及舊 0.1 測試版都不會受到影響。")
                .setPositiveButton("確認清除", (dialog, which) -> {
                    prefs.edit().clear().apply();
                    notice = "本版測試存檔已清除，晶石回到 1,000。";
                    render(4);
                })
                .setNegativeButton("取消", null)
                .show();
    }

    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN && event.getRepeatCount() == 0) {
            int key = event.getKeyCode();
            if (key == KeyEvent.KEYCODE_BUTTON_L1) {
                open((page + 4) % 5);
                return true;
            }
            if (key == KeyEvent.KEYCODE_BUTTON_R1) {
                open((page + 1) % 5);
                return true;
            }
            if (key == KeyEvent.KEYCODE_BUTTON_B) {
                boolean shouldNavigate = page != 0;
                if (shouldNavigate) open(0);
                return shouldNavigate;
            }
            if (key == KeyEvent.KEYCODE_BUTTON_A) {
                View focused = getCurrentFocus();
                if (focused instanceof Button) {
                    focused.performClick();
                    return true;
                }
                if (defaultButton != null) {
                    defaultButton.performClick();
                    return true;
                }
            }
        }
        return super.dispatchKeyEvent(event);
    }

    @Override public void onBackPressed() {
        if (page != 0) open(0);
        else super.onBackPressed();
    }
}
