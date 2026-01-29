// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  devtools: { enabled: true },
  runtimeConfig: {
    public: {
      webauthnApiBase:
        process.env.NUXT_PUBLIC_WEBAUTHN_API_BASE ?? "http://localhost:8000",
    },
  },
})
