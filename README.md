# WebAuth デモアプリ

Nuxt をフロントエンド、Django REST Framework をバックエンドにした WebAuthn（パスキー / Touch ID）認証のデモアプリです。  
登録（Attestation）と認証（Assertion）の両方をサーバー側で検証します。

## 機能
- パスキー登録（プラットフォーム認証器優先）
- パスキー認証（サーバー側検証）
- Touch ID 利用可否の判定表示
- 登録ユーザーの記憶（ローカル保存）

## 技術構成
- フロントエンド: Nuxt 4 / Vue 3
- バックエンド: Django 5 + Django REST Framework
- WebAuthn 検証: `webauthn`（duo-labs/py_webauthn）
- DB: SQLite（開発用）

## 主要エンドポイント（DRF）
- `POST /api/webauthn/register/options`  
  登録用 `publicKey` を発行（challenge を保存）
- `POST /api/webauthn/register/verify`  
  Attestation を検証し、公開鍵・credentialId・signCount を保存
- `POST /api/webauthn/login/options`  
  認証用 `publicKey` を発行
- `POST /api/webauthn/login/verify`  
  Assertion を検証し、signCount を更新

## ローカル起動

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

### Frontend
```bash
cd frontend
npm install
export NUXT_PUBLIC_WEBAUTHN_API_BASE=http://localhost:8000
npm run dev
```

## WebAuthn の前提
- WebAuthn は HTTPS または `localhost` でのみ有効です
- `WEBAUTHN_ORIGIN` / `WEBAUTHN_RP_ID` が実環境と一致している必要があります

## 設定（環境変数）
- `WEBAUTHN_RP_ID`（例: `localhost`）
- `WEBAUTHN_RP_NAME`（例: `Labo Auth`）
- `WEBAUTHN_ORIGIN`（例: `http://localhost:3000`）
- `NUXT_PUBLIC_WEBAUTHN_API_BASE`（例: `http://localhost:8000`）

## 内部処理の流れ（図解）

### 登録（Attestation）
```
ユーザー
  │ 1) 登録開始
  ▼
Frontend (Nuxt)
  │ 2) /register/options
  ▼
Backend (DRF)
  │ challenge生成・保存
  │ publicKeyOptions返却
  ▼
Frontend (Nuxt)
  │ navigator.credentials.create()
  │ 3) /register/verify (attestation送信)
  ▼
Backend (DRF)
  │ clientDataJSON/challenge/origin検証
  │ 公開鍵・credentialId・signCount保存
  ▼
完了
```

### ログイン（Assertion）
```
ユーザー
  │ 1) ログイン開始
  ▼
Frontend (Nuxt)
  │ 2) /login/options
  ▼
Backend (DRF)
  │ challenge生成・保存
  │ allowCredentials返却
  ▼
Frontend (Nuxt)
  │ navigator.credentials.get()
  │ 3) /login/verify (assertion送信)
  ▼
Backend (DRF)
  │ signature検証・signCount更新
  ▼
ログイン成功
```

## パスワードログインと併用する場合のおすすめ
- まずは **パスワード + WebAuthn の二段階**（ステップアップ認証）で安全性を高める
- パスワード成功後に WebAuthn を必須にする、または信頼済みデバイスのみ省略
- WebAuthn 失敗時のフォールバックは「パスワード再入力 + 追加確認（メールOTP等）」に限定
- `credentialId` はユーザー単位で複数保持し、端末追加に対応
- 既存のパスワードハッシュ（PBKDF2/Argon2/Bcrypt）と併存する設計にする
- UI は「パスワード / パスキー」どちらも選べる導線にし、移行を段階的に進める
