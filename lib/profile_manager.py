"""Profile management utilities for multi-account support."""
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProfileManager:
    """Handles CRUD operations for saved API profiles."""

    def __init__(self):
        self.config_dir = Path.home() / ".porkbun_dns"
        self.profile_file = self.config_dir / "profiles.json"
        self.legacy_config_file = self.config_dir / "config.json"
        self.data: Dict[str, Any] = {
            "active_profile": None,
            "profiles": {}
        }
        self.load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def load(self):
        """Load profiles from disk and migrate legacy settings if needed."""
        if self.profile_file.exists():
            try:
                with open(self.profile_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
            except Exception:
                # Fall back to clean structure on error
                self.data = {
                    "active_profile": None,
                    "profiles": {}
                }

        if "profiles" not in self.data or not isinstance(self.data["profiles"], dict):
            self.data["profiles"] = {}

        if not self.data["profiles"]:
            self._maybe_migrate_legacy()

        # Ensure config dir exists and persist the structure so users can edit manually if needed
        self.save()

    def save(self):
        """Persist profile data to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------\n+    # CRUD operations
    # ------------------------------------------------------------------
    def list_profiles(self) -> List[Dict[str, str]]:
        profiles = []
        for profile_id, payload in self.data.get("profiles", {}).items():
            profiles.append({
                "id": profile_id,
                "label": payload.get("label", profile_id),
                "api_key": payload.get("api_key", ""),
                "secret_api_key": payload.get("secret_api_key", ""),
                "last_used_at": payload.get("last_used_at"),
                "created_at": payload.get("created_at")
            })
        # Sort by creation time or label for consistent UI ordering
        return sorted(
            profiles,
            key=lambda item: (item.get("created_at") or "", item.get("label", ""))
        )

    def get_profile(self, profile_id: str) -> Optional[Dict[str, str]]:
        return self.data.get("profiles", {}).get(profile_id)

    def get_active_profile_id(self) -> Optional[str]:
        active_id = self.data.get("active_profile")
        if active_id in self.data.get("profiles", {}):
            return active_id
        return None

    def set_active_profile(self, profile_id: Optional[str]):
        if profile_id and profile_id in self.data.get("profiles", {}):
            self.data["active_profile"] = profile_id
            self.data["profiles"][profile_id]["last_used_at"] = datetime.now().isoformat()
        else:
            self.data["active_profile"] = None
        self.save()

    def add_profile(self, label: str, api_key: str, secret_api_key: str) -> str:
        profile_id = self._generate_profile_id(label)
        timestamp = datetime.now().isoformat()
        self.data.setdefault("profiles", {})[profile_id] = {
            "label": label,
            "api_key": api_key,
            "secret_api_key": secret_api_key,
            "created_at": timestamp,
            "last_used_at": None
        }

        # First profile becomes active automatically
        if not self.data.get("active_profile"):
            self.data["active_profile"] = profile_id
        self.save()
        return profile_id

    def update_profile(self, profile_id: str, label: str, api_key: str, secret_api_key: str):
        if profile_id not in self.data.get("profiles", {}):
            return
        payload = self.data["profiles"][profile_id]
        payload.update({
            "label": label,
            "api_key": api_key,
            "secret_api_key": secret_api_key,
            "updated_at": datetime.now().isoformat()
        })
        self.save()

    def delete_profile(self, profile_id: str):
        if profile_id not in self.data.get("profiles", {}):
            return
        del self.data["profiles"][profile_id]
        if self.data.get("active_profile") == profile_id:
            self.data["active_profile"] = next(iter(self.data.get("profiles", {})), None)
        self.save()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _generate_profile_id(self, label: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9]+", "_", label.strip()) or "profile"
        unique_suffix = uuid.uuid4().hex[:6]
        candidate = f"{base.lower()}_{unique_suffix}"
        while candidate in self.data.get("profiles", {}):
            unique_suffix = uuid.uuid4().hex[:6]
            candidate = f"{base.lower()}_{unique_suffix}"
        return candidate

    def _maybe_migrate_legacy(self):
        """Create a default profile from legacy config or env vars."""
        # Legacy config.json had single api_key/secret_api_key entries
        legacy_data = None
        if self.legacy_config_file.exists():
            try:
                with open(self.legacy_config_file, "r", encoding="utf-8") as f:
                    legacy_data = json.load(f)
            except Exception:
                legacy_data = None

        api_key = None
        secret_key = None

        if isinstance(legacy_data, dict):
            api_key = legacy_data.get("api_key") or legacy_data.get("apikey")
            secret_key = legacy_data.get("secret_api_key") or legacy_data.get("secretapikey")

        if not api_key or not secret_key:
            api_key = os.getenv("PORKBUN_API_KEY")
            secret_key = os.getenv("PORKBUN_SECRET_API_KEY")

        if api_key and secret_key:
            self.add_profile("기본", api_key, secret_key)
