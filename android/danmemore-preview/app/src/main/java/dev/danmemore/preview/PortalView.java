package dev.danmemore.preview;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.view.View;

/**
 * Original, procedural title illustration.
 * No archived game artwork or external image/font asset is used.
 */
public final class PortalView extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);

    public PortalView(Context context) {
        super(context);
        setContentDescription("夜色迷宮山巒、金色光環與遠方門扉的原創背景");
        setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
    }

    private void color(int color) {
        paint.reset();
        paint.setAntiAlias(true);
        paint.setColor(color);
        paint.setStyle(Paint.Style.FILL);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int save = canvas.save();
        canvas.scale(getWidth() / 960f, getHeight() / 370f);

        color(Color.rgb(10, 23, 38));
        paint.setShader(new LinearGradient(0, 0, 0, 370,
                Color.rgb(9, 31, 51), Color.rgb(4, 12, 23),
                Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, 960, 370, paint);
        paint.setShader(null);

        for (int i = 0; i < 58; i++) {
            int x = (i * 241 + 67) % 960;
            int y = (i * 137 + 31) % 205;
            color(Color.argb(i % 4 == 0 ? 165 : 70, 175, 222, 236));
            canvas.drawCircle(x, y, i % 8 == 0 ? 1.8f : 0.7f, paint);
        }

        color(Color.WHITE);
        paint.setShader(new RadialGradient(690, 180, 210,
                new int[]{Color.argb(70, 63, 222, 212),
                        Color.argb(24, 46, 112, 160), Color.TRANSPARENT},
                null, Shader.TileMode.CLAMP));
        canvas.drawCircle(690, 180, 210, paint);
        paint.setShader(null);

        mountain(canvas, 0xff122b39, 0,
                285, 160, 325, 340, 220, 520, 321, 720, 215, 960, 312);
        mountain(canvas, 0xff0a192b, 0,
                348, 105, 307, 228, 351, 340, 277, 505, 335, 690, 270, 960, 354);

        color(0xff143c49);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(15);
        canvas.drawCircle(686, 181, 104, paint);
        color(0xffd7b376);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(3.5f);
        canvas.drawCircle(686, 181, 105, paint);
        paint.setStrokeWidth(1.5f);
        paint.setColor(0x99dfc386);
        canvas.drawCircle(686, 181, 120, paint);
        paint.setColor(0x55dfc386);
        canvas.drawArc(554, 49, 818, 313, 205, 119, false, paint);

        color(0xffc3ecda);
        paint.setShader(new RadialGradient(685, 178, 79,
                new int[]{0xe6a5e5d9, 0x9446a9a7, 0x00226666},
                null, Shader.TileMode.CLAMP));
        canvas.drawCircle(685, 181, 86, paint);
        paint.setShader(null);

        color(0xff102030);
        canvas.drawRect(653, 169, 718, 302, paint);
        color(0xffd3b37b);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(3f);
        canvas.drawRoundRect(650, 146, 720, 304, 35f, 35f, paint);
        color(0xff18383d);
        canvas.drawRect(660, 172, 710, 294, paint);
        color(0xffb6dacd);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(1.5f);
        canvas.drawLine(685, 175, 685, 292, paint);

        color(0xff0b1926);
        Path front = new Path();
        front.moveTo(0, 370);
        front.lineTo(0, 336);
        front.lineTo(180, 335);
        front.lineTo(330, 356);
        front.lineTo(520, 335);
        front.lineTo(685, 314);
        front.lineTo(840, 328);
        front.lineTo(960, 314);
        front.lineTo(960, 370);
        front.close();
        canvas.drawPath(front, paint);

        color(0x80e6bc81);
        paint.setStrokeWidth(1);
        for (int i = 0; i < 5; i++) {
            canvas.drawLine(575 - i * 50, 370, 675 - i * 10, 313, paint);
            canvas.drawLine(800 + i * 50, 370, 699 + i * 10, 313, paint);
        }
        canvas.restoreToCount(save);
    }

    private void mountain(Canvas canvas, int color, float... coordinates) {
        color(color);
        Path line = new Path();
        line.moveTo(coordinates[0], coordinates[1]);
        for (int i = 2; i < coordinates.length; i += 2) {
            line.lineTo(coordinates[i], coordinates[i + 1]);
        }
        line.lineTo(960, 370);
        line.lineTo(0, 370);
        line.close();
        canvas.drawPath(line, paint);
    }
}
