from django.contrib import admin

from .models import WebAuthnChallenge, WebAuthnCredential, WebAuthnUser


@admin.register(WebAuthnUser)
class WebAuthnUserAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("created_at",)


@admin.register(WebAuthnCredential)
class WebAuthnCredentialAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "sign_count", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("created_at",)


@admin.register(WebAuthnChallenge)
class WebAuthnChallengeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "ceremony", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("created_at",)
