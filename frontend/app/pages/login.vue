<template>
  <main class="page">
    <section class="card">
      <header class="card__header">
        <h1>WebAuthn ログイン</h1>
        <p class="muted">
          パスキー / 生体認証によるログインです。スマホ・Bluetooth（BLE）認証機も利用できます。
        </p>
      </header>

      <div class="status" :data-type="statusType" v-if="statusMessage">
        {{ statusMessage }}
      </div>

      <div class="field">
        <label for="username">ユーザー名</label>
        <input
          id="username"
          v-model="username"
          type="text"
          placeholder="例: yukimoto"
          autocomplete="username"
        />
      </div>

      <div class="actions">
        <button class="primary" :disabled="!canRegister" @click="handleRegister">
          パスキーを登録
        </button>
        <button class="secondary" :disabled="!canLogin" @click="handleLogin">
          パスキーでログイン（ユーザー名で）
        </button>
        <button
          class="secondary discoverable"
          :disabled="!isSupported || isLoading"
          @click="handleLoginDiscoverable"
        >
          デバイスからパスキーを選ぶ（PCに認証機がなくてもスマホ可）
        </button>
      </div>

      <div class="meta">
        <p>WebAuthn 対応: <strong>{{ isSupported ? "はい" : "いいえ" }}</strong></p>
        <p>認証機（Touch ID / スマホ・BLE）: <strong>{{ platformLabel }}</strong></p>
        <p>API: <strong>{{ apiBase }}</strong></p>
        <p>入力中ユーザー: <strong>{{ storedUserName || username || "未入力" }}</strong></p>
        <p>最終ログイン: <strong>{{ lastLoginAt || "なし" }}</strong></p>
      </div>

      <div class="footer">
        <button class="text" @click="clearStoredCredential">ローカル状態をリセット</button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue"

const username = ref("")
const statusMessage = ref("")
const statusType = ref<"info" | "success" | "error">("info")
const isSupported = ref(false)
const storedUserName = ref<string | null>(null)
const lastLoginAt = ref<string | null>(null)
const isLoading = ref(false)
const isPlatformAuthenticatorAvailable = ref(false)
const runtimeConfig = useRuntimeConfig()
const apiBase = computed(() => runtimeConfig.public.webauthnApiBase)

const canRegister = computed(() => {
  return isSupported.value && !isLoading.value && username.value.trim().length > 0
})

const canLogin = computed(() => {
  return isSupported.value && !isLoading.value && username.value.trim().length > 0
})

const platformLabel = computed(() => {
  if (!isSupported.value) return "未対応"
  return isPlatformAuthenticatorAvailable.value ? "利用可" : "未確認"
})

onMounted(() => {
  if (!import.meta.client) return
  isSupported.value = typeof window !== "undefined" && "PublicKeyCredential" in window
  storedUserName.value = localStorage.getItem("webauthn.userName")
  lastLoginAt.value = localStorage.getItem("webauthn.lastLoginAt")
  if (storedUserName.value) {
    username.value = storedUserName.value
  }
  if (isSupported.value && typeof PublicKeyCredential !== "undefined") {
    PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
      .then((available) => {
        isPlatformAuthenticatorAvailable.value = available
      })
      .catch(() => {
        isPlatformAuthenticatorAvailable.value = false
      })
  }
})

const setStatus = (message: string, type: "info" | "success" | "error") => {
  statusMessage.value = message
  statusType.value = type
}

const toBase64Url = (buffer: ArrayBuffer) => {
  const bytes = new Uint8Array(buffer)
  let binary = ""
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte)
  })
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "")
}

