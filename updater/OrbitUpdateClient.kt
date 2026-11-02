package dev.orbit.updates

import android.content.Context
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * Experimental reference component. NOT yet included in existing APKs.
 * check() and download() must run on a background executor; never on the UI thread.
 * Installation must be explicitly initiated in the UI.
 */
class OrbitUpdateClient(private val context: Context) {
    private val feed = "https://raw.githubusercontent.com/1234Taschenlampe/ORBIT/main/updates.json"
    private val repoPrefix = "https://raw.githubusercontent.com/1234Taschenlampe/ORBIT/main/apks/"
    private val maxFeed = 2 * 1024 * 1024L
    private val maxApk = 100 * 1000 * 1000L

    data class Update(
        val packageName: String,
        val versionCode: Long,
        val versionName: String,
        val filename: String,
        val url: String,
        val size: Long,
        val sha256: String
    )

    @Suppress("DEPRECATION")
    private fun packageInfo(pkg: String): PackageInfo {
        val manager = context.packageManager
        return if (Build.VERSION.SDK_INT >= 33) {
            manager.getPackageInfo(pkg, PackageManager.PackageInfoFlags.of(
                PackageManager.GET_SIGNING_CERTIFICATES.toLong()
            ))
        } else {
            manager.getPackageInfo(pkg, PackageManager.GET_SIGNING_CERTIFICATES)
        }
    }

    private fun sha256(b: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(b).joinToString("") { "%02x".format(it) }

    private fun getJson(url: String): String {
        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 12000
            readTimeout = 12000
        }
        try {
            if (conn.responseCode != 200) error("Invalid HTTP response")
            val out = ByteArrayOutputStream()
            conn.inputStream.use { input ->
                val buf = ByteArray(16384)
                while (true) {
                    val n = input.read(buf)
                    if (n < 0) break
                    if (out.size().toLong() + n > maxFeed) error("Feed too large")
                    out.write(buf, 0, n)
                }
            }
            return out.toString("UTF-8")
        } finally { conn.disconnect() }
    }

    /** Returns a newer release matching the installed app's package and ACTIVE signing key. */
    fun check(packageName: String): Update? {
        val installed = try {
            packageInfo(packageName)
        } catch (_: PackageManager.NameNotFoundException) {
            return null
        }
        val signing = installed.signingInfo ?: return null
        val certs = signing.apkContentsSigners.map { sha256(it.toByteArray()) }.toSet()
        val installedCode = installed.longVersionCode
        val artifacts = JSONObject(getJson(feed)).getJSONArray("artifacts")
        var best: Update? = null
        for (i in 0 until artifacts.length()) {
            val item = artifacts.getJSONObject(i)
            if (item.optString("packageName") != packageName) continue
            if (item.optString("channel") != "release") continue
            if (!item.optBoolean("recommendedForInstalledSigner")) continue
            if (item.optString("signerSha256") !in certs) continue
            val code = item.optLong("versionCode", -1)
            if (code <= installedCode) continue
            if (item.optInt("minSdk", 0) > Build.VERSION.SDK_INT) continue
            val name = item.optString("filename")
            if (!Regex("[A-Za-z0-9_.()+-]+\\.apk").matches(name)) continue
            val url = item.optString("url")
            if (!url.startsWith(repoPrefix) || !url.endsWith("/" + java.net.URLEncoder.encode(name, "UTF-8").replace("+", "%20"))) continue
            val size = item.optLong("size", 0)
            if (size < 1 || size > maxApk) continue
            val hash = item.optString("sha256")
            if (!Regex("[a-f0-9]{64}").matches(hash)) continue
            val candidate = Update(packageName, code, item.optString("versionName"), name, url, size, hash)
            if (best == null || code > best.versionCode) best = candidate
        }
        return best
    }

    /** Automatically download to private cache and validate exact size + SHA256. */
    fun download(update: Update): File {
        val dir = File(context.cacheDir, "orbit").also { it.mkdirs() }
        val partial = File.createTempFile("orbit-", ".tmp", dir)
        val final = File(dir, update.sha256 + ".apk")
        val digest = MessageDigest.getInstance("SHA-256")
        var total = 0L
        try {
            val conn = (URL(update.url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 15000
                readTimeout = 30000
            }
            try {
                if (conn.responseCode != 200) error("Download unavailable")
                partial.outputStream().use { dest ->
                    conn.inputStream.use { source ->
                        val buf = ByteArray(32768)
                        while (true) {
                            val n = source.read(buf)
                            if (n < 0) break
                            total += n
                            if (total > update.size || total > maxApk) error("APK too large")
                            digest.update(buf, 0, n)
                            dest.write(buf, 0, n)
                        }
                    }
                }
            } finally { conn.disconnect() }
            val sha = digest.digest().joinToString("") { "%02x".format(it) }
            if (total != update.size || !sha.equals(update.sha256, true)) error("Invalid APK digest")
            if (final.exists()) final.delete()
            check(partial.renameTo(final)) { "Cannot save APK" }
            return final
        } finally { partial.delete() }
    }

    /** Invoked by a visible Update button. Android decides whether confirmation is needed. */
    fun launchInstaller(verifiedApk: File): Boolean {
        if (Build.VERSION.SDK_INT >= 26 && !context.packageManager.canRequestPackageInstalls()) {
            val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                data = Uri.parse("package:" + context.packageName)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            return false
        }
        val uri = FileProvider.getUriForFile(
            context, context.packageName + ".orbit.fileprovider", verifiedApk
        )
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(intent)
        return true
    }
}
