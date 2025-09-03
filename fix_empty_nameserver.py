#!/usr/bin/env python3
"""네임서버가 비어있는 도메인 복구 스크립트"""
from porkbun_dns import PorkbunDNS
import sys

def fix_empty_nameservers():
    """네임서버가 비어있는 도메인을 Porkbun 기본값으로 복구"""
    
    print("=" * 60)
    print("네임서버 복구 도구")
    print("=" * 60)
    print("\n이 도구는 네임서버가 비어있는 도메인을")
    print("Porkbun 기본 네임서버로 복구합니다.\n")
    
    # API 키 입력
    api_key = input("API Key: ").strip()
    secret_key = input("Secret API Key: ").strip()
    domain = input("도메인 이름 (예: example.com): ").strip()
    
    client = PorkbunDNS(api_key, secret_key)
    
    # 1. API 연결 테스트
    print(f"\n[1/4] API 연결 테스트...")
    if not client.ping():
        print("❌ API 연결 실패. API 키를 확인하세요.")
        return
    print("✅ API 연결 성공")
    
    # 2. 현재 네임서버 확인
    print(f"\n[2/4] 현재 네임서버 확인...")
    try:
        current_ns = client.get_nameservers(domain)
        if current_ns:
            print(f"현재 네임서버: {current_ns}")
            reply = input("\n네임서버가 이미 설정되어 있습니다. 계속하시겠습니까? (y/n): ")
            if reply.lower() != 'y':
                print("작업 취소됨")
                return
        else:
            print("⚠️ 네임서버가 비어있습니다!")
    except Exception as e:
        print(f"네임서버 확인 실패: {e}")
        # API 접근 권한 문제일 수 있음
        if "not opted in" in str(e) or "API 접근이 비활성화" in str(e):
            print("\n❌ 이 도메인에 대한 API 접근이 비활성화되어 있습니다.")
            print("해결 방법:")
            print("1. https://porkbun.com 로그인")
            print("2. Domain Management 페이지")
            print(f"3. '{domain}' 도메인 클릭")
            print("4. Details 탭에서 'API ACCESS' 토글을 ON으로 변경")
            return
    
    # 3. Porkbun 기본 네임서버로 설정
    print(f"\n[3/4] Porkbun 기본 네임서버로 설정...")
    porkbun_ns = [
        "curitiba.ns.porkbun.com",
        "fortaleza.ns.porkbun.com",
        "maceio.ns.porkbun.com",
        "salvador.ns.porkbun.com"
    ]
    
    print("설정할 네임서버:")
    for ns in porkbun_ns:
        print(f"  - {ns}")
    
    try:
        result = client.update_nameservers(domain, porkbun_ns)
        if result.get("status") == "SUCCESS":
            print("\n✅ 네임서버 업데이트 성공!")
        else:
            print(f"\n❌ 업데이트 실패: {result.get('message', 'Unknown error')}")
            return
    except Exception as e:
        print(f"\n❌ 네임서버 업데이트 실패: {e}")
        print("\n대안:")
        print(f"1. 웹사이트에서 직접 설정: https://porkbun.com/account/domainsSpeedy?domain={domain}")
        print("2. 잠시 후 다시 시도")
        return
    
    # 4. 확인
    print(f"\n[4/4] 변경 사항 확인...")
    try:
        updated_ns = client.get_nameservers(domain)
        print(f"업데이트된 네임서버: {updated_ns}")
        
        if client.is_using_porkbun_nameservers(updated_ns):
            print("\n🎉 성공! 이제 DNS 레코드를 관리할 수 있습니다.")
        else:
            print("\n⚠️ 네임서버가 업데이트되었지만 Porkbun이 아닌 것 같습니다.")
    except Exception as e:
        print(f"확인 실패: {e}")
        print("웹사이트에서 직접 확인해보세요.")

if __name__ == "__main__":
    try:
        fix_empty_nameservers()
    except KeyboardInterrupt:
        print("\n\n작업 취소됨")
    except Exception as e:
        print(f"\n오류: {e}")
    
    input("\n엔터를 눌러 종료...")