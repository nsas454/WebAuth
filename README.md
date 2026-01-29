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
- **注意**: `WEBAUTHN_ORIGIN` はスキーム/ホスト/ポートまで一致が必要、`WEBAUTHN_RP_ID` はホスト名のみを設定します
- **記述例**:
  - 開発: `WEBAUTHN_ORIGIN=http://localhost:3000` / `WEBAUTHN_RP_ID=localhost`
  - 本番: `WEBAUTHN_ORIGIN=https://example.com` / `WEBAUTHN_RP_ID=example.com`

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

## 用語解説
- **WebAuthn**: ブラウザ標準の公開鍵認証API。パスキーや生体認証を扱う
- **Passkey（パスキー）**: WebAuthn で使う鍵ペア。秘密鍵は端末内に安全保管される
- **RP (Relying Party)**: 認証を提供する側。`WEBAUTHN_RP_ID` がドメインになる
- **Challenge**: 一度きりの乱数。リプレイ攻撃を防ぐために毎回生成される
- **Attestation**: 登録時の証明データ。認証器の情報と公開鍵を含む
- **Assertion**: ログイン時の署名データ。保存済み公開鍵で検証する
- **credentialId**: 認証器で発行される資格情報ID（サーバーはこれで鍵を識別）
- **signCount**: 署名カウンタ。複製や巻き戻しの検知に使う

## ログイン時にDBへ保存するもの
- **必須**: `signCount` の更新（クローン検知のため単調増加を確認）
- **必須**: `challenge` の削除/無効化（使い捨て）
- **任意**: 最終ログイン時刻・IP・User-Agent などの監査ログ
- **任意**: 失敗回数やロック状態（ブルートフォース対策）

## シングルサインオン（SSO）を実現するには
- **IdP を導入**（例: Keycloak / Auth0 / Azure AD / Okta）
- **標準プロトコルを採用**: OAuth 2.0 / OpenID Connect を推奨（SAML も可）
- **WebAuthn は IdP 側の認証手段として組み込む**  
  各アプリは IdP 発行のトークン（ID/Access Token）を検証する
- **セッション管理を統一**: 失効・更新（Refresh）・ログアウト連携
- **アプリ間のユーザー識別子を統一**（sub/uid を基準にする）

## 標準的なSSO構成（詳細）
推奨は **OIDC Authorization Code + PKCE** です。  
IdP は自分のドメインでセッション Cookie を持ち、アプリ側は `code` を交換してトークンを取得します。

### 1) ログイン開始〜認可コード取得
1. アプリ → IdP にリダイレクト  
   `response_type=code`, `client_id`, `redirect_uri`, `scope=openid profile`, `code_challenge`
2. IdP で認証（パスワード/MFA/WebAuthnなど）  
   認証結果は **IdP ドメインの HttpOnly Cookie** に保存
3. IdP → アプリへ **`code` を付与してリダイレクト**

### 2) トークン交換〜アプリのセッション確立
4. アプリのバックエンドが IdP に `code` を送信（PKCE の `code_verifier` を添付）
5. IdP が **ID Token / Access Token / Refresh Token** を発行
6. アプリ側で **自前セッションCookieを発行**（またはトークン検証のみで運用）

### 3) 推奨される実装ポイント
- **トークンをURLに載せてリダイレクトしない**（`code` を使う）
- **IdP の Cookie とアプリの Cookie は分離**（ドメイン別に管理）
- **トークン検証はサーバー側**（公開鍵/JWKSで署名検証）
- **ログアウト連携**（IdPのセッション失効とアプリのセッション破棄）

## セッションタイムアウト時のトークン（JWT）
- **アクセストークンは期限切れで無効**になり、API は 401 を返す
- **リフレッシュトークンが有効なら再発行**、期限切れなら再ログイン
- **リフレッシュはローテーション/失効**を推奨（漏洩対策）
