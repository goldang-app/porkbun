#!/usr/bin/env python3
"""Porkbun 기본 네임서버로 변경 테스트"""
from porkbun_dns import PorkbunDNS
import os

def test_porkbun_nameservers():
    # API 키 (보안상 환경변수나 입력으로 받아야 함)
    print("⚠️  주의: API 키는 절대 코드에 하드코딩하지 마세요!")
    api_key = input("API Key: ").strip()
    secret_key = input("Secret API Key: ").strip()
    domain = "mailtestmaxxpassx.sbs"
    
    client = PorkbunDNS(api_key, secret_key)
    
    print(f"\n테스트 도메인: {domain}")
    
    # 1. 현재 네임서버 확인
    print("\n1. 현재 네임서버 확인...")
    try:
        current_ns = client.get_nameservers(domain)
        print(f"현재 네임서버: {current_ns}")
    except Exception as e:
        print(f"오류: {e}")
        return
    
    # 2. Porkbun 기본 네임서버로 변경 시도
    print("\n2. Porkbun 기본 네임서버로 변경 시도...")
    porkbun_ns = [
        "curitiba.ns.porkbun.com",
        "fortaleza.ns.porkbun.com",
        "maceio.ns.porkbun.com",
        "salvador.ns.porkbun.com"
    ]
    
    print(f"변경할 네임서버: {porkbun_ns}")
    
    try:
        result = client.update_nameservers(domain, porkbun_ns)
        print(f"✅ 성공! 결과: {result}")
        
        # 3. 변경 확인
        print("\n3. 변경된 네임서버 확인...")
        updated_ns = client.get_nameservers(domain)
        print(f"변경된 네임서버: {updated_ns}")
        
        # 4. Cloudflare로 변경 재시도
        print("\n4. 이제 Cloudflare 네임서버로 변경 시도...")
        cloudflare_ns = [
            "lilith.ns.cloudflare.com",
            "hans.ns.cloudflare.com"
        ]
        
        result2 = client.update_nameservers(domain, cloudflare_ns)
        print(f"✅ Cloudflare 변경 성공! 결과: {result2}")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        print("\n추가 확인사항:")
        print("1. Porkbun 웹사이트에 로그인")
        print(f"2. https://porkbun.com/account/domainsSpeedy?domain={domain}")
        print("3. 'Details' 탭에서 'API ACCESS' 확인")
        print("4. 'Nameservers' 섹션에서 수동으로 변경 가능")

if __name__ == "__main__":
    test_porkbun_nameservers()