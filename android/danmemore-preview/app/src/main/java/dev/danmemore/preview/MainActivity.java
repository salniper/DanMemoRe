package dev.danmemore.preview;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.security.SecureRandom;

/**
 * Independently playable OFFLINE PROTOTYPE, not the recovered Memoria Freese.
 * All plot text, characters, battle values and gacha probabilities here are
 * newly authored stand-ins. It never imports or contacts the retired game.
 */
public final class MainActivity extends Activity {
    private static final int BG = Color.rgb(9, 17, 29);
    private static final int PANEL = Color.rgb(22, 36, 51);
    private static final int INK = Color.rgb(239, 243, 247);
    private static final int SOFT = Color.rgb(169, 190, 204);
    private static final int GOLD = Color.rgb(239, 196, 123);
    private static final int TEAL = Color.rgb(99, 219, 190);
    private static final String[] SCENES = {
        "一封沒有署名的委託，出現在安靜的冒險者公會。",
        "你走進迷宮入口，牆面上的火把照亮了陌生的足跡。",
        "轉角傳來聲響。一隻守衛獸擋住通往下一層的階梯。",
        "擊退守衛獸後，你拾起刻著星紋的石片。冒險，才剛開始。"
    };
    private static final String[] HEROES = {
        "見習劍士", "風之術師", "遺跡射手", "迷宮守護者", "星紋旅者"
    };
    private final SecureRandom random = new SecureRandom();
    private SharedPreferences save;
    private LinearLayout body;
    private int screen = 0;
    private String notice = "測試版已就緒，所有操作均在本機完成。";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        save = getSharedPreferences("danmemore-preview-v1", MODE_PRIVATE);
        render(0);
    }

    private int get(String key, int fallback) { return save.getInt(key, fallback); }
    private void put(String key, int value) { save.edit().putInt(key, value).apply(); }
    private int dp(int n) { return (int) (getResources().getDisplayMetrics().density * n + 0.5f); }

    private GradientDrawable background(int color, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        return shape;
    }

    private TextView text(String value, int size, int color, boolean bold) {
        TextView label = new TextView(this);
        label.setText(value);
        label.setTextColor(color);
        label.setTextSize(size);
        if (bold) label.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        label.setLineSpacing(dp(3), 1f);
        return label;
    }

    private void card(String title, String description) {
        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setPadding(dp(18), dp(16), dp(18), dp(16));
        container.setBackground(background(PANEL, 16));
        LinearLayout.LayoutParams params =
            new LinearLayout.LayoutParams(-1, -2);
        params.setMargins(0, 0, 0, dp(12));
        body.addView(container, params);
        TextView headline = text(title, 18, GOLD, true);
        container.addView(headline);
        TextView copy = text(description, 15, INK, false);
        LinearLayout.LayoutParams gap = new LinearLayout.LayoutParams(-1, -2);
        gap.topMargin = dp(8);
        container.addView(copy, gap);
    }

    private void subtitle(String value) {
        TextView label = text(value, 14, SOFT, false);
        LinearLayout.LayoutParams gap = new LinearLayout.LayoutParams(-1, -2);
        gap.setMargins(0, 0, 0, dp(12));
        body.addView(label, gap);
    }

    private Button button(String value, boolean primary, Runnable onClick) {
        Button btn = new Button(this);
        btn.setText(value);
        btn.setAllCaps(false);
        btn.setTextSize(15);
        btn.setTextColor(primary ? BG : INK);
        btn.setBackgroundTintList(ColorStateList.valueOf(
            primary ? TEAL : Color.rgb(48, 67, 82)));
        btn.setOnClickListener(v -> onClick.run());
        return btn;
    }

    private void action(String label, boolean primary, Runnable onClick) {
        Button b = button(label, primary, onClick);
        LinearLayout.LayoutParams margin = new LinearLayout.LayoutParams(-1, dp(54));
        margin.bottomMargin = dp(10);
        body.addView(b, margin);
    }

    private void render(int next) {
        screen = next;
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(14), dp(16), 0);
        root.setBackgroundColor(BG);
        setContentView(root);

        TextView logo = text("DANMEMORE  /  OFFLINE PREVIEW", 12, TEAL, true);
        root.addView(logo);
        TextView heading = text("迷宮記憶 · 離線測試", 26, INK, true);
        LinearLayout.LayoutParams titleGap = new LinearLayout.LayoutParams(-1, -2);
        titleGap.setMargins(0, dp(4), 0, dp(4));
        root.addView(heading, titleGap);
        TextView warning = text("獨立原創測試內容｜非原版遊戲｜不需網路", 12, GOLD, false);
        root.addView(warning);

        HorizontalScrollView navScroll = new HorizontalScrollView(this);
        navScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout nav = new LinearLayout(this);
        nav.setPadding(0, dp(10), 0, dp(8));
        navScroll.addView(nav);
        String[] titles = {"首頁", "劇情", "戰鬥", "抽卡", "存檔"};
        for (int i = 0; i < titles.length; i++) {
            final int page = i;
            Button b = button(titles[i], i == screen, () -> open(page));
            LinearLayout.LayoutParams margin = new LinearLayout.LayoutParams(dp(79), dp(46));
            margin.rightMargin = dp(5);
            nav.addView(b, margin);
        }
        root.addView(navScroll);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(false);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(0, dp(8), 0, dp(20));
        scroll.addView(body);

        if (screen == 0) showHome();
        else if (screen == 1) showStory();
        else if (screen == 2) showBattle();
        else if (screen == 3) showGacha();
        else showSave();

        TextView status = text(notice, 12, SOFT, false);
        status.setPadding(dp(3), dp(9), dp(3), dp(10));
        root.addView(status);
    }

    private void open(int page) {
        if (page == 2 && !save.getBoolean("battleActive", false)) startBattle();
        else render(page);
    }

    private void showHome() {
        card("回到迷宮的入口",
            "這是一個可以安裝在 Android／AYN Thor 的獨立離線操作測試。"
            + "\n\n目前包含原創短篇劇情、可操作的回合戰鬥、模擬抽卡，以及重新啟動後仍保留的本機存檔。");
        card("目前持有", "測試晶石  " + get("iris", 1000) +
            "\n已進行抽卡  " + get("draws", 0) +
            "\n劇情進度  " + (get("chapter", 0) + 1) + " / " + SCENES.length);
        action("進入劇情", true, () -> open(1));
        action("開始戰鬥", false, () -> open(2));
        action("前往抽卡", false, () -> open(3));
        subtitle("本 APK 不含、也不會載入原版 Memoria Freese 遊戲素材或伺服器資料；原版劇情、技能、戰鬥、抽卡機率都尚未還原。");
    }

    private void showStory() {
        int chapter = Math.max(0, Math.min(SCENES.length - 1, get("chapter", 0)));
        card("劇情 / 第 " + (chapter + 1) + " 節", SCENES[chapter]);
        if (chapter < SCENES.length - 1) {
            action("繼續閱讀", true, () -> {
                put("chapter", chapter + 1);
                notice = "已自動儲存劇情進度。";
                render(1);
            });
        } else {
            action("完成測試篇章", true, () -> {
                if (!save.getBoolean("storyRewarded", false)) {
                    save.edit().putBoolean("storyRewarded", true)
                        .putInt("iris", get("iris", 1000) + 50).apply();
                    notice = "第一次完成篇章：獲得 50 測試晶石！";
                } else {
                    notice = "已完成測試篇章，獎勵不會重複發放。";
                }
                render(1);
            });
        }
        action("重讀第一節", false, () -> {
            put("chapter", 0);
            notice = "已重設閱讀位置，首次獎勵紀錄保留。";
            render(1);
        });
        subtitle("此段為原創的測試腳本，不是原版遊戲劇情。");
    }

    private void startBattle() {
        save.edit()
            .putInt("hp", 100).putInt("enemyHp", 85)
            .putInt("heals", 2).putBoolean("battleActive", true)
            .apply();
        notice = "測試戰鬥開始！";
        render(2);
    }

    private void showBattle() {
        boolean active = save.getBoolean("battleActive", false);
        int hp = get("hp", 100);
        int enemyHp = get("enemyHp", 85);
        card("訓練場 · 回合戰鬥",
            "你的生命：" + hp + " / 100\n守衛獸生命：" + enemyHp +
            " / 85\n剩餘治療：" + get("heals", 2));
        if (!active) {
            subtitle("上一場戰鬥已結束，隨時可以重新挑戰。");
            action("重新開始戰鬥", true, this::startBattle);
            return;
        }
        action("普通攻擊", true, () -> fight("attack"));
        action("防禦", false, () -> fight("guard"));
        action("治療 +30", false, () -> fight("heal"));
        action("退出本場戰鬥", false, () -> {
            save.edit().putBoolean("battleActive", false).apply();
            notice = "已離開測試戰鬥。";
            render(2);
        });
        subtitle("戰鬥數值與敵人均為獨立測試規則，非原版演算。");
    }

    private void fight(String move) {
        int hp = get("hp", 100);
        int enemyHp = get("enemyHp", 85);
        int heals = get("heals", 2);
        boolean guarded = move.equals("guard");
        if (move.equals("attack")) {
            int dealt = 16 + random.nextInt(11);
            enemyHp = Math.max(0, enemyHp - dealt);
            notice = "你造成 " + dealt + " 點傷害。";
        } else if (move.equals("heal")) {
            if (heals == 0) {
                notice = "治療次數已用完。";
                render(2);
                return;
            }
            heals--;
            hp = Math.min(100, hp + 30);
            notice = "你恢復了 30 點生命（最多 100）。";
        } else {
            notice = "你採取防禦姿態。";
        }
        if (enemyHp == 0) {
            int rewards = 80;
            save.edit().putInt("hp", hp).putInt("enemyHp", 0)
                .putInt("heals", heals).putBoolean("battleActive", false)
                .putInt("iris", get("iris", 1000) + rewards)
                .putInt("wins", get("wins", 0) + 1).apply();
            notice += " 戰鬥勝利！獲得 " + rewards + " 測試晶石。";
        } else {
            int received = guarded ? (2 + random.nextInt(5)) :
                (9 + random.nextInt(11));
            hp = Math.max(0, hp - received);
            save.edit().putInt("hp", hp).putInt("enemyHp", enemyHp)
                .putInt("heals", heals).putBoolean("battleActive", hp > 0).apply();
            notice += " 守衛獸反擊 " + received + " 點。";
            if (hp == 0) notice += " 戰鬥失敗，可重新挑戰。";
        }
        render(2);
    }

    private void showGacha() {
        card("記憶召喚 · 模擬抽卡",
            "測試晶石：" + get("iris", 1000) +
            "\n累計抽卡：" + get("draws", 0) +
            "\n單抽消耗：100 測試晶石" +
            "\n此處抽卡不涉及任何真實貨幣或連線交易。");
        String recent = save.getString("lastDraw", "尚未進行召喚");
        card("最近一次召喚", recent);
        action("抽取 1 次（100）", true, () -> draw(1));
        action("抽取 10 次（1000）", false, () -> draw(10));
        action("調整測試晶石數量", false, this::changeIris);
        subtitle("所有角色為測試用原創名稱，機率是暫定規則，不代表原版卡池。");
    }

    private void draw(int count) {
        int price = 100 * count, iris = get("iris", 1000);
        if (iris < price) {
            notice = "測試晶石不足，請使用下方按鈕自行調整。";
            render(3);
            return;
        }
        StringBuilder listing = new StringBuilder();
        SharedPreferences.Editor editor = save.edit()
            .putInt("iris", iris - price)
            .putInt("draws", get("draws", 0) + count);
        for (int n = 0; n < count; n++) {
            int roll = random.nextInt(100);
            int idx = roll < 5 ? 4 : roll < 24 ? 3 : random.nextInt(3);
            int rarity = idx == 4 ? 5 : idx == 3 ? 4 : 3;
            String key = "hero_" + idx;
            int amount = get(key, 0) + 1;
            // Multiple copies in the same batch are counted below by
            // tracking the in-batch increment independently.
            for (int prior = 0; prior < n; prior++) {
                // No-op: counts are maintained by local batch array below.
            }
            listing.append(rarity).append("★ ").append(HEROES[idx]).append('\n');
        }
        // Recount the exact revealed batch rather than re-rolling it.
        String[] lines = listing.toString().split("\n");
        for (int i = 0; i < HEROES.length; i++) {
            int delta = 0;
            for (String line : lines) if (line.endsWith(HEROES[i])) delta++;
            if (delta > 0) editor.putInt("hero_" + i, get("hero_" + i, 0) + delta);
        }
        editor.putString("lastDraw", listing.toString().trim()).apply();
        notice = "離線模擬召喚完成 " + count + " 次，抽卡結果已儲存。";
        render(3);
    }

    private void changeIris() {
        final String[] options = {
            "增加 100", "增加 1,000", "直接設為 10,000", "設為 0"
        };
        new AlertDialog.Builder(this)
            .setTitle("調整測試晶石（無上限，可自行設定）")
            .setItems(options, (dialog, which) -> {
                int current = get("iris", 1000);
                int amount = which == 0 ? Math.min(100000000, current + 100)
                    : which == 1 ? Math.min(100000000, current + 1000)
                    : which == 2 ? 10000 : 0;
                put("iris", amount);
                notice = "測試晶石已改為 " + amount + "，並儲存於本機。";
                render(3);
            }).setNegativeButton("取消", null).show();
    }

    private void showSave() {
        StringBuilder owned = new StringBuilder();
        for (int i = 0; i < HEROES.length; i++) {
            int copies = get("hero_" + i, 0);
            if (copies > 0) owned.append(HEROES[i]).append(" × ")
                .append(copies).append('\n');
        }
        card("本機存檔狀態",
            "劇情位置：" + (get("chapter", 0) + 1) + " / " + SCENES.length +
            "\n戰鬥勝場：" + get("wins", 0) +
            "\n抽卡次數：" + get("draws", 0) +
            "\n測試晶石：" + get("iris", 1000));
        card("已抽得的角色", owned.length() == 0 ?
            "目前尚無紀錄，先試試看模擬抽卡。" : owned.toString().trim());
        action("返回首頁", true, () -> open(0));
        action("清除測試存檔", false, () ->
            new AlertDialog.Builder(this)
                .setTitle("確定清除本機測試紀錄？")
                .setMessage("會重置劇情、戰鬥、抽卡與測試晶石。原版遊戲資料不會受到影響。")
                .setPositiveButton("確認清除", (dialog, which) -> {
                    save.edit().clear().apply();
                    notice = "測試存檔已清除，初始晶石恢復為 1,000。";
                    render(4);
                })
                .setNegativeButton("取消", null).show()
        );
        subtitle("使用 Android SharedPreferences 保存在本機。不需帳號、不上傳存檔、不讀取原版遊戲資料。");
    }

    @Override public void onBackPressed() {
        if (screen != 0) render(0);
        else super.onBackPressed();
    }
}