const fromBase64Url = (value: string) => {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/")
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=")
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

const postJson = async <T>(path: string, body: Record<string, unknown>) => {
  const response = await fetch(`${apiBase.value}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const data = (await response.json()) as T & { error?: string }
  if (!response.ok) {
    throw new Error(data.error || "サーバー処理に失敗しました。")
  }
  return data
}

const persistUserName = (userName: string) => {
  localStorage.setItem("webauthn.userName", userName)
  storedUserName.value = userName
}

const normalizeCreationOptions = (options: any) => {
  return {
    ...options,
    challenge: fromBase64Url(options.challenge),
    user: {
      ...options.user,
      id: fromBase64Url(options.user.id),
    },
    excludeCredentials: options.excludeCredentials?.map((cred: any) => ({
      ...cred,
      id: fromBase64Url(cred.id),
    })),
  }
}

const normalizeRequestOptions = (options: any) => {
  return {
    ...options,
    challenge: fromBase64Url(options.challenge),
    allowCredentials: options.allowCredentials?.map((cred: any) => ({
      ...cred,
      id: fromBase64Url(cred.id),
    })),
  }
}

const handleRegister = async () => {
  if (!import.meta.client) return
  if (!canRegister.value) {
    setStatus("ユーザー名を入力してください。", "error")
    return
  }
  if (!isSupported.value) {
    setStatus("このブラウザは WebAuthn に対応していません。", "error")
    return
  }
  isLoading.value = true
  setStatus("パスキーを登録しています…（スマホ・Bluetooth 認証機も利用可）", "info")
  try {
    const trimmed = username.value.trim()
    const optionsResponse = await postJson<{ publicKey: any }>(
      "/api/webauthn/register/options",
      { username: trimmed },
    )
    const publicKey = normalizeCreationOptions(optionsResponse.publicKey)
    const credential = (await navigator.credentials.create({
      publicKey,
    })) as PublicKeyCredential | null

    if (!credential) {
      setStatus("登録がキャンセルされました。", "error")
      return
    }

    const attestationResponse = credential.response as AuthenticatorAttestationResponse
    const credentialJson = {
      id: credential.id,
      rawId: toBase64Url(credential.rawId),
      type: credential.type,
      response: {
        attestationObject: toBase64Url(attestationResponse.attestationObject),
        clientDataJSON: toBase64Url(attestationResponse.clientDataJSON),
        transports: attestationResponse.getTransports?.() ?? [],
      },
      clientExtensionResults: credential.getClientExtensionResults?.() ?? {},
      authenticatorAttachment: credential.authenticatorAttachment ?? null,
    }

    await postJson("/api/webauthn/register/verify", {
      username: trimmed,
      credential: credentialJson,
    })

    persistUserName(trimmed)
    setStatus("パスキーを登録しました。次はログインしてください。", "success")
  } catch (error) {
    const message = error instanceof Error ? error.message : "登録に失敗しました。"
    setStatus(message, "error")
  } finally {
    isLoading.value = false
  }
}

const handleLogin = async () => {
  if (!import.meta.client) return
  if (!isSupported.value) {
    setStatus("このブラウザは WebAuthn に対応していません。", "error")
    return
  }

  isLoading.value = true
  setStatus("パスキーで認証しています…（スマホ・Bluetooth 認証機も利用可）", "info")
  try {
    const trimmed = username.value.trim()
    const optionsResponse = await postJson<{ publicKey: any }>(
      "/api/webauthn/login/options",
      { username: trimmed },
    )
    const publicKey = normalizeRequestOptions(optionsResponse.publicKey)
    const credential = (await navigator.credentials.get({
      publicKey,
      mediation: "optional",
    })) as PublicKeyCredential | null

    if (!credential) {
      setStatus("認証がキャンセルされました。", "error")
      return
    }

    const assertionResponse = credential.response as AuthenticatorAssertionResponse
    const credentialJson = {
      id: credential.id,
      rawId: toBase64Url(credential.rawId),
      type: credential.type,
      response: {
        authenticatorData: toBase64Url(assertionResponse.authenticatorData),
        clientDataJSON: toBase64Url(assertionResponse.clientDataJSON),
        signature: toBase64Url(assertionResponse.signature),
        userHandle: assertionResponse.userHandle
          ? toBase64Url(assertionResponse.userHandle)
          : null,
      },
      clientExtensionResults: credential.getClientExtensionResults?.() ?? {},
      authenticatorAttachment: credential.authenticatorAttachment ?? null,
    }

    await postJson("/api/webauthn/login/verify", {
      username: trimmed,
      credential: credentialJson,
    })

    const timestamp = new Date().toLocaleString("ja-JP")
    lastLoginAt.value = timestamp
    localStorage.setItem("webauthn.lastLoginAt", timestamp)
    persistUserName(trimmed)
    setStatus("認証成功。サーバー側で検証しました。", "success")
  } catch (error) {
    const message = error instanceof Error ? error.message : "認証に失敗しました。"
    setStatus(message, "error")
  } finally {
    isLoading.value = false
  }
}

/** PCに認証機がなくても、スマホ等を認証機として選べる（ユーザー名不要） */
const handleLoginDiscoverable = async () => {
  if (!import.meta.client) return
  if (!isSupported.value) {
    setStatus("このブラウザは WebAuthn に対応していません。", "error")
    return
  }

  isLoading.value = true
  setStatus("デバイスからパスキーを選んでください…（スマホ・Bluetooth 可）", "info")
  try {
    const optionsResponse = await postJson<{ publicKey: any }>(
      "/api/webauthn/login/options/discoverable",
      {},
    )
    const publicKey = normalizeRequestOptions(optionsResponse.publicKey)
    const credential = (await navigator.credentials.get({
      publicKey,
      mediation: "conditional",
    })) as PublicKeyCredential | null

    if (!credential) {
      setStatus("認証がキャンセルされました。", "error")
      return
    }

    const assertionResponse = credential.response as AuthenticatorAssertionResponse
    const credentialJson = {
      id: credential.id,
      rawId: toBase64Url(credential.rawId),
      type: credential.type,
      response: {
        authenticatorData: toBase64Url(assertionResponse.authenticatorData),
        clientDataJSON: toBase64Url(assertionResponse.clientDataJSON),
        signature: toBase64Url(assertionResponse.signature),
        userHandle: assertionResponse.userHandle
          ? toBase64Url(assertionResponse.userHandle)
          : null,
      },
      clientExtensionResults: credential.getClientExtensionResults?.() ?? {},
      authenticatorAttachment: credential.authenticatorAttachment ?? null,
    }

    const result = await postJson<{ username: string }>(
      "/api/webauthn/login/verify/discoverable",
      { credential: credentialJson },
    )

    const loggedInUsername = result.username || "unknown"
    const timestamp = new Date().toLocaleString("ja-JP")
    lastLoginAt.value = timestamp
    localStorage.setItem("webauthn.lastLoginAt", timestamp)
    persistUserName(loggedInUsername)
    username.value = loggedInUsername
    setStatus(`認証成功: ${loggedInUsername}（デバイスから選択）`, "success")
  } catch (error) {
    const message = error instanceof Error ? error.message : "認証に失敗しました。"
    setStatus(message, "error")
  } finally {
    isLoading.value = false
  }
}

const clearStoredCredential = () => {
  if (!import.meta.client) return
  localStorage.removeItem("webauthn.userName")
  localStorage.removeItem("webauthn.lastLoginAt")
  storedUserName.value = null
  lastLoginAt.value = null
  setStatus("ローカル状態を削除しました。", "info")
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 16px;
}

.card {
  width: min(560px, 100%);
  background: #ffffff;
  border-radius: 16px;
  padding: 28px;
  box-shadow: 0 20px 60px rgba(20, 20, 60, 0.1);
  display: grid;
  gap: 20px;
}

.card__header h1 {
  margin: 0 0 8px;
  font-size: 1.6rem;
}

.muted {
  margin: 0;
  color: #6b7280;
  font-size: 0.95rem;
}

.status {
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 0.95rem;
  background: #eef2ff;
  color: #3730a3;
}

.status[data-type="success"] {
  background: #ecfdf5;
  color: #065f46;
}

.status[data-type="error"] {
  background: #fef2f2;
  color: #991b1b;
}

.field {
  display: grid;
  gap: 8px;
}

label {
  font-weight: 600;
}

input {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  font-size: 1rem;
}

.actions {
  display: grid;
  gap: 12px;
}

button {
  padding: 12px 14px;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary {
  background: #4f46e5;
  color: #ffffff;
}

.secondary {
  background: #e0e7ff;
  color: #312e81;
}

.secondary.discoverable {
  background: #ecfdf5;
  color: #065f46;
}

.text {
  background: none;
  padding: 4px 0;
  color: #6b7280;
}

.meta {
  display: grid;
  gap: 6px;
  color: #374151;
  font-size: 0.95rem;
}

.footer {
  display: flex;
  justify-content: flex-end;
}
</style>
