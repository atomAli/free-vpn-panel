package com.family.vpnpanel

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    companion object {
        // بعد از دیپلوی Worker روی Cloudflare، آدرس واقعی را جایگزین کنید
        const val CONFIG_URL = "https://family-vpn.YOUR_SUBDOMAIN.workers.dev/cfg"
    }

    private val scanner = registerForActivityResult(ScanContract()) { result ->
        result.contents?.let(::handleConfig)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        findViewById<Button>(R.id.btnFetchServer).setOnClickListener {
            fetchConfigFromServer()
        }

        findViewById<Button>(R.id.btnScan).setOnClickListener {
            val options = ScanOptions()
                .setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                .setPrompt("QR کانفیگ را در کادر قرار دهید")
                .setBeepEnabled(false)
                .setOrientationLocked(true)
            scanner.launch(options)
        }

        findViewById<Button>(R.id.btnSubmitManual).setOnClickListener {
            val text = findViewById<EditText>(R.id.etManual).text.toString().trim()
            if (text.isNotEmpty()) handleConfig(text) else {
                Toast.makeText(this, "کانفیگ را وارد کنید", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun fetchConfigFromServer() {
        val status = findViewById<TextView>(R.id.tvStatus)
        status.text = getString(R.string.fetching)

        thread {
            var result: String? = null
            try {
                val connection = URL(CONFIG_URL).openConnection() as HttpURLConnection
                connection.connectTimeout = 15000
                connection.readTimeout = 15000
                connection.requestMethod = "GET"
                result = connection.inputStream.bufferedReader().use { it.readText() }.trim()
            } catch (e: Exception) {
                e.printStackTrace()
            }

            runOnUiThread {
                if (result != null && result.startsWith("vless://")) {
                    handleConfig(result)
                } else if (result != null && isBase64Subscription(result)) {
                    val uri = String(android.util.Base64.decode(result, android.util.Base64.DEFAULT))
                        .trim().lineSequence().firstOrNull { it.startsWith("vless://") }
                    if (uri != null) handleConfig(uri)
                    else fail(status)
                } else {
                    fail(status)
                }
            }
        }
    }

    private fun fail(status: TextView) {
        status.text = ""
        Toast.makeText(this, getString(R.string.fetch_failed), Toast.LENGTH_LONG).show()
    }

    private fun isBase64Subscription(text: String): Boolean {
        return !text.startsWith("vless://") && text.matches(Regex("[A-Za-z0-9+/=\\s]+"))
    }

    private fun handleConfig(raw: String) {
        val uri = raw.lineSequence().firstOrNull { it.startsWith("vless://") }?.trim()
            ?: raw.trim()

        if (!uri.startsWith("vless://")) {
            Toast.makeText(this, "این یک کانفیگ معتبر vless نیست", Toast.LENGTH_LONG).show()
            return
        }

        findViewById<TextView>(R.id.tvStatus).text = uri

        val clipboard = getSystemService(ClipboardManager::class.java)
        clipboard.setPrimaryClip(ClipData.newPlainText("config", uri))
        Toast.makeText(this, "کانفیگ دریافت شد و کپی شد", Toast.LENGTH_SHORT).show()

        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(uri)))
        } catch (e: Exception) {
            Toast.makeText(this, "v2rayNG نصب نیست؛ کانفیگ در کلیپ‌بورد است", Toast.LENGTH_LONG).show()
        }
    }
}
