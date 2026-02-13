import json
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .models import WebAuthnChallenge, WebAuthnCredential, WebAuthnUser

_VALID_TRANSPORTS = {e.value: e for e in AuthenticatorTransport}


def _to_transport_enums(transports):
    """DB に保存された文字列（または文字列のリスト）を AuthenticatorTransport のリストに変換する。"""
    if transports is None:
        return None
    if isinstance(transports, str):
        transports = [transports]
    if not transports:
        return None
    out = [_VALID_TRANSPORTS[t] for t in transports if isinstance(t, str) and t in _VALID_TRANSPORTS]
    return out if out else None


def _get_username(request):
    username = str(request.data.get("username", "")).strip()
    return username


def _get_or_create_user(username):
    user, _ = User.objects.get_or_create(username=username)
    profile, created = WebAuthnUser.objects.get_or_create(user=user)
    if created or not profile.webauthn_user_id:
        profile.webauthn_user_id = secrets.token_bytes(16)
        profile.save(update_fields=["webauthn_user_id"])
    return user, profile


def _store_challenge(user, ceremony, challenge):
    WebAuthnChallenge.objects.filter(user=user, ceremony=ceremony).delete()
    return WebAuthnChallenge.objects.create(user=user, ceremony=ceremony, challenge=challenge)


def _load_challenge(user, ceremony):
    return (
        WebAuthnChallenge.objects.filter(user=user, ceremony=ceremony)
        .order_by("-created_at")
        .first()
    )


class RegisterOptionsView(APIView):
    def post(self, request):
        username = _get_username(request)
        if not username:
            return Response({"error": "username is required"}, status=status.HTTP_400_BAD_REQUEST)

        user, profile = _get_or_create_user(username)
        exclude_credentials = [
            PublicKeyCredentialDescriptor(
                id=cred.credential_id,
                type=PublicKeyCredentialType.PUBLIC_KEY,
                transports=_to_transport_enums(cred.transports),
            )
            for cred in WebAuthnCredential.objects.filter(user=user)
        ]

        challenge = secrets.token_bytes(32)
        options = generate_registration_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            rp_name=settings.WEBAUTHN_RP_NAME,
            user_id=profile.webauthn_user_id,
            user_name=username,
            user_display_name=username,
            challenge=challenge,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                # 未指定: スマホ・Bluetooth(BLE)・USBキー等を認証機として利用可能に
                authenticator_attachment=None,
                # ディスカバラブル認証情報: 他デバイス（スマホ等）から「パスキーでサインイン」で利用可能
                resident_key=ResidentKeyRequirement.REQUIRED,
            ),
            exclude_credentials=exclude_credentials,
        )

        _store_challenge(user, "registration", challenge)
        public_key = json.loads(options_to_json(options))
        return Response({"publicKey": public_key})


class RegisterVerifyView(APIView):
    def post(self, request):
        username = _get_username(request)
        credential = request.data.get("credential")
        if not username or not credential:
            return Response({"error": "username and credential are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "user not found"}, status=status.HTTP_404_NOT_FOUND)

        challenge_record = _load_challenge(user, "registration")
        if not challenge_record:
            return Response({"error": "challenge not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=challenge_record.challenge,
                expected_origin=settings.WEBAUTHN_ORIGIN,
                expected_rp_id=settings.WEBAUTHN_RP_ID,
                require_user_verification=True,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        transports = []
        response = credential.get("response") if isinstance(credential, dict) else None
        if isinstance(response, dict):
            transports = response.get("transports") or []

        with transaction.atomic():
            WebAuthnCredential.objects.update_or_create(
                user=user,
                credential_id=verification.credential_id,
                defaults={
                    "public_key": verification.credential_public_key,
                    "sign_count": verification.sign_count,
                    "transports": transports,
                },
            )
            challenge_record.delete()

        return Response({"status": "ok"})


class LoginOptionsView(APIView):
    def post(self, request):
        username = _get_username(request)
        if not username:
            return Response({"error": "username is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "user not found"}, status=status.HTTP_404_NOT_FOUND)

        credentials = list(WebAuthnCredential.objects.filter(user=user))
        if not credentials:
            return Response({"error": "credential not found"}, status=status.HTTP_404_NOT_FOUND)

        allow_credentials = [
            PublicKeyCredentialDescriptor(
                id=cred.credential_id,
                type=PublicKeyCredentialType.PUBLIC_KEY,
                transports=_to_transport_enums(cred.transports),
            )
            for cred in credentials
        ]

        challenge = secrets.token_bytes(32)
        options = generate_authentication_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            challenge=challenge,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.REQUIRED,
        )

        _store_challenge(user, "authentication", challenge)
        public_key = json.loads(options_to_json(options))
        return Response({"publicKey": public_key})


class LoginVerifyView(APIView):
    def post(self, request):
        username = _get_username(request)
        credential = request.data.get("credential")
        if not username or not credential:
            return Response({"error": "username and credential are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "user not found"}, status=status.HTTP_404_NOT_FOUND)

        challenge_record = _load_challenge(user, "authentication")
        if not challenge_record:
            return Response({"error": "challenge not found"}, status=status.HTTP_400_BAD_REQUEST)

        raw_id = None
        if isinstance(credential, dict):
            raw_id = credential.get("rawId") or credential.get("id")
        if not raw_id:
            return Response({"error": "credential id missing"}, status=status.HTTP_400_BAD_REQUEST)

        credential_id = base64url_to_bytes(raw_id)
        try:
            stored = WebAuthnCredential.objects.get(user=user, credential_id=credential_id)
        except WebAuthnCredential.DoesNotExist:
            return Response({"error": "credential not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=challenge_record.challenge,
                expected_rp_id=settings.WEBAUTHN_RP_ID,
                expected_origin=settings.WEBAUTHN_ORIGIN,
                credential_public_key=stored.public_key,
                credential_current_sign_count=stored.sign_count,
                require_user_verification=True,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        stored.sign_count = verification.new_sign_count
        stored.save(update_fields=["sign_count"])
        challenge_record.delete()

        return Response({"status": "ok"})
