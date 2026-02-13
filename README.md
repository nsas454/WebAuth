# WebAuth デモアプリ

Nuxt をフロントエンド、Django REST Framework をバックエンドにした WebAuthn（パスキー / Touch ID）認証のデモアプリです。  
登録（Attestation）と認証（Assertion）の両方をサーバー側で検証します。

## 機能
- パスキー登録・認証（サーバー側検証）
- **スマホ・Bluetooth（BLE）を認証機として利用可能**（プラットフォーム認証器に限定しない）
- **PC に認証機がなくてもスマホを認証機として利用可能**（「デバイスからパスキーを選ぶ」＝ディスカバラブル認証）
- ディスカバラブル認証情報（resident key）対応で、他デバイスから「パスキーでサインイン」可能
- Touch ID / 認証機利用可否の表示
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
- `POST /api/webauthn/login/options/discoverable`  
  ユーザー名不要で認証用 options を発行（allow_credentials なし → ブラウザが全パスキーを提示）
- `POST /api/webauthn/login/verify/discoverable`  
  assertion のみで検証し、userHandle からユーザーを特定して `username` を返す

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
- スマホ/ngrok 用（任意）: `ALLOWED_HOSTS_EXTRA`（カンマ区切り）, `CORS_EXTRA_ORIGINS`（カンマ区切り）

## スマホ・Bluetooth（BLE）で認証する

スマホでパスキー認証や Bluetooth（BLE）対応の認証デバイスを使うには、**HTTPS** が必要です（WebAuthn の仕様）。  
ここでは **スマホのフロントから、PC で動かしている Backend（localhost:8000）と連携する** 2 パターンを説明します。

---

### パターン1: スマホ × PC の localhost:8000（同一 LAN）

Backend は PC の **localhost:8000** のまま動かし、スマホは同一 Wi‑Fi から PC の IP で API にアクセスします。フロントだけ ngrok で HTTPS にします。

1. **PC の LAN IP を確認**  
   例: `192.168.1.10`（`ifconfig` / `ipconfig` で確認）

2. **フロントエンド用に ngrok でポート 3000 を公開**
   ```bash
   ngrok http 3000
   ```
   → 表示された HTTPS のホスト名を控える（例: `abc123.ngrok-free.app`）

3. **Backend を「すべてのインターフェース」で起動（localhost:8000 のまま）**
   ```bash
   cd backend
   source .venv/bin/activate
   python manage.py runserver 0.0.0.0:8000
   ```
   → PC の `localhost:8000` が同一 LAN 内のスマホから `http://<PCのIP>:8000` で届くようにします。

4. **Backend の環境変数**（`backend/.env`）
   ```bash
   WEBAUTHN_RP_ID=abc123.ngrok-free.app
   WEBAUTHN_ORIGIN=https://abc123.ngrok-free.app
   ALLOWED_HOSTS_EXTRA=192.168.1.10
   CORS_EXTRA_ORIGINS=https://abc123.ngrok-free.app
   ```
   → `ALLOWED_HOSTS_EXTRA` は **PC の LAN IP**（手順1で確認した値）に合わせてください。

5. **Frontend の環境変数（スマホから API を叩くとき）**  
   スマホのブラウザからは「PC の localhost」に届かないので、**API のベース URL を PC の IP にします**。
   ```bash
   NUXT_PUBLIC_WEBAUTHN_API_BASE=http://192.168.1.10:8000
   ```
   → `192.168.1.10` は手順1の PC の LAN IP に合わせてください。  
   → この状態で `npm run dev` を実行し、フロントは ngrok で公開された HTTPS の URL で開きます。

6. **スマホでアクセス**  
   スマホを同じ Wi‑Fi に繋ぎ、ブラウザで `https://abc123.ngrok-free.app` を開きます。  
   → フロントは ngrok（HTTPS）、API は PC の **localhost:8000**（= `http://<PCのIP>:8000`）と連携し、スマホの生体認証や BLE で登録・ログインできます。

---

### パターン2: フロント・バックともに ngrok（2 本トンネル）

1. **ngrok をインストール**  
   [ngrok](https://ngrok.com/) でアカウント取得後、フロント用・バックエンド用の 2 本のトンネルを張ります。

2. **フロントエンド用トンネル（例: ポート 3000）**
   ```bash
   ngrok http 3000
   ```
   → 表示された HTTPS のホスト名を控える（例: `abc123.ngrok-free.app`）

3. **バックエンド用トンネル（例: ポート 8000）**
   ```bash
   ngrok http 8000
   ```
   → 表示された HTTPS のホスト名を控える（例: `def456.ngrok-free.app`）

4. **Backend の環境変数**（`backend/.env`）
   ```bash
   WEBAUTHN_RP_ID=abc123.ngrok-free.app
   WEBAUTHN_ORIGIN=https://abc123.ngrok-free.app
   ALLOWED_HOSTS_EXTRA=def456.ngrok-free.app,abc123.ngrok-free.app
   CORS_EXTRA_ORIGINS=https://abc123.ngrok-free.app
   ```
   - `WEBAUTHN_RP_ID` / `WEBAUTHN_ORIGIN` は **フロントの HTTPS のホスト** に合わせます。
   - `ALLOWED_HOSTS_EXTRA` にフロント・バックの ngrok ホストをカンマ区切りで指定します。
   - `CORS_EXTRA_ORIGINS` にフロントの Origin（`https://フロントのホスト`）を指定します。

5. **Frontend の環境変数**
   ```bash
   NUXT_PUBLIC_WEBAUTHN_API_BASE=https://def456.ngrok-free.app
   ```
   → バックエンドの ngrok URL を指定して `npm run dev` を実行します。

6. **スマホでアクセス**  
   スマホのブラウザで `https://abc123.ngrok-free.app` を開き、登録・ログインを試します。
   - スマホ内蔵の生体認証（Touch ID / 顔認証など）や、Bluetooth（BLE）の認証デバイスが利用可能です。
   - 本アプリは認証器の種類を限定していないため、BLE トランスポートもそのまま利用できます。

---

### 補足
- 登録時に「このサイトではデバイスが利用できません」と出る場合は、**HTTPS** と **WEBAUTHN_ORIGIN / WEBAUTHN_RP_ID** がフロントの URL と一致しているか確認してください。
- BLE の認証キーを使う場合は、端末の Bluetooth をオンにし、キーがペアリング済みである必要があります。
- **パターン1** では Backend はあくまで PC の **localhost:8000** で動作し、スマホからは `http://<PCのIP>:8000` でそのまま連携します。

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
