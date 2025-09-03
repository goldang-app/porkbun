#!/usr/bin/env python3
"""테스트 스크립트 - 네임서버 업데이트 디버깅"""
from porkbun_dns import PorkbunDNS
import sys

def test_nameserver_update():
    # API 키 입력
    api_key = input("API Key: ").strip()
    secret_key = input("Secret API Key: ").strip()
    domain = input("Domain (예: mailtestmaxxpassx.sbs): ").strip()
    
    client = PorkbunDNS(api_key, secret_key)
    
    # 1. API 연결 테스트
    print("\n1. API 연결 테스트...")
    if client.ping():
        print("✅ API 연결 성공")
    else:
        print("❌ API 연결 실패")
        return
    
    # 2. 도메인 정보 확인
    print(f"\n2. 도메인 '{domain}' 정보 확인...")
    domain_info = client.get_domain_info(domain)
    print(f"도메인 상태: {domain_info}")
    
    if domain_info.get("status") == "ERROR":
        if not domain_info.get("api_access", True):
            print("❌ API 접근이 비활성화되어 있습니다!")
            print("\n해결 방법:")
            print("1. https://porkbun.com 로그인")
            print("2. Domain Management 페이지")
            print(f"3. '{domain}' 도메인 클릭")
            print("4. Details 탭에서 'API ACCESS' 토글을 ON으로 변경")
            return
        else:
            print(f"❌ 도메인 접근 오류: {domain_info.get('error')}")
            return
    
    # 3. 현재 네임서버 확인
    print(f"\n3. 현재 네임서버 확인...")
    try:
        current_ns = client.get_nameservers(domain)
        print(f"현재 네임서버: {current_ns}")
    except Exception as e:
        print(f"❌ 네임서버 조회 실패: {e}")
        return
    
    # 4. Cloudflare 네임서버로 변경 시도
    print(f"\n4. Cloudflare 네임서버로 변경 시도...")
    cloudflare_ns = [
        "lilith.ns.cloudflare.com",
        "hans.ns.cloudflare.com"
    ]
    
    print(f"변경할 네임서버: {cloudflare_ns}")
    
    try:
        result = client.update_nameservers(domain, cloudflare_ns)
        print(f"✅ 네임서버 업데이트 성공: {result}")
    except Exception as e:
        print(f"❌ 네임서버 업데이트 실패: {e}")
        
        # 추가 디버깅 정보
        print("\n디버깅 정보:")
        print("- 위의 [DEBUG] 메시지를 확인하세요")
        print("- 500 에러의 경우 응답 본문이 출력됩니다")
        
        # 대안 제시
        print("\n다른 시도해볼 방법:")
        print("1. Porkbun 기본 네임서버로 먼저 변경 시도")
        print("2. 웹사이트에서 직접 변경 후 API로 확인")

if __name__ == "__main__":
    test_nameserver_update()