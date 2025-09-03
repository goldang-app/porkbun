"""Porkbun DNS API Client"""
import json
import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class RecordType(Enum):
    """DNS record types supported by Porkbun"""
    A = "A"
    AAAA = "AAAA"
    MX = "MX"
    CNAME = "CNAME"
    ALIAS = "ALIAS"
    TXT = "TXT"
    NS = "NS"
    SRV = "SRV"
    TLSA = "TLSA"
    CAA = "CAA"
    HTTPS = "HTTPS"
    SVCB = "SVCB"


@dataclass
class DNSRecord:
    """DNS Record data structure"""
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    ttl: Optional[int] = None
    prio: Optional[int] = None
    notes: Optional[str] = None


class PorkbunDNS:
    """Porkbun DNS API client"""
    
    BASE_URL = "https://api.porkbun.com/api/json/v3"
    
    def __init__(self, api_key: str, secret_api_key: str):
        """Initialize Porkbun DNS client
        
        Args:
            api_key: Your Porkbun API key
            secret_api_key: Your Porkbun secret API key
        """
        self.api_key = api_key
        self.secret_api_key = secret_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _get_auth(self) -> Dict[str, str]:
        """Get authentication payload"""
        return {
            "apikey": self.api_key,
            "secretapikey": self.secret_api_key
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        # Add authentication to data
        if data is None:
            data = {}
        data.update(self._get_auth())
        
        # 디버그 모드: 네임서버 업데이트 요청일 때 데이터 출력
        if "updateNs" in endpoint:
            print(f"[DEBUG] 네임서버 업데이트 요청:")
            print(f"  URL: {url}")
            print(f"  데이터: {data}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data
            )
            
            # 500 에러 시 응답 본문 확인
            if response.status_code == 500:
                print(f"[DEBUG] 500 에러 응답:")
                print(f"  Status Code: {response.status_code}")
                print(f"  Headers: {response.headers}")
                try:
                    error_body = response.text
                    print(f"  Response Body: {error_body[:500]}")  # 처음 500자만 출력
                except:
                    pass
            
            # Try to get JSON response even if status is not OK
            try:
                result = response.json()
            except:
                response.raise_for_status()
                raise Exception(f"Invalid response from API")
            
            # Check for API error in response
            if result.get("status") == "ERROR":
                error_message = result.get('message', 'Unknown error')
                # Common error messages in Korean
                if "API keys" in error_message:
                    raise Exception(f"API 인증 오류: API 키를 확인해주세요")
                elif "not enabled for API access" in error_message or "not opted in to API access" in error_message:
                    domain_name = endpoint.split('/')[-1]
                    raise Exception(f"❌ 도메인 '{domain_name}'에 대한 API 접근이 비활성화되어 있습니다.\n\n"
                                  f"✅ 해결 방법:\n"
                                  f"1. https://porkbun.com 에 로그인\n"
                                  f"2. Domain Management 페이지로 이동\n"
                                  f"3. '{domain_name}' 도메인 클릭\n"
                                  f"4. Details 탭에서 'API ACCESS' 섹션 찾기\n"
                                  f"5. 'API ACCESS' 토글을 ON으로 변경\n"
                                  f"6. 변경사항 저장 후 이 프로그램 새로고침")
                else:
                    raise Exception(f"API 오류: {error_message}")
            
            # If status code is not OK but we got JSON, show the message
            if not response.ok:
                response.raise_for_status()
            
            return result
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_msg = error_json.get('message', str(e))
                    if "not enabled for API access" in error_msg:
                        domain = endpoint.split('/')[-1]
                        raise Exception(f"도메인 '{domain}'에 대한 API 접근이 활성화되지 않았습니다.\nPorkbun 웹사이트 > Domain Management > {domain} > Settings에서 'API Access'를 ON으로 설정해주세요.")
                    raise Exception(f"API 요청 실패: {error_msg}")
                except:
                    pass
            raise Exception(f"Request failed: {str(e)}")
    
    def ping(self) -> bool:
        """Test API connection
        
        Returns:
            True if connection successful
        """
        try:
            result = self._make_request("POST", "/ping")
            return result.get("status") == "SUCCESS"
        except Exception:
            return False
    
    def get_domains(self) -> List[Dict[str, Any]]:
        """Get list of all domains
        
        Returns:
            List of domain information
        """
        result = self._make_request("POST", "/domain/listAll")
        return result.get("domains", [])
    
    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """Get detailed information about a specific domain
        
        Args:
            domain: Domain name
            
        Returns:
            Domain information including lock status
        """
        try:
            # Porkbun doesn't have a direct domain info endpoint, 
            # but we can check nameservers to validate domain access
            nameservers = self.get_nameservers(domain)
            return {
                "status": "SUCCESS",
                "domain": domain,
                "nameservers": nameservers,
                "api_access": True
            }
        except Exception as e:
            error_msg = str(e)
            if "not enabled for API access" in error_msg or "API 접근이 비활성화" in error_msg:
                return {
                    "status": "ERROR",
                    "domain": domain,
                    "api_access": False,
                    "error": "API access not enabled"
                }
            else:
                return {
                    "status": "ERROR", 
                    "domain": domain,
                    "error": error_msg
                }
    
    def check_domain_api_access(self, domain: str) -> bool:
        """Check if domain has API access enabled
        
        Args:
            domain: Domain name to check
            
        Returns:
            True if API access is enabled, False otherwise
        """
        try:
            # Try to get DNS records - if it works, API access is enabled
            self.get_dns_records(domain)
            return True
        except Exception as e:
            error_msg = str(e)
            if "API 접근이 비활성화" in error_msg or "not opted in" in error_msg.lower():
                return False
            # If it's a different error, we assume API access is enabled
            return True
    
    def get_nameservers(self, domain: str) -> List[str]:
        """Get current nameservers for a domain
        
        Args:
            domain: Domain name
            
        Returns:
            List of nameserver hostnames
        """
        result = self._make_request("POST", f"/domain/getNs/{domain}")
        return result.get("ns", [])
    
    def update_nameservers(self, domain: str, nameservers: List[str]) -> Dict[str, Any]:
        """Update nameservers for a domain
        
        Args:
            domain: Domain name
            nameservers: List of nameserver hostnames
            
        Returns:
            API response
        """
        # 빈 네임서버 필터링 및 검증
        valid_nameservers = []
        for ns in nameservers:
            if ns and ns.strip():  # 빈 문자열 제거
                ns_clean = ns.strip()  # 대소문자 그대로 유지
                # 기본적인 네임서버 형식 검증
                if '.' in ns_clean and len(ns_clean) > 3:
                    valid_nameservers.append(ns_clean)
        
        if not valid_nameservers:
            # 네임서버가 비어있으면 Porkbun 기본 네임서버 사용 제안
            raise Exception("네임서버가 비어있습니다!\n\n"
                          "Porkbun 기본 네임서버를 사용하시겠습니까?\n"
                          "- curitiba.ns.porkbun.com\n"
                          "- fortaleza.ns.porkbun.com\n"
                          "- maceio.ns.porkbun.com\n"
                          "- salvador.ns.porkbun.com")
        
        # 최소 2개의 네임서버 필요
        if len(valid_nameservers) < 2:
            raise Exception("최소 2개 이상의 네임서버가 필요합니다.")
        
        # Porkbun API는 ns 배열 형식을 사용
        data = {
            "ns": valid_nameservers[:10]  # 최대 10개
        }
        
        try:
            return self._make_request("POST", f"/domain/updateNs/{domain}", data)
        except Exception as e:
            error_msg = str(e)
            # 500 에러에 대한 상세 메시지 처리
            if "500" in error_msg or "Internal Server Error" in error_msg:
                # 현재 네임서버 상태 확인 제안
                print("\n[DEBUG] 네임서버 업데이트 500 에러 발생")
                print(f"시도한 네임서버: {valid_nameservers}")
                
                raise Exception(f"네임서버 업데이트 실패 (500 Internal Server Error)\n\n"
                              f"입력한 네임서버: {', '.join(valid_nameservers)}\n\n"
                              f"해결 방법:\n"
                              f"1. 웹사이트에서 현재 네임서버가 비어있는지 확인:\n"
                              f"   https://porkbun.com/account/domainsSpeedy?domain={domain}\n\n"
                              f"2. 네임서버가 비어있다면, 먼저 Porkbun 기본값으로 설정:\n"
                              f"   - curitiba.ns.porkbun.com\n"
                              f"   - fortaleza.ns.porkbun.com\n"
                              f"   - maceio.ns.porkbun.com\n"
                              f"   - salvador.ns.porkbun.com\n\n"
                              f"3. 그 다음 원하는 네임서버로 변경")
            raise
    
    def get_default_nameservers(self) -> List[str]:
        """Get Porkbun's default nameservers
        
        Returns:
            List of Porkbun's default nameserver hostnames
        """
        # Porkbun's default nameservers
        return [
            "curitiba.ns.porkbun.com",
            "fortaleza.ns.porkbun.com",
            "maceio.ns.porkbun.com",
            "salvador.ns.porkbun.com"
        ]
    
    def is_using_porkbun_nameservers(self, nameservers: List[str]) -> bool:
        """Check if domain is using Porkbun's nameservers
        
        Args:
            nameservers: List of current nameserver hostnames
            
        Returns:
            True if using Porkbun nameservers
        """
        porkbun_ns = self.get_default_nameservers()
        # Check if all nameservers are Porkbun's
        for ns in nameservers:
            if not any(porkbun in ns.lower() for porkbun in ["porkbun.com"]):
                return False
        return len(nameservers) > 0
    
    def get_dns_records(self, domain: str) -> List[Dict[str, Any]]:
        """Retrieve all DNS records for a domain
        
        Args:
            domain: Domain name
            
        Returns:
            List of DNS records
        """
        result = self._make_request("POST", f"/dns/retrieve/{domain}")
        return result.get("records", [])
    
    def get_dns_record_by_type(self, domain: str, record_type: str, subdomain: str = "") -> List[Dict[str, Any]]:
        """Retrieve DNS records by type and subdomain
        
        Args:
            domain: Domain name
            record_type: DNS record type (A, CNAME, etc.)
            subdomain: Subdomain (optional, empty for root)
            
        Returns:
            List of matching DNS records
        """
        endpoint = f"/dns/retrieveByNameType/{domain}/{record_type}"
        if subdomain:
            endpoint += f"/{subdomain}"
        
        result = self._make_request("POST", endpoint)
        return result.get("records", [])
    
    def create_dns_record(self, 
                         domain: str,
                         record_type: str,
                         content: str,
                         name: str = "",
                         ttl: int = 600,
                         prio: Optional[int] = None,
                         notes: Optional[str] = None) -> Dict[str, Any]:
        """Create a new DNS record
        
        Args:
            domain: Domain name
            record_type: DNS record type (A, CNAME, etc.)
            content: Record content/value
            name: Subdomain (optional, empty for root)
            ttl: Time to live in seconds (minimum 600)
            prio: Priority (for MX records)
            notes: Optional notes
            
        Returns:
            API response
        """
        data = {
            "type": record_type,
            "content": content,
            "ttl": str(ttl)
        }
        
        if name:
            data["name"] = name
        if prio is not None:
            data["prio"] = str(prio)
        if notes:
            data["notes"] = notes
        
        return self._make_request("POST", f"/dns/create/{domain}", data)
    
    def edit_dns_record(self,
                       domain: str,
                       record_id: str,
                       record_type: str,
                       content: str,
                       name: str = "",
                       ttl: int = 600,
                       prio: Optional[int] = None,
                       notes: Optional[str] = None) -> Dict[str, Any]:
        """Edit an existing DNS record by ID
        
        Args:
            domain: Domain name
            record_id: Record ID to edit
            record_type: DNS record type
            content: Record content/value
            name: Subdomain (optional)
            ttl: Time to live in seconds
            prio: Priority (for MX records)
            notes: Optional notes
            
        Returns:
            API response
        """
        data = {
            "type": record_type,
            "content": content,
            "ttl": str(ttl)
        }
        
        if name:
            data["name"] = name
        if prio is not None:
            data["prio"] = str(prio)
        if notes:
            data["notes"] = notes
        
        return self._make_request("POST", f"/dns/edit/{domain}/{record_id}", data)
    
    def edit_dns_record_by_type(self,
                                domain: str,
                                record_type: str,
                                subdomain: str,
                                content: str,
                                ttl: int = 600,
                                prio: Optional[int] = None,
                                notes: Optional[str] = None) -> Dict[str, Any]:
        """Edit DNS records by type and subdomain
        
        Args:
            domain: Domain name
            record_type: DNS record type
            subdomain: Subdomain to edit
            content: New record content
            ttl: Time to live in seconds
            prio: Priority (for MX records)
            notes: Optional notes
            
        Returns:
            API response
        """
        endpoint = f"/dns/editByNameType/{domain}/{record_type}"
        if subdomain:
            endpoint += f"/{subdomain}"
        
        data = {
            "content": content,
            "ttl": str(ttl)
        }
        
        if prio is not None:
            data["prio"] = str(prio)
        if notes:
            data["notes"] = notes
        
        return self._make_request("POST", endpoint, data)
    
    def delete_dns_record(self, domain: str, record_id: str) -> Dict[str, Any]:
        """Delete a DNS record by ID
        
        Args:
            domain: Domain name
            record_id: Record ID to delete
            
        Returns:
            API response
        """
        return self._make_request("POST", f"/dns/delete/{domain}/{record_id}")
    
    def delete_dns_record_by_type(self, domain: str, record_type: str, subdomain: str = "") -> Dict[str, Any]:
        """Delete DNS records by type and subdomain
        
        Args:
            domain: Domain name
            record_type: DNS record type
            subdomain: Subdomain (optional)
            
        Returns:
            API response
        """
        endpoint = f"/dns/deleteByNameType/{domain}/{record_type}"
        if subdomain:
            endpoint += f"/{subdomain}"
        
        return self._make_request("POST", endpoint)
    
    def bulk_delete_records(self, domain: str, record_ids: List[str]) -> List[Dict[str, Any]]:
        """Delete multiple DNS records
        
        Args:
            domain: Domain name
            record_ids: List of record IDs to delete
            
        Returns:
            List of deletion results
        """
        results = []
        for record_id in record_ids:
            try:
                result = self.delete_dns_record(domain, record_id)
                results.append({"id": record_id, "status": "SUCCESS", "result": result})
            except Exception as e:
                results.append({"id": record_id, "status": "ERROR", "error": str(e)})
        return results
    
    def export_dns_records(self, domain: str, format: str = "json") -> str:
        """Export DNS records in various formats
        
        Args:
            domain: Domain name
            format: Export format ('json', 'zone', 'csv')
            
        Returns:
            Formatted DNS records
        """
        records = self.get_dns_records(domain)
        
        if format == "json":
            return json.dumps(records, indent=2)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            if records:
                writer = csv.DictWriter(output, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
            return output.getvalue()
        elif format == "zone":
            zone_lines = []
            for record in records:
                name = record.get("name", "@")
                ttl = record.get("ttl", 600)
                record_type = record.get("type", "")
                content = record.get("content", "")
                prio = record.get("prio", "")
                
                if record_type == "MX" and prio:
                    zone_lines.append(f"{name}\t{ttl}\tIN\t{record_type}\t{prio} {content}")
                else:
                    zone_lines.append(f"{name}\t{ttl}\tIN\t{record_type}\t{content}")
            return "\n".join(zone_lines)
        else:
            raise ValueError(f"Unsupported format: {format}")