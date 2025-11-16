"""Background worker for bulk DNS operations."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Callable, List, Dict, Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from lib.porkbun_dns import PorkbunDNS
from lib.dns_templates import TemplateResult


@dataclass
class DomainJobResult:
    """Represents the outcome of a bulk DNS job for a single domain."""

    domain: str
    success: bool = False
    created_records: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    backup_path: str | None = None
    deleted_records: List[Dict[str, Any]] = field(default_factory=list)


class BulkDNSWorker(QThread):
    """QThread worker that applies DNS templates across multiple domains."""

    progress = pyqtSignal(int, int, str)  # current, total, message
    completed = pyqtSignal(list)  # List[DomainJobResult as dict]
    failed = pyqtSignal(str)

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        domains: List[str],
        generator: Callable[[str], TemplateResult],
        job_label: str,
        backup_dir: str | Path = "backups",
        delete_types: Optional[List[str]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.api_key = api_key
        self.secret_key = secret_key
        self.domains = domains
        self.generator = generator
        self.job_label = job_label
        self.backup_dir = Path(backup_dir)
        self.delete_types = delete_types or []

    def _ensure_backup_dir(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _write_backup(self, domain: str, records: List[Dict[str, Any]]) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        backup_path = self.backup_dir / f"{timestamp}_{domain}.log"
        with open(backup_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
        return backup_path

    def run(self):
        if not self.domains:
            self.completed.emit([])
            return

        try:
            client = PorkbunDNS(self.api_key, self.secret_key)
        except Exception as exc:  # pragma: no cover - critical failure
            self.failed.emit(str(exc))
            return

        self._ensure_backup_dir()
        total = len(self.domains)
        results: List[Dict[str, Any]] = []

        for index, domain in enumerate(self.domains, start=1):
            result = DomainJobResult(domain=domain)
            try:
                self.progress.emit(index - 1, total, f"{domain} 백업 중...")
                records = client.get_dns_records(domain)
                backup_path = self._write_backup(domain, records)
                result.backup_path = str(backup_path)

                if self.delete_types:
                    deleted = []
                    for existing in records:
                        if existing.get("type") in self.delete_types:
                            record_id = existing.get("id")
                            if not record_id:
                                continue
                            response = client.delete_dns_record(domain, record_id)
                            if response.get("status") != "SUCCESS":
                                raise Exception(
                                    f"{existing.get('type')} 삭제 실패: {existing.get('name', '@')}"
                                )
                            deleted.append(
                                {
                                    "id": record_id,
                                    "name": existing.get("name", "@"),
                                    "content": existing.get("content", ""),
                                    "type": existing.get("type"),
                                }
                            )
                    result.deleted_records = deleted

                template_payload = self.generator(domain)
                result.metadata = template_payload.metadata
                record_requests = template_payload.records
                if not record_requests:
                    raise ValueError("생성할 DNS 레코드가 없습니다.")

                for request in record_requests:
                    ttl = max(int(request.get("ttl", 600)), 600)
                    response = client.create_dns_record(
                        domain=domain,
                        record_type=request["type"],
                        content=request["content"],
                        name=request.get("name", ""),
                        ttl=ttl,
                        prio=request.get("prio"),
                        notes=request.get("notes"),
                    )
                    if response.get("status") != "SUCCESS":
                        raise Exception(response.get("message", "API 오류"))

                    result.created_records.append(
                        {
                            "type": request["type"],
                            "name": request.get("name") or "@",
                            "content": request.get("content", ""),
                        }
                    )

                result.success = True
            except Exception as exc:  # Continue with other domains
                result.errors.append(str(exc))

            results.append(asdict(result))
            self.progress.emit(index, total, f"{domain} 처리 완료")

        self.completed.emit(results)
