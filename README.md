# Finalized Session Switcher

This folder contains the complete **multi-session Telegram upload/download** toolset with the following files:

- **`session_switcher.py`** — Interactive menu to switch between accounts, upload, and download.
- **`session_manager.py`** — Backend logic for managing multiple account `.session` files.
- **`uploader_multi_session.py`** — Upload tool supporting multiple stored sessions.
- **`uploader.py`** — Single-session uploader.
- **`downloder.py`** — Single-session downloader *(filename retains original spelling)*.

---

## 1. Getting Your API Credentials

To use these tools, you must have a `.env.local` file in the **project root** with your Telegram API credentials.

### Steps to Get API_ID and API_HASH:
1. Go to **[https://my.telegram.org](https://my.telegram.org)** in your browser.
2. Log in with your phone number.
3. Enter the OTP code sent to your official Telegram app.
4. Click **API Development Tools**.
5. If you have no app created yet:
   - Fill out **App Title** (any name, e.g., `MyUploader`).
   - Short Name (e.g., `uploader`).
   - Select Platform: `Desktop`.
   - Click **Create Application**.
6. Note down **App api_id** and **App api_hash** displayed.

---

## 2. Creating `.env.local` File

In your project root (`TGDUS/`), create a file named `.env.local` with:

```
API_ID=123456
API_HASH=abcdef1234567890abcdef1234567890
```

Replace with the **API_ID** and **API_HASH** you got from step 1.

---

## 3. Running the Session Switcher

### Initial Run:
```bash
python session_switcher.py
```
- On first login, you will be prompted for your phone number.
- A Telegram OTP will be sent to your account — enter it.
- If Two Factor Authentication is enabled, you’ll be prompted for your password.
- The session will be saved in the `sessions/` folder and you will not need to log in again for that account.

---

## 4. Features in Session Switcher Menu
- **Upload files** — using your currently active Telegram account.
- **Download files** — using your currently active account.
- **Switch between accounts** — choose from any stored sessions.
- **Add new account** — log in with new credentials and store it.
- **Manage sessions** — delete, rename, or view existing sessions.

---

## 5. Notes
- Protect your `.session` files as they contain credentials.
- API credentials and session files are account-specific — keep them secure.

- You can use **multiple accounts** without re-login by switching sessions.
