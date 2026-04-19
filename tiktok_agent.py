#!/usr/bin/env python3
"""TikTok Streak Keeper — Playwright-based automation for maintaining DM streaks."""

import os, time, json, datetime, threading

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, "tiktok_session")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

_pw_lock = threading.Lock()

# ─── Browser Context ──────────────────────────────────────────────────────────

def _open_context():
    if not HAS_PLAYWRIGHT:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        )
    os.makedirs(SESSION_DIR, exist_ok=True)
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        SESSION_DIR,
        headless=False,
        args=["--start-maximized"],
        no_viewport=True,
    )
    return pw, ctx

# ─── Setup / Login ────────────────────────────────────────────────────────────

def setup_tiktok_session():
    """Open TikTok in a browser. Waits up to 3 min for the user to log in, then saves session."""
    pw, ctx = _open_context()
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded")
    print("[tiktok] Please log in. Waiting up to 3 minutes...")
    try:
        page.wait_for_url(lambda url: "/login" not in url, timeout=180_000)
        print("[tiktok] Login detected — session saved.")
    except PWTimeout:
        print("[tiktok] Login timed out — session may still be saved.")
    ctx.close()
    pw.stop()
    return "TikTok session saved. You won't need to log in again."

# ─── Streak Detection ─────────────────────────────────────────────────────────

def _get_page_width(page):
    try:
        return page.evaluate("window.innerWidth") or 1280
    except Exception:
        return 1280

def get_streak_conversations(page):
    """Return list of {username, index} for DM conversations that show a 🔥 streak."""
    page.goto("https://www.tiktok.com/messages", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    # Each conversation in the list is a clickable item.
    # We look for items that contain the fire emoji anywhere inside them.
    streaks = []
    try:
        # TikTok renders conversation items; we grab all of them then filter
        # by whether they contain 🔥 text anywhere inside.
        conv_sels = [
            "[data-e2e='dm-conversation-item']",
            "li[class*='conversation']",
            "div[class*='conversation-item']",
            "div[class*='ConversationItem']",
        ]
        convs = []
        for sel in conv_sels:
            items = page.locator(sel).all()
            if items:
                convs = items
                break

        if not convs:
            # Broad fallback: grab all sizeable divs in the left panel
            convs = [
                d for d in page.locator("div").all()
                if (b := d.bounding_box()) and 150 < b["width"] < 450 and b["height"] > 40
            ]

        for i, conv in enumerate(convs):
            try:
                html = conv.inner_html(timeout=500)
                if "🔥" not in html:
                    continue
                # Extract display name: first text chunk that isn't just a number or emoji
                name = ""
                for sel in ["[class*='name']", "[class*='nick']", "[class*='user']", "span", "p"]:
                    try:
                        candidates = conv.locator(sel).all()
                        for c in candidates:
                            t = c.inner_text(timeout=300).strip()
                            if t and "🔥" not in t and not t.isdigit() and len(t) < 60:
                                name = t
                                break
                        if name:
                            break
                    except Exception:
                        pass
                streaks.append({"username": name or f"streak_{i}", "index": i, "locator": conv})
            except Exception as e:
                print(f"[tiktok] streak item parse error: {e}")
    except Exception as e:
        print(f"[tiktok] get_streak_conversations error: {e}")

    print(f"[tiktok] Found {len(streaks)} streak conversation(s)")
    return streaks

# ─── Conversation Analysis ────────────────────────────────────────────────────

def analyze_conversation(page, conv_locator):
    """
    Click into a conversation and determine who still needs to send today.
    Returns: 'user_needs_to_send' | 'other_needs_to_send' | 'both_sent' | 'neither_sent'
    """
    try:
        conv_locator.click()
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"[tiktok] Failed to open conversation: {e}")
        return "both_sent"  # safe default — do nothing

    user_sent  = False
    other_sent = False

    try:
        pw = _get_page_width(page)

        # Find the Y position of the "Today" date separator so we only look at today's messages
        sep_y = 0
        for sep_text in ["Today", "today", "Dzisiaj"]:  # add more locales if needed
            try:
                sep_box = page.get_by_text(sep_text).last.bounding_box()
                if sep_box:
                    sep_y = sep_box["y"]
                    break
            except Exception:
                pass

        # Try known TikTok message selectors first
        msg_sels = [
            "[data-e2e='chat-message-container']",
            "[class*='message-item']",
            "[class*='MessageItem']",
            "[class*='chat-item']",
        ]
        messages = []
        for sel in msg_sels:
            items = page.locator(sel).all()
            if len(items) > 1:
                messages = items
                break

        if not messages:
            # Broad fallback: collect all reasonably-sized divs below sep_y
            all_divs = page.locator("div").all()
            messages = [
                d for d in all_divs
                if (b := d.bounding_box())
                and b["y"] > sep_y
                and 20 < b["width"] < pw * 0.75
                and b["height"] > 12
            ]

        for msg in messages[-30:]:
            try:
                box = msg.bounding_box()
                if not box or box["y"] < sep_y:
                    continue
                text = msg.inner_text(timeout=300).strip()
                if not text:
                    continue
                # Messages whose centre is in the right half = sent by user
                centre_x = box["x"] + box["width"] / 2
                if centre_x > pw * 0.5:
                    user_sent = True
                else:
                    other_sent = True
                if user_sent and other_sent:
                    break
            except Exception:
                pass

    except Exception as e:
        print(f"[tiktok] analyze error: {e}")

    print(f"[tiktok] user_sent={user_sent}, other_sent={other_sent}")

    if user_sent and other_sent:       return "both_sent"
    if user_sent and not other_sent:   return "other_needs_to_send"
    if not user_sent and other_sent:   return "user_needs_to_send"
    return "neither_sent"

