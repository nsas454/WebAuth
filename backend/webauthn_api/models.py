from django.db import models
from django.contrib.auth.models import User


class WebAuthnUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="webauthn_profile")
    webauthn_user_id = models.BinaryField(unique=True, max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class WebAuthnCredential(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="webauthn_credentials")
    credential_id = models.BinaryField(unique=True, max_length=1024)
    public_key = models.BinaryField()
    sign_count = models.PositiveIntegerField(default=0)
    transports = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WebAuthnChallenge(models.Model):
    CEREMONY_CHOICES = [
        ("registration", "registration"),
        ("authentication", "authentication"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="webauthn_challenges")
    ceremony = models.CharField(max_length=32, choices=CEREMONY_CHOICES)
    challenge = models.BinaryField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "ceremony", "-created_at"]),
        ]
