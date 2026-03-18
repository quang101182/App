package com.voicesnap.app.util

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import java.net.SocketTimeoutException
import java.net.UnknownHostException

object NetworkHelper {

    fun isNetworkAvailable(context: Context): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return true // assume available if we can't check
        val network = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    fun friendlyErrorMessage(e: Exception): String = when {
        e is UnknownHostException -> "Pas de connexion internet"
        e is SocketTimeoutException -> "Connexion trop lente, r\u00e9essayez"
        e.message?.contains("Unable to resolve host") == true -> "Pas de connexion internet"
        e.message?.contains("timeout") == true -> "Connexion trop lente"
        e.message?.contains("failed to connect") == true -> "Serveur inaccessible"
        e.message?.contains("429") == true -> "Service surcharg\u00e9, r\u00e9essayez"
        e.message?.contains("500") == true -> "Erreur serveur"
        e.message?.contains("502") == true -> "Serveur temporairement indisponible"
        e.message?.contains("503") == true -> "Service en maintenance"
        else -> "Erreur: ${e.message?.take(50) ?: "inconnue"}"
    }
}
