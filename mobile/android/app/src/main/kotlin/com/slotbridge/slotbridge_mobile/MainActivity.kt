package com.slotbridge.slotbridge_mobile

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.Executors

class MainActivity : FlutterActivity() {
  private val executor = Executors.newSingleThreadExecutor()
  private lateinit var updates: MethodChannel
  override fun configureFlutterEngine(engine: FlutterEngine) {
    super.configureFlutterEngine(engine)
    updates = MethodChannel(engine.dartExecutor.binaryMessenger, "slotbridge/updater")
    updates.setMethodCallHandler { call, result ->
      when (call.method) {
        "installedVersionCode" -> result.success(if (Build.VERSION.SDK_INT >= 28) packageManager.getPackageInfo(packageName, 0).longVersionCode else @Suppress("DEPRECATION") packageManager.getPackageInfo(packageName, 0).versionCode.toLong())
        "checkDue" -> {
          val prefs = getSharedPreferences("slotbridge_updater", MODE_PRIVATE)
          val now = System.currentTimeMillis(); val last = prefs.getLong("last_check", 0)
          if (now - last >= 6 * 60 * 60 * 1000) { prefs.edit().putLong("last_check", now).apply(); result.success(true) } else result.success(false)
        }
        "downloadAndInstall" -> {
          val url = call.argument<String>("url") ?: return@setMethodCallHandler result.error("URL", "Missing URL", null)
          val sha = call.argument<String>("sha256") ?: return@setMethodCallHandler result.error("SHA", "Missing SHA-256", null)
          executor.execute { try { downloadAndInstall(url, sha); runOnUiThread { result.success(true) } } catch (e: Exception) { runOnUiThread { result.error("UPDATE_FAILED", e.message, null) } } }
        }
        else -> result.notImplemented()
      }
    }
  }

  private fun downloadAndInstall(value: String, expected: String) {
    var url = URL(value)
    require(url.protocol == "https") { "Update URL must use HTTPS" }
    var connection: HttpURLConnection
    while (true) {
      connection = url.openConnection() as HttpURLConnection
      connection.instanceFollowRedirects = false; connection.connectTimeout = 15000; connection.readTimeout = 60000
      if (connection.responseCode in 300..399) { val next = URL(connection.getHeaderField("Location")); connection.disconnect(); require(next.protocol == "https") { "Redirect must use HTTPS" }; url = next; continue }
      require(connection.responseCode == 200) { "Download failed" }; break
    }
    val directory = File(externalCacheDir, "updates").apply { mkdirs() }
    val target = File(directory, "SlotBridge-update.apk")
    val total = connection.contentLengthLong
    connection.inputStream.use { input -> target.outputStream().use { output ->
      val buffer = ByteArray(64 * 1024); var downloaded = 0L
      while (true) { val count = input.read(buffer); if (count < 0) break; output.write(buffer, 0, count); downloaded += count
        if (total > 0) runOnUiThread { updates.invokeMethod("progress", downloaded.toDouble() / total.toDouble()) }
      }
    } }
    val actual = MessageDigest.getInstance("SHA-256").digest(target.readBytes()).joinToString("") { "%02x".format(it) }
    if (!actual.equals(expected, true)) { target.delete(); throw SecurityException("SHA-256 mismatch") }
    if (Build.VERSION.SDK_INT >= 26 && !packageManager.canRequestPackageInstalls()) {
      startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:$packageName"))); return
    }
    val uri = FileProvider.getUriForFile(this, "$packageName.updates", target)
    startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, "application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK))
  }
}
