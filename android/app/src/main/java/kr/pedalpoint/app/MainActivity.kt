package kr.pedalpoint.app

import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.ProgressBar
import android.widget.TextView

/**
 * Pedal Point 이용자 앱.
 *
 * PC에서 실행 중인 Streamlit 서버의 이용자 화면을 WebView로 띄우는 하이브리드 앱이다.
 * 모든 데이터 처리(대여·반납·결제·마일리지)는 서버와 padal DB에서 이뤄진다.
 * User-Agent 끝에 "PedalPointApp"을 붙여, 서버가 이 앱의 접속을 알아보고 모바일 화면을 보여준다.
 */
class MainActivity : Activity() {

    private lateinit var web: WebView
    private lateinit var progress: ProgressBar
    private lateinit var errorView: View
    private lateinit var errorText: TextView

    private val prefs by lazy { getSharedPreferences("pedalpoint", MODE_PRIVATE) }
    private val serverUrl: String
        get() = prefs.getString(KEY_SERVER, "") ?: ""

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        web = findViewById(R.id.web)
        progress = findViewById(R.id.progress)
        errorView = findViewById(R.id.error)
        errorText = findViewById(R.id.error_text)

        web.settings.apply {
            javaScriptEnabled = true          // Streamlit은 React 앱
            domStorageEnabled = true
            userAgentString = "$userAgentString $UA_SUFFIX"
            setSupportZoom(false)
        }
        web.webViewClient = AppWebViewClient()
        web.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, newProgress: Int) {
                progress.progress = newProgress
                progress.visibility = if (newProgress < 100) View.VISIBLE else View.GONE
            }
        }

        findViewById<Button>(R.id.retry).setOnClickListener { load() }
        findViewById<Button>(R.id.settings).setOnClickListener { askServer(first = false) }

        when {
            serverUrl.isEmpty() -> askServer(first = true)
            savedInstanceState != null -> web.restoreState(savedInstanceState)
            else -> load()
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    /** 뒤로가기: 앱 안의 이전 화면 → 없으면 종료·서버 주소 변경 선택. */
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (errorView.visibility != View.VISIBLE && web.canGoBack()) {
            web.goBack()
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Pedal Point")
            .setItems(arrayOf("앱 종료", "서버 주소 변경", "새로고침")) { _, which ->
                when (which) {
                    0 -> finish()
                    1 -> askServer(first = false)
                    2 -> load()
                }
            }
            .show()
    }

    private fun load() {
        errorView.visibility = View.GONE
        web.visibility = View.VISIBLE
        web.loadUrl(serverUrl)
    }

    private fun showError(reason: String) {
        web.stopLoading()
        web.visibility = View.INVISIBLE
        errorView.visibility = View.VISIBLE
        errorText.text = "주소: $serverUrl\n($reason)\n\nPC에서 run.bat이 실행 중인지,\n휴대폰과 PC가 같은 Wi-Fi에 있는지 확인해 주세요."
    }

    /** 서버 주소 입력. 처음 실행할 때는 필수. */
    private fun askServer(first: Boolean) {
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            hint = "예: 192.168.0.12:8501"
            setText(serverUrl.removePrefix("http://"))
            setSingleLine()
        }
        val box = FrameLayout(this).apply {
            val pad = (20 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad / 2, pad, 0)
            addView(input)
        }
        AlertDialog.Builder(this)
            .setTitle("서버 주소")
            .setMessage("PC에서 run.bat을 실행하면 나오는 Network URL을 입력하세요.")
            .setView(box)
            .setCancelable(!first)
            .setPositiveButton("연결") { _, _ ->
                val url = normalize(input.text.toString())
                if (url == null) {
                    askServer(first)
                } else {
                    prefs.edit().putString(KEY_SERVER, url).apply()
                    web.clearHistory()
                    load()
                }
            }
            .setNegativeButton(if (first) "종료" else "취소") { _, _ -> if (first) finish() }
            .show()
    }

    private inner class AppWebViewClient : WebViewClient() {
        override fun onPageStarted(view: WebView, url: String?, favicon: Bitmap?) {
            progress.visibility = View.VISIBLE
        }

        override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
            if (request.isForMainFrame) showError(error.description.toString())
        }

        /** 서버 안의 이동은 앱에서, 바깥 링크는 브라우저로 연다. */
        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
            val target = request.url
            val base = Uri.parse(serverUrl)
            if (target.host == base.host && target.port == base.port) return false
            runCatching { startActivity(Intent(Intent.ACTION_VIEW, target)) }
            return true
        }
    }

    companion object {
        private const val KEY_SERVER = "server_url"
        private const val UA_SUFFIX = "PedalPointApp/1.0"
        private const val DEFAULT_PORT = 8501

        /** "192.168.0.12" → "http://192.168.0.12:8501". 형식이 틀리면 null. */
        fun normalize(raw: String): String? {
            var text = raw.trim().trimEnd('/')
            if (text.isEmpty()) return null
            if (!text.startsWith("http://") && !text.startsWith("https://")) text = "http://$text"
            val uri = Uri.parse(text)
            val host = uri.host ?: return null
            val port = if (uri.port == -1) DEFAULT_PORT else uri.port
            return "${uri.scheme}://$host:$port"
        }
    }
}
