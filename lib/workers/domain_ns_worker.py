import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class DomainNSWorker(QObject):
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    check_completed = pyqtSignal(list)  # external_ns_domains
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.api_key = None
        self.api_secret = None
        self.config_file = Path("config/nameserver_config.json")
        self.is_checking = False
        self.rate_limit_delay = 0.5  # 500ms delay between requests
        self.batch_size = 5  # Process 5 domains at a time
        
    def set_credentials(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def load_config(self) -> Dict:
        """Load saved nameserver configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        return {
            "last_check": None,
            "external_ns_domains": [],
            "check_history": []
        }
    
    def save_config(self, config: Dict):
        """Save nameserver configuration"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def check_domain_ns(self, domain: str) -> Optional[Dict]:
        """Check nameserver for a single domain with retry logic"""
        url = f"https://api.porkbun.com/api/json/v3/domain/getNs/{domain}"
        data = {
            "secretapikey": self.api_secret,
            "apikey": self.api_key
        }
        
        max_retries = 3
        retry_delay = 2  # Start with 2 second delay
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "SUCCESS":
                        ns_list = result.get("ns", [])
                        # Check if any NS is not Porkbun's
                        porkbun_ns = ["curitiba.ns.porkbun.com", "fortaleza.ns.porkbun.com", 
                                    "maceio.ns.porkbun.com", "salvador.ns.porkbun.com"]
                        external_ns = [ns for ns in ns_list if ns not in porkbun_ns]
                        
                        if external_ns:
                            return {
                                "domain": domain,
                                "nameservers": ns_list,
                                "is_external": True
                            }
                        return {
                            "domain": domain,
                            "nameservers": ns_list,
                            "is_external": False
                        }
                elif response.status_code == 503:
                    # Service temporarily unavailable - wait and retry
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Max retries reached for {domain}")
                        return None
                else:
                    logger.error(f"API error for {domain}: {response.status_code}")
                    return None
            except requests.exceptions.Timeout:
                logger.error(f"Timeout checking {domain}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
            except Exception as e:
                logger.error(f"Error checking {domain}: {e}")
                return None
        
        return None
    
    def check_all_domains(self, domains: List[str]):
        """Check nameservers for all domains with rate limiting"""
        if self.is_checking:
            return
        
        self.is_checking = True
        external_ns_domains = []
        total = len(domains)
        current = 0
        
        try:
            # Process domains with ThreadPoolExecutor for parallel checking
            with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
                # Process in batches
                for i in range(0, total, self.batch_size):
                    batch = domains[i:i + self.batch_size]
                    
                    # Submit batch for parallel processing
                    futures = {executor.submit(self.check_domain_ns, domain): domain 
                             for domain in batch}
                    
                    # Collect results as they complete
                    for future in as_completed(futures):
                        domain = futures[future]
                        current += 1
                        self.progress_updated.emit(current, total, f"Checking {domain}...")
                        
                        try:
                            result = future.result(timeout=15)
                            if result:
                                if result["is_external"]:
                                    external_ns_domains.append({
                                        "domain": result["domain"],
                                        "nameservers": result["nameservers"]
                                    })
                                    logger.info(f"External NS found: {result['domain']} -> {result['nameservers']}")
                            else:
                                logger.warning(f"Failed to check {domain}")
                        except Exception as e:
                            logger.error(f"Error checking {domain}: {e}")
                        
                        # Rate limiting between requests
                        if current < total:
                            time.sleep(self.rate_limit_delay)
                    
                    # Additional delay between batches
                    if i + self.batch_size < total:
                        time.sleep(1)
            
            # Save results to config
            config = {
                "last_check": datetime.now().isoformat(),
                "external_ns_domains": external_ns_domains,
                "check_history": []
            }
            self.save_config(config)
            
            self.check_completed.emit(external_ns_domains)
            self.progress_updated.emit(total, total, "Check completed!")
            
        except Exception as e:
            logger.error(f"Error during domain check: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.is_checking = False
    
    def start_check(self, domains: List[str]):
        """Start checking domains (called from main thread)"""
        if not self.api_key or not self.api_secret:
            self.error_occurred.emit("API credentials not set")
            return
        
        # Run synchronously
        self.check_all_domains(domains)
    
    def get_cached_external_domains(self) -> List[Dict]:
        """Get cached external nameserver domains"""
        config = self.load_config()
        return config.get("external_ns_domains", [])
    
    def is_external_ns_domain(self, domain: str) -> bool:
        """Check if domain has external nameservers (from cache)"""
        external_domains = self.get_cached_external_domains()
        return any(d["domain"] == domain for d in external_domains)