# ─── Actions ──────────────────────────────────────────────────────────────────

def share_fyp_video(page, target_username):
    """Share the 2nd FYP video to target_username via DM."""
    try:
        page.goto("https://www.tiktok.com", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        # Find share buttons — TikTok uses data-e2e="share-icon" on the FYP
        share_sels = [
            "[data-e2e='share-icon']",
            "[class*='share-icon']",
            "button[aria-label*='share' i]",
            "[class*='ShareButton']",
        ]
        share_btns = []
        for sel in share_sels:
            share_btns = page.locator(sel).all()
            if len(share_btns) >= 2:
                break

        if len(share_btns) < 2:
            # Scroll down to load a 2nd video and try again
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(2500)
            for sel in share_sels:
                share_btns = page.locator(sel).all()
                if len(share_btns) >= 2:
                    break

        if len(share_btns) < 2:
            print("[tiktok] Could not find 2nd FYP share button")
            return False

        share_btns[1].click()
        page.wait_for_timeout(2000)

        # Click the DM / "Send to friends" option in the share sheet
        for dm_sel in [
            "text=Send to friends",
            "text=Direct message",
            "[aria-label*='message' i]",
            "[class*='dm']",
            "[data-e2e*='dm']",
        ]:
            try:
                page.locator(dm_sel).first.click(timeout=3000)
                page.wait_for_timeout(1500)
                break
            except Exception:
                pass

        # Search for the target username
        for search_sel in [
            "input[placeholder*='earch']",
            "[data-e2e*='search']",
            "input[type='text']",
        ]:
            try:
                page.locator(search_sel).first.fill(target_username, timeout=3000)
                page.wait_for_timeout(1500)
                break
            except Exception:
                pass

        # Click the matching user result
        page.get_by_text(target_username).first.click(timeout=5000)
        page.wait_for_timeout(1000)

        # Click Send
        for send_sel in [
            "text=Send",
            "[data-e2e*='send']",
            "button[class*='send' i]",
        ]:
            try:
                page.locator(send_sel).first.click(timeout=3000)
                page.wait_for_timeout(1000)
                break
            except Exception:
                pass

        print(f"[tiktok] Shared FYP video to {target_username}")
        return True

    except Exception as e:
        print(f"[tiktok] share_fyp_video error: {e}")
        return False


def send_dm_message(page, target_username, text):
    """Open the DM conversation with target_username and send text."""
    try:
        page.goto("https://www.tiktok.com/messages", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Find and click the conversation
        page.get_by_text(target_username).first.click(timeout=5000)
        page.wait_for_timeout(2000)

        # Find the message input (TikTok uses a contenteditable div)
        sent = False
        for input_sel in [
            "[data-e2e='message-input']",
            "div[contenteditable='true']",
            "textarea",
        ]:
            try:
                inp = page.locator(input_sel).first
                inp.click(timeout=2000)
                inp.fill(text)
                page.wait_for_timeout(400)
                page.keyboard.press("Enter")
                page.wait_for_timeout(800)
                sent = True
                break
            except Exception:
                pass

        if not sent:
            # Last resort: click in the middle-bottom of the chat area and type
            vp = page.viewport_size or {"width": 1280, "height": 800}
            page.mouse.click(vp["width"] * 0.6, vp["height"] * 0.9)
            page.wait_for_timeout(500)
            page.keyboard.type(text)
            page.keyboard.press("Enter")
            page.wait_for_timeout(800)

        print(f"[tiktok] Sent '{text}' to {target_username}")
        return True

    except Exception as e:
        print(f"[tiktok] send_dm_message error: {e}")
        return False

# ─── Main Orchestrator ────────────────────────────────────────────────────────

def run_streak_check():
    """
    Called once at end of day by Jarvis scheduler (or manually on request).
    Checks all active TikTok streaks and takes action where needed.
    Returns a short summary string for Jarvis to speak.
    """
    if not HAS_PLAYWRIGHT:
        return ("Playwright is not installed, sir. "
                "Run: pip install playwright and playwright install chromium")

    actions = []
    errors  = []
    pw = ctx = None

    try:
        with _pw_lock:
            pw, ctx = _open_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            # Check login state
            page.goto("https://www.tiktok.com/messages", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            if "/login" in page.url:
                ctx.close(); pw.stop()
                return "Not logged in to TikTok, sir. Say 'set up TikTok' to log in first."

            streaks = get_streak_conversations(page)
            if not streaks:
                ctx.close(); pw.stop()
                return "No active TikTok streaks found."

            for streak in streaks:
                uname  = streak["username"]
                status = analyze_conversation(page, streak["locator"])
                print(f"[tiktok] {uname}: {status}")

                if status in ("user_needs_to_send", "neither_sent"):
                    ok = share_fyp_video(page, uname)
                    actions.append(f"sent video to {uname}" if ok else f"video to {uname} FAILED")
                    if not ok:
                        errors.append(uname)

                if status in ("other_needs_to_send", "neither_sent"):
                    ok = send_dm_message(page, uname, "passa!")
                    actions.append(f"nudged {uname}" if ok else f"nudge to {uname} FAILED")
                    if not ok:
                        errors.append(uname)

                # Go back to the messages list for the next streak
                try:
                    page.goto("https://www.tiktok.com/messages", wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)
                except Exception:
                    pass

            ctx.close()
            pw.stop()

    except Exception as e:
        try:
            if ctx: ctx.close()
            if pw:  pw.stop()
        except Exception:
            pass
        return f"Streak check hit a snag, sir: {e}"

    if not actions:
        return f"All {len(streaks)} streak(s) are safe — no action needed."
    return "; ".join(actions) + "."
