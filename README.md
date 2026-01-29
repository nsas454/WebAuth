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
