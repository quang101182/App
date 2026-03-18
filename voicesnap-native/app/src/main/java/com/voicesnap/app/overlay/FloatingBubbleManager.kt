package com.voicesnap.app.overlay

import android.animation.ObjectAnimator
import android.animation.PropertyValuesHolder
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.util.Log
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageView
import android.view.animation.AccelerateDecelerateInterpolator
import android.view.animation.LinearInterpolator
import com.voicesnap.app.R
import com.voicesnap.app.service.RecordingService
import com.voicesnap.app.service.RecordingState

class FloatingBubbleManager(private val context: Context) {

    companion object {
        private const val TAG = "FloatingBubble"
        private const val BUBBLE_SIZE_DP = 56
        private const val ICON_SIZE_DP = 28
    }

    private var windowManager: WindowManager? = null
    private var bubbleView: FrameLayout? = null
    private var bubbleBackground: View? = null
    private var iconView: ImageView? = null
    private var currentAnimator: ObjectAnimator? = null
    private var isShowing = false

    private val density: Float get() = context.resources.displayMetrics.density

    private fun dpToPx(dp: Int): Int = (dp * density).toInt()

    fun show() {
        if (isShowing) return

        try {
            windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager

            // Create bubble layout
            bubbleView = FrameLayout(context).apply {
                layoutParams = FrameLayout.LayoutParams(dpToPx(BUBBLE_SIZE_DP), dpToPx(BUBBLE_SIZE_DP))
            }

            // Circular background
            bubbleBackground = View(context).apply {
                layoutParams = FrameLayout.LayoutParams(dpToPx(BUBBLE_SIZE_DP), dpToPx(BUBBLE_SIZE_DP))
                background = GradientDrawable().apply {
                    shape = GradientDrawable.OVAL
                    setColor(Color.parseColor("#EF4444")) // Red = recording
                }
                elevation = dpToPx(8).toFloat()
            }
            bubbleView!!.addView(bubbleBackground)

            // Mic icon
            iconView = ImageView(context).apply {
                val iconSize = dpToPx(ICON_SIZE_DP)
                layoutParams = FrameLayout.LayoutParams(iconSize, iconSize).apply {
                    gravity = Gravity.CENTER
                }
                setImageResource(R.drawable.ic_tile_mic)
                setColorFilter(Color.WHITE)
            }
            bubbleView!!.addView(iconView)

            // Touch listener — tap to stop
            bubbleView!!.setOnClickListener {
                Log.d(TAG, "Bubble tapped — sending STOP")
                val stopIntent = Intent(context, RecordingService::class.java).apply {
                    action = RecordingService.ACTION_STOP
                }
                context.startService(stopIntent)
            }

            // Window params
            val params = WindowManager.LayoutParams(
                dpToPx(BUBBLE_SIZE_DP),
                dpToPx(BUBBLE_SIZE_DP),
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                        WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.END
                x = dpToPx(16)
                y = dpToPx(200)
            }

            windowManager!!.addView(bubbleView, params)
            isShowing = true

            // Start pulse animation
            startPulseAnimation()

            Log.d(TAG, "Bubble shown")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to show bubble", e)
            isShowing = false
        }
    }

    fun updateState(state: RecordingState) {
        if (!isShowing) return

        try {
            val bg = bubbleBackground?.background as? GradientDrawable ?: return

            when (state) {
                RecordingState.RECORDING -> {
                    bg.setColor(Color.parseColor("#EF4444")) // Red
                    stopCurrentAnimation()
                    startPulseAnimation()
                    iconView?.rotation = 0f
                }
                RecordingState.TRANSCRIBING -> {
                    bg.setColor(Color.parseColor("#6D28D9")) // Violet
                    stopCurrentAnimation()
                    startSpinAnimation()
                }
                RecordingState.TRANSLATING -> {
                    bg.setColor(Color.parseColor("#06B6D4")) // Cyan
                    stopCurrentAnimation()
                    startSpinAnimation()
                }
                RecordingState.IDLE -> {
                    dismiss()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "updateState error", e)
        }
    }

    fun dismiss() {
        if (!isShowing) return

        try {
            stopCurrentAnimation()
            windowManager?.removeView(bubbleView)
            Log.d(TAG, "Bubble dismissed")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to dismiss bubble", e)
        } finally {
            bubbleView = null
            bubbleBackground = null
            iconView = null
            windowManager = null
            isShowing = false
        }
    }

    private fun startPulseAnimation() {
        val view = bubbleBackground ?: return

        val scaleX = PropertyValuesHolder.ofFloat(View.SCALE_X, 1f, 1.2f, 1f)
        val scaleY = PropertyValuesHolder.ofFloat(View.SCALE_Y, 1f, 1.2f, 1f)
        val alpha = PropertyValuesHolder.ofFloat(View.ALPHA, 1f, 0.7f, 1f)

        currentAnimator = ObjectAnimator.ofPropertyValuesHolder(view, scaleX, scaleY, alpha).apply {
            duration = 900L
            repeatCount = ObjectAnimator.INFINITE
            interpolator = AccelerateDecelerateInterpolator()
            start()
        }
    }

    private fun startSpinAnimation() {
        val view = iconView ?: return

        currentAnimator = ObjectAnimator.ofFloat(view, View.ROTATION, 0f, 360f).apply {
            duration = 1000L
            repeatCount = ObjectAnimator.INFINITE
            interpolator = LinearInterpolator()
            start()
        }
    }

    private fun stopCurrentAnimation() {
        currentAnimator?.cancel()
        currentAnimator = null
        // Reset transforms
        bubbleBackground?.scaleX = 1f
        bubbleBackground?.scaleY = 1f
        bubbleBackground?.alpha = 1f
        iconView?.rotation = 0f
    }
}
