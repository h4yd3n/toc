package com.toc.coptoc

import android.net.Uri
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView

/** Shared console with the existing demo profile. It does not implement production SSO. */
@Composable
fun NativeWorkspace(baseUrl: String, userId: String, section: String, onClose: () -> Unit) {
    var chooser by remember { mutableStateOf<ValueCallback<Array<Uri>>?>(null) }
    var browser by remember { mutableStateOf<WebView?>(null) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        chooser?.onReceiveValue(uri?.let { arrayOf(it) }); chooser = null
    }
    val origin = remember(baseUrl) { Uri.parse(baseUrl) }
    val url = remember(baseUrl, userId, section) {
        Uri.parse(baseUrl.trimEnd('/') + "/console/").buildUpon()
            .appendQueryParameter("embedded", "1").appendQueryParameter("profile", userId)
            .encodedFragment("/workspace/$section/overview").build().toString()
    }
    BackHandler { if (browser?.canGoBack() == true) browser?.goBack() else onClose() }
    DisposableEffect(Unit) { onDispose { chooser?.onReceiveValue(null); browser?.destroy() } }
    AndroidView(modifier = Modifier.fillMaxSize(), factory = { context ->
        WebView(context).apply {
            browser = this
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = false
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    val target = request.url
                    return target.scheme != origin.scheme || target.host != origin.host || target.port != origin.port
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(view: WebView, callback: ValueCallback<Array<Uri>>, params: FileChooserParams): Boolean {
                    chooser?.onReceiveValue(null); chooser = callback
                    picker.launch(arrayOf("application/pdf")); return true
                }
            }
            loadUrl(url)
        }
    })
}
