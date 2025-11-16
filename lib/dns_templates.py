"""Reusable DNS templates for bulk operations."""
from __future__ import annotations

from dataclasses import dataclass, field
import secrets
import string
from typing import Callable, Dict, List, Any, Optional


ALPHABET = string.ascii_lowercase + string.digits


@dataclass
class TemplateResult:
    """Represents a set of DNS records generated for a domain."""

    records: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateDefinition:
    """Metadata wrapper for DNS templates."""

    name: str
    description: str
    generator: Callable[[str], TemplateResult]


def _generate_random_label(min_length: int = 30) -> str:
    """Generate a random lowercase alphanumeric label."""

    length = max(min_length, 30)
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def generate_tempererror_chain(
    domain: str,
    *,
    chain_depth: int = 4,
    min_label_length: int = 32,
    final_content: str = "v=spf1 include:_spf.AUTUMNWINDZ.COM ~all",
) -> TemplateResult:
    """Create the Cloudflare Tempererror SPF TXT chain for a domain.

    Args:
        domain: 대상 도메인.
        chain_depth: `_spf` 이후 거칠 랜덤 서브도메인 수. 1 이하이면 `_spf`
            레코드가 바로 최종 include 레코드가 된다.
        min_label_length: 랜덤 서브도메인 최소 길이.
    """

    chain_depth = max(0, int(chain_depth))
    random_labels: List[str] = []
    while len(random_labels) < chain_depth:
        candidate = _generate_random_label(min_label_length)
        if candidate not in random_labels:
            random_labels.append(candidate)

    wildcard_redirect = f"_spf.{domain}."
    records: List[Dict[str, Any]] = [
        {
            "type": "TXT",
            "name": "*",
            "content": f"v=spf1 redirect={wildcard_redirect}",
            "ttl": 600,
            "notes": "Tempererror wildcard redirect",
        }
    ]

    final_content = final_content.strip() or "v=spf1 include:_spf.AUTUMNWINDZ.COM ~all"

    if random_labels:
        # _spf redirects into the first random label
        records.append(
            {
                "type": "TXT",
                "name": "_spf",
                "content": f"v=spf1 redirect={random_labels[0]}.{domain}.",
                "ttl": 600,
                "notes": "Tempererror chain hop",
            }
        )

        for idx in range(len(random_labels) - 1):
            records.append(
                {
                    "type": "TXT",
                    "name": random_labels[idx],
                    "content": f"v=spf1 redirect={random_labels[idx + 1]}.{domain}.",
                    "ttl": 600,
                    "notes": "Tempererror chain hop",
                }
            )

        records.append(
            {
                "type": "TXT",
                "name": random_labels[-1],
                "content": final_content,
                "ttl": 600,
                "notes": "Tempererror final stage",
            }
        )
    else:
        # Direct include without additional hops
        records.append(
            {
                "type": "TXT",
                "name": "_spf",
                "content": final_content,
                "ttl": 600,
                "notes": "Tempererror direct include",
            }
        )

    metadata = {
        "template": "Tempererror SPF",
        "tempererror_chain": random_labels,
        "wildcard_target": wildcard_redirect,
        "hop_count": chain_depth,
        "final_content": final_content,
    }
    return TemplateResult(records=records, metadata=metadata)


DNS_TEMPLATES: Dict[str, TemplateDefinition] = {
    "tempererror": TemplateDefinition(
        name="Tempererror SPF",
        description=(
            "Cloudflare Tempererror 스타일 SPF TXT 체인을 생성하여 "
            "모든 서브도메인을 _spf 하위 체인으로 리디렉션합니다."
        ),
        generator=generate_tempererror_chain,
    )
}


def get_template(name: str) -> Optional[TemplateDefinition]:
    """Return the template definition for the given name if it exists."""

    return DNS_TEMPLATES.get(name)


def list_templates() -> List[TemplateDefinition]:
    """Return all registered DNS templates."""

    return list(DNS_TEMPLATES.values())
