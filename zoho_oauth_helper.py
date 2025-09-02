"""Zoho OAuth helper to generate authorization URL and exchange code for tokens.

Usage examples:

1) Generate an authorization URL (open it in a browser, log in, authorize):

   uv run python zoho_oauth_helper.py --make-auth-url \
     --scopes "ZohoProjects.projects.READ,ZohoProjects.portals.READ,\
       ZohoWorkDrive.files.READ,ZohoWorkDrive.files.CREATE"

   After authorizing, Zoho will redirect to your configured redirect URI with a
   `code` parameter. Copy that code.

2) Exchange the authorization code for tokens (prints refresh token):

   uv run python zoho_oauth_helper.py --exchange-code "<PASTE_CODE_HERE>"

Environment variables expected in .env:
- ZOHO_CLIENT_ID
- ZOHO_CLIENT_SECRET
- ZOHO_REDIRECT_URI
- Optional: ZOHO_ACCOUNTS_BASE (default: https://accounts.zoho.com)

Note: Ensure your app in Zoho Developer Console has the same redirect URI and
that you request offline access with user consent to receive a refresh token.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.parse

import requests
from dotenv import load_dotenv


def _require_env(name: str) -> str:
    """Return required environment variable or exit with a clear message.

    Args:
        name: The environment variable name to retrieve.

    Returns:
        The environment variable value.
    """
    val = os.environ.get(name)
    if not val:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return val


def _normalize_scopes(raw: str) -> str:
    """Normalize scopes string from env/args.

    - Removes backslashes used for line continuations in .env
    - Converts commas to spaces
    - Collapses any whitespace/newlines
    """
    cleaned = raw.replace("\\", " ").replace(",", " ")
    return " ".join(cleaned.split())


def make_auth_url(scopes: str) -> str:
    """Build the Zoho OAuth authorization URL.

    Args:
        scopes: Comma-separated Zoho scopes, e.g.
            "ZohoProjects.projects.READ,ZohoWorkDrive.files.READ".

    Returns:
        A URL string to open in the browser.
    """
    accounts_base = os.environ.get("ZOHO_ACCOUNTS_BASE", "https://accounts.zoho.com")
    client_id = _require_env("ZOHO_CLIENT_ID")
    redirect_uri = _require_env("ZOHO_REDIRECT_URI")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        # Ensure a refresh token is issued
        "access_type": "offline",
        # Force consent to ensure refresh token issuance
        "prompt": "consent",
    }
    return f"{accounts_base}/oauth/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict[str, str]:
    """Exchange an authorization code for access and refresh tokens.

    Args:
        code: The `code` query parameter returned to your redirect URI.

    Returns:
        Dict with keys: access_token, refresh_token, expires_in, token_type, ...
    """
    accounts_base = os.environ.get("ZOHO_ACCOUNTS_BASE", "https://accounts.zoho.com")
    client_id = _require_env("ZOHO_CLIENT_ID")
    client_secret = _require_env("ZOHO_CLIENT_SECRET")
    redirect_uri = _require_env("ZOHO_REDIRECT_URI")

    url = f"{accounts_base}/oauth/v2/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    resp = requests.post(url, data=data, timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        print(f"Zoho token endpoint error {resp.status_code}: {resp.text}", file=sys.stderr)
        raise
    return resp.json()


def main() -> None:
    """CLI entrypoint to generate auth URL or exchange code for tokens."""
    load_dotenv()

    PRESET_SCOPES = {
        # Comprehensive Zoho Projects/Bugtracker/Sheet access as requested
        "projects-full": (
            "ZohoProjects.portals.ALL "
            "ZohoProjects.projects.ALL "
            "ZohoProjects.activities.READ "
            "ZohoProjects.status.READ "
            "ZohoProjects.status.CREATE "
            "ZohoProjects.milestones.ALL "
            "ZohoProjects.tasklists.ALL "
            "ZohoProjects.tasks.ALL "
            "ZohoProjects.timesheets.ALL "
            "ZohoProjects.bugs.ALL "
            "ZohoProjects.events.ALL "
            "ZohoProjects.forums.ALL "
            "ZohoProjects.users.ALL "
            "ZohoProjects.search.READ "
            "ZohoProjects.clients.ALL "
            "ZohoProjects.documents.ALL "
            "ZohoPC.files.ALL "
            "ZohoBugtracker.portals.READ "
            "ZohoBugtracker.projects.ALL "
            "ZohoBugtracker.milestones.ALL "
            "ZohoBugtracker.timesheets.ALL "
            "ZohoBugtracker.bugs.ALL "
            "ZohoBugtracker.events.ALL "
            "ZohoBugtracker.forums.ALL "
            "ZohoBugtracker.users.ALL "
            "ZohoBugtracker.search.READ "
            "ZohoBugtracker.documents.ALL "
            "ZohoBugtracker.tags.READ "
            "ZohoSheet.dataAPI.READ "
            "ZohoProjects.custom_fields.ALL "
            "ZohoProjects.documents.READ "
            "WorkDrive.team.ALL "
            "WorkDrive.workspace.ALL "
            "WorkDrive.files.ALL"
        ),
    }

    # Defaults and environment
    DEFAULT_SCOPES = (
        "ZohoProjects.projects.READ,ZohoProjects.portals.READ,"
        "ZohoWorkDrive.files.READ,ZohoWorkDrive.files.CREATE"
    )
    env_scopes = os.environ.get("ZOHO_SCOPES")

    parser = argparse.ArgumentParser(description="Zoho OAuth helper")
    parser.add_argument(
        "--make-auth-url",
        action="store_true",
        help="Print the authorization URL to initiate OAuth flow.",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESET_SCOPES.keys()),
        help="Use a predefined scope set (overrides --scopes).",
    )
    parser.add_argument(
        "--scopes",
        default=DEFAULT_SCOPES,
        help="Comma-separated Zoho scopes (highest precedence).",
    )
    parser.add_argument(
        "--exchange-code",
        metavar="CODE",
        help="Exchange the given authorization code for tokens.",
    )

    args = parser.parse_args()

    if args.make_auth_url:
        # Precedence: --scopes > --preset > ZOHO_SCOPES > DEFAULT_SCOPES
        if args.scopes and args.scopes != DEFAULT_SCOPES:
            scope_str = args.scopes
        elif args.preset:
            scope_str = PRESET_SCOPES[args.preset]
        elif env_scopes:
            scope_str = env_scopes
        else:
            scope_str = DEFAULT_SCOPES
        url = make_auth_url(_normalize_scopes(scope_str))
        print("Open this URL in your browser to authorize the app:\n")
        print(url)
        print(
            "\nAfter authorization, copy the `code` param from your redirect URI "
            "and run:\n"
            "uv run python zoho_oauth_helper.py --exchange-code '<CODE>'\n"
        )
        return

    if args.exchange_code:
        tokens = exchange_code_for_tokens(args.exchange_code)
        refresh = tokens.get("refresh_token")
        access = tokens.get("access_token")
        print("Tokens response:\n")
        print(tokens)
        if refresh:
            print(
                "\nYour ZOHO_REFRESH_TOKEN (add this to your .env):\n\n"
                f'ZOHO_REFRESH_TOKEN="{refresh}"\n'
            )
        else:
            print(
                "\nNo refresh_token returned. Ensure you used access_type=offline "
                "and prompt=consent, and that the app is not already authorized "
                "without forcing consent."
            )
        if access:
            print("Note: access_token expires; use refresh_token for long-term access.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
