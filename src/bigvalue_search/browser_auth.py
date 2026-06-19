"""Playwright browser automation for BigValue.ai login and JWT extraction."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Self

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from bigvalue_search.config import config
from bigvalue_search.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

SIGN_IN_URL: str = f"{config.BIGVALUE_API_BASE}/sign-in"
TOKEN_CACHE_FILE: Path = Path(__file__).resolve().parents[2] / ".token_cache.json"


@dataclass
class AuthResult:
    """Result of authentication attempt."""

    jwt_token: str = ""
    access_token: str = ""  # JWT accessToken from /api/auth/session
    success: bool = False
    error: str = ""
    cookies: dict[str, str] = field(default_factory=dict)


class BrowserSession:
    """Manages an active Playwright browser session with login state."""

    def __init__(
        self,
        page: Page,
        context: BrowserContext,
        browser: Browser,
        playwright_instance: object,
        jwt_token: str = "",
        access_token: str = "",
        cookies: dict[str, str] | None = None,
    ) -> None:
        self.page = page
        self.context = context
        self.browser = browser
        self._playwright = playwright_instance
        self.jwt_token = jwt_token
        self.access_token = access_token
        self.cookies = cookies or {}

    def close(self) -> None:
        """Close the browser and clean up."""
        try:
            self.browser.close()
        except Exception:
            pass
        try:
            self._playwright.stop()  # type: ignore[union-attr]
        except Exception:
            pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _save_token_cache(auth: AuthResult) -> None:
    """Cache token to disk."""
    try:
        TOKEN_CACHE_FILE.write_text(json.dumps({
            "jwt_token": auth.jwt_token,
            "access_token": auth.access_token,
            "cookies": auth.cookies,
        }, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to save token cache: %s", e)


def _load_token_cache() -> AuthResult | None:
    """Load cached token if it exists."""
    if not TOKEN_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
        if data.get("jwt_token") or data.get("access_token"):
            return AuthResult(
                jwt_token=data.get("jwt_token", ""),
                access_token=data.get("access_token", ""),
                success=True,
                cookies=data.get("cookies", {}),
            )
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load token cache: %s", e)
    return None


def _fill_form_field(page: Page, selectors: list[str], value: str, field_name: str) -> bool:
    """Try to fill a form field using multiple selectors.

    Args:
        page: Playwright page
        selectors: CSS selectors to try
        value: Value to fill
        field_name: Name for logging

    Returns:
        True if field was filled successfully.
    """
    for selector in selectors:
        try:
            elem = page.wait_for_selector(selector, timeout=3000)
            if elem and elem.is_visible():
                elem.fill(value)
                logger.info("Filled %s field with selector: %s", field_name, selector)
                return True
        except Exception:
            continue
    logger.warning("Could not find %s input field", field_name)
    return False


def _click_button(page: Page, selectors: list[str]) -> bool:
    """Try to click a button using multiple selectors.

    Args:
        page: Playwright page
        selectors: CSS selectors to try

    Returns:
        True if button was clicked successfully.
    """
    for selector in selectors:
        try:
            elem = page.wait_for_selector(selector, timeout=3000)
            if elem and elem.is_visible():
                elem.click()
                logger.info("Clicked button with selector: %s", selector)
                return True
        except Exception:
            continue
    return False


def _extract_token_from_page(page: Page, context: BrowserContext) -> tuple[str, str]:
    """Extract JWT/access token from the page.

    Tries multiple sources in order:
    1. /api/auth/session via JS fetch
    2. localStorage
    3. sessionStorage
    4. Cookies

    Args:
        page: Playwright page
        context: Browser context

    Returns:
        Tuple of (jwt_token, access_token).
    """
    jwt_token = ""
    access_token = ""

    # 1. Try /api/auth/session
    try:
        session_data = page.evaluate('''async () => {
            const resp = await fetch('/api/auth/session');
            const data = await resp.json();
            return data;
        }''')
        if isinstance(session_data, dict) and "accessToken" in session_data:
            token = session_data["accessToken"]
            if token and len(token) > 20:
                access_token = token
                logger.info("Extracted accessToken from /api/auth/session via JS")
                return jwt_token, access_token
    except Exception as e:
        logger.debug("Failed to fetch /api/auth/session: %s", e)

    # 2. Try localStorage
    for key in ["token", "access_token", "jwt", "auth_token", "accessToken"]:
        try:
            token = page.evaluate(f"localStorage.getItem('{key}')")
            if token and len(token) > 20:
                jwt_token = token
                logger.info("Extracted token from localStorage key: %s", key)
                return jwt_token, access_token
        except Exception:
            continue

    # 3. Try sessionStorage
    for key in ["token", "access_token", "jwt", "auth_token", "accessToken"]:
        try:
            token = page.evaluate(f"sessionStorage.getItem('{key}')")
            if token and len(token) > 20:
                jwt_token = token
                logger.info("Extracted token from sessionStorage key: %s", key)
                return jwt_token, access_token
        except Exception:
            continue

    # 4. Try cookies
    cookies = context.cookies()
    for cookie in cookies:
        if "token" in cookie["name"].lower() or "jwt" in cookie["name"].lower():
            if len(cookie["value"]) > 20:
                jwt_token = cookie["value"]
                logger.info("Extracted token from cookie: %s", cookie["name"])
                return jwt_token, access_token

    return jwt_token, access_token


EMAIL_SELECTORS: list[str] = [
    'input[type="email"]',
    'input[name="email"]',
    'input[id*="email"]',
    'input[placeholder*="email" i]',
    'input[placeholder*="이메일"]',
    'input[type="text"]',
]

PASSWORD_SELECTORS: list[str] = [
    'input[type="password"]',
    'input[name="password"]',
    'input[id*="password"]',
    'input[placeholder*="password" i]',
    'input[placeholder*="비밀번호"]',
]

LOGIN_BUTTON_SELECTORS: list[str] = [
    'button[type="submit"]',
    'button:has-text("로그인")',
    'button:has-text("Login")',
    'button:has-text("Sign in")',
    'button:has-text("Sign In")',
    'input[type="submit"]',
]


def login_with_playwright(
    email: str | None = None,
    password: str | None = None,
    headless: bool | None = None,
    use_cache: bool = True,
) -> AuthResult:
    """
    Login to BigValue.ai using Playwright browser automation.

    Extracts the JWT Bearer token from browser's localStorage/sessionStorage
    or intercepted network requests after login.

    Args:
        email: Login email (defaults to config)
        password: Login password (defaults to config)
        headless: Run browser headlessly (defaults to config)
        use_cache: Whether to use cached token

    Returns:
        AuthResult with JWT token if successful.
    """
    if use_cache:
        cached = _load_token_cache()
        if cached and cached.success:
            logger.info("Using cached JWT token")
            return cached

    email = email or config.BIGVALUE_EMAIL
    password = password or config.BIGVALUE_PASSWORD
    headless = headless if headless is not None else config.HEADLESS

    if not email or not password:
        return AuthResult(error="Email and password are required")

    auth_result = AuthResult()
    captured_tokens: list[str] = []
    captured_access_tokens: list[str] = []

    logger.info("Launching browser for BigValue login...")

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=headless)
        context: BrowserContext = browser.new_context()
        page: Page = context.new_page()

        # Intercept network requests to capture JWT token
        def handle_request(request: object) -> None:
            auth_header = request.headers.get("authorization", "")  # type: ignore[union-attr]
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                if token not in captured_tokens:
                    captured_tokens.append(token)
                    logger.info("Captured JWT token from network request")

        # Intercept responses to capture accessToken from /api/auth/session
        def handle_response(response: object) -> None:
            try:
                url = response.url  # type: ignore[union-attr]
                if "/api/auth/session" in url and response.status == 200:  # type: ignore[union-attr]
                    ct = response.headers.get("content-type", "")  # type: ignore[union-attr]
                    if "json" in ct:
                        data = response.json()  # type: ignore[union-attr]
                        if isinstance(data, dict) and "accessToken" in data:
                            token = data["accessToken"]
                            if token and len(token) > 20:
                                captured_access_tokens.append(token)
                                logger.info("Captured accessToken from /api/auth/session (length: %d)", len(token))
            except Exception:
                pass

        page.on("request", handle_request)
        page.on("response", handle_response)

        try:
            # Navigate to sign-in page
            logger.info("Navigating to %s", SIGN_IN_URL)
            page.goto(SIGN_IN_URL, timeout=config.BROWSER_TIMEOUT)
            page.wait_for_load_state("networkidle", timeout=config.BROWSER_TIMEOUT)

            # Fill login form
            _fill_form_field(page, EMAIL_SELECTORS, email, "email")
            _fill_form_field(page, PASSWORD_SELECTORS, password, "password")

            # Click login button
            if not _click_button(page, LOGIN_BUTTON_SELECTORS):
                logger.warning("Could not find login button, trying Enter key")
                page.keyboard.press("Enter")

            # Wait for navigation/response after login
            try:
                page.wait_for_load_state("networkidle", timeout=config.BROWSER_TIMEOUT)
            except Exception:
                page.wait_for_timeout(5000)

            # Try to extract token from various sources
            # 1. From captured accessToken from /api/auth/session (preferred)
            if captured_access_tokens:
                auth_result.access_token = captured_access_tokens[-1]
                auth_result.success = True
                logger.info("Using accessToken from /api/auth/session")

            # 2. From captured network requests
            if not auth_result.access_token and captured_tokens:
                auth_result.jwt_token = captured_tokens[-1]
                auth_result.success = True

            # 3. Try extracting from page
            if not auth_result.access_token:
                jwt_token, access_token = _extract_token_from_page(page, context)
                if access_token:
                    auth_result.access_token = access_token
                    auth_result.success = True
                elif jwt_token:
                    auth_result.jwt_token = jwt_token
                    auth_result.success = True

            # 4. Try cookies
            if not auth_result.jwt_token and not auth_result.access_token:
                cookies = context.cookies()
                auth_result.cookies = {c["name"]: c["value"] for c in cookies}
                for cookie in cookies:
                    if "token" in cookie["name"].lower() or "jwt" in cookie["name"].lower():
                        if len(cookie["value"]) > 20:
                            auth_result.jwt_token = cookie["value"]
                            auth_result.success = True
                            logger.info("Extracted token from cookie: %s", cookie["name"])
                            break

            if not auth_result.jwt_token and not auth_result.access_token:
                auth_result.error = "Could not extract JWT token after login"
                logger.error(auth_result.error)
            else:
                _save_token_cache(auth_result)

        except Exception as e:
            auth_result.error = f"Login failed: {e}"
            logger.error("Login failed: %s", e)
        finally:
            browser.close()

    return auth_result


def login_keep_browser(
    email: str | None = None,
    password: str | None = None,
    headless: bool | None = None,
    use_cache: bool = True,
) -> BrowserSession | None:
    """
    Login to BigValue.ai and return an active BrowserSession.

    Unlike login_with_playwright(), this keeps the browser open for
    further interaction (navigation, searching, data extraction).

    Args:
        email: Login email (defaults to config)
        password: Login password (defaults to config)
        headless: Run browser headlessly (defaults to config)
        use_cache: Whether to use cached token (token will still be validated)

    Returns:
        BrowserSession if successful, None if login failed.
    """
    email = email or config.BIGVALUE_EMAIL
    password = password or config.BIGVALUE_PASSWORD
    headless = headless if headless is not None else config.HEADLESS

    if not email or not password:
        logger.error("Email and password are required")
        return None

    captured_tokens: list[str] = []
    captured_access_tokens: list[str] = []

    logger.info("Launching browser for BigValue login (keeping open)...")

    pw = sync_playwright().start()
    browser: Browser = pw.chromium.launch(headless=headless)
    context: BrowserContext = browser.new_context()
    page: Page = context.new_page()

    # Intercept network requests to capture JWT token
    def handle_request(request: object) -> None:
        auth_header = request.headers.get("authorization", "")  # type: ignore[union-attr]
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token not in captured_tokens:
                captured_tokens.append(token)
                logger.info("Captured JWT token from network request")

    # Intercept responses to capture accessToken from /api/auth/session
    def handle_response(response: object) -> None:
        try:
            url = response.url  # type: ignore[union-attr]
            if "/api/auth/session" in url and response.status == 200:  # type: ignore[union-attr]
                ct = response.headers.get("content-type", "")  # type: ignore[union-attr]
                if "json" in ct:
                    data = response.json()  # type: ignore[union-attr]
                    if isinstance(data, dict) and "accessToken" in data:
                        token = data["accessToken"]
                        if token and len(token) > 20:
                            captured_access_tokens.append(token)
                            logger.info("Captured accessToken from /api/auth/session (length: %d)", len(token))
        except Exception:
            pass

    page.on("request", handle_request)
    page.on("response", handle_response)

    try:
        # Navigate to sign-in page
        logger.info("Navigating to %s", SIGN_IN_URL)
        page.goto(SIGN_IN_URL, timeout=config.BROWSER_TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=config.BROWSER_TIMEOUT)

        # Fill login form
        _fill_form_field(page, EMAIL_SELECTORS, email, "email")
        _fill_form_field(page, PASSWORD_SELECTORS, password, "password")

        # Click login button
        if not _click_button(page, LOGIN_BUTTON_SELECTORS):
            logger.warning("Could not find login button, trying Enter key")
            page.keyboard.press("Enter")

        # Wait for navigation/response after login
        logger.info("Waiting for post-login redirect...")
        time.sleep(8)

        try:
            page.wait_for_load_state("networkidle", timeout=config.BROWSER_TIMEOUT)
        except Exception:
            pass

        # If still on sign-in page, wait a bit more
        if "sign-in" in page.url:
            logger.info("Still on sign-in page, waiting for redirect...")
            time.sleep(5)

        logger.info("Post-login URL: %s", page.url)

        # Extract JWT token
        jwt_token = ""
        access_token = ""

        # 1. From captured accessToken from /api/auth/session (preferred)
        if captured_access_tokens:
            access_token = captured_access_tokens[-1]
            logger.info("Using accessToken from /api/auth/session")

        # 2. From captured network request Bearer tokens
        if not access_token and captured_tokens:
            jwt_token = captured_tokens[-1]

        # 3. Try extracting from page
        if not access_token:
            extracted_jwt, extracted_access = _extract_token_from_page(page, context)
            if extracted_access:
                access_token = extracted_access
            elif extracted_jwt:
                jwt_token = extracted_jwt

        cookie_dict = {c["name"]: c["value"] for c in context.cookies()}

        if not jwt_token and not access_token:
            logger.error("Could not extract JWT token after login")
            browser.close()
            pw.stop()
            return None

        # Cache the token
        _save_token_cache(AuthResult(
            jwt_token=jwt_token,
            access_token=access_token,
            success=True,
            cookies=cookie_dict,
        ))

        return BrowserSession(
            page=page,
            context=context,
            browser=browser,
            playwright_instance=pw,
            jwt_token=jwt_token,
            access_token=access_token,
            cookies=cookie_dict,
        )

    except Exception as e:
        logger.error("Login failed: %s", e)
        browser.close()
        pw.stop()
        return None


def clear_token_cache() -> None:
    """Remove cached token file."""
    if TOKEN_CACHE_FILE.exists():
        TOKEN_CACHE_FILE.unlink()
        logger.info("Token cache cleared")
