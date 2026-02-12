# Django REST Framework WebAuthn API

## セットアップ（ローカル）

**要約: Python 3.10 以上**（Django 5.x のため）。pyenv 利用時は `python3.12 -m venv .venv` などで作成してください。

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

## Admin 画面
```bash
python manage.py createsuperuser
```

`http://localhost:8000/admin/` にアクセスしてログインします。

## 環境変数（.env）
`backend/.env` に設定できます。サンプルは `backend/.env.example` です。

### Nuxt 連携

`NUXT_PUBLIC_WEBAUTHN_API_BASE=http://localhost:8000` を指定してください。

### WebAuthn 設定（任意）

```bash
export WEBAUTHN_RP_ID=localhost
export WEBAUTHN_ORIGIN=http://localhost:3000
export WEBAUTHN_RP_NAME="Labo Auth"
```
