#!/usr/bin/env python3
"""네임서버 업데이트 상세 테스트"""
from porkbun_dns import PorkbunDNS
import json

def test_nameserver_update_detailed():
    print("="*60)
    print("네임서버 업데이트 상세 테스트")
    print("="*60)
    
    # API 키 입력
    api_key = input("API Key: ").strip()
    secret_key = input("Secret API Key: ").strip()
    domain = input("도메인 (예: example.com): ").strip()
    
    client = PorkbunDNS(api_key, secret_key)
    
    # 1. 현재 네임서버 확인
    print("\n[1단계] 현재 네임서버 확인...")
    try:
        current_ns = client.get_nameservers(domain)
        print(f"현재 네임서버: {current_ns}")
        print(f"네임서버 개수: {len(current_ns)}")
        
        if client.is_using_porkbun_nameservers(current_ns):
            print("✅ Porkbun 네임서버 사용 중")
        else:
            print("⚠️ 외부 네임서버 사용 중")
    except Exception as e:
        print(f"❌ 오류: {e}")
        return
    
    # 2. 테스트할 네임서버 선택
    print("\n[2단계] 테스트할 네임서버 선택")
    print("1. Porkbun 기본 네임서버")
    print("2. Cloudflare 네임서버")
    print("3. 수동 입력")
    
    choice = input("\n선택 (1-3): ").strip()
    
    if choice == "1":
        test_ns = [
            "curitiba.ns.porkbun.com",
            "fortaleza.ns.porkbun.com",
            "maceio.ns.porkbun.com",
            "salvador.ns.porkbun.com"
        ]
    elif choice == "2":
        ns1 = input("Cloudflare NS1 (예: lilith.ns.cloudflare.com): ").strip()
        ns2 = input("Cloudflare NS2 (예: hans.ns.cloudflare.com): ").strip()
        test_ns = [ns1, ns2]
    else:
        test_ns = []
        print("네임서버를 입력하세요 (빈 줄로 종료):")
        while True:
            ns = input(f"NS{len(test_ns)+1}: ").strip()
            if not ns:
                break
            test_ns.append(ns)
    
    if not test_ns:
        print("네임서버가 입력되지 않았습니다.")
        return
    
    print(f"\n설정할 네임서버: {test_ns}")
    
    # 3. API 요청 데이터 확인
    print("\n[3단계] API 요청 데이터 생성")
    data = {}
    for i, ns in enumerate(test_ns[:10], 1):
        data[f"ns{i}"] = ns
    
    # API 키 추가 (디버그용)
    data["apikey"] = "***hidden***"
    data["secretapikey"] = "***hidden***"
    
    print("API로 전송될 데이터:")
    print(json.dumps(data, indent=2))
    
    # 4. 업데이트 실행
    confirm = input("\n업데이트를 실행하시겠습니까? (y/n): ")
    if confirm.lower() != 'y':
        print("취소됨")
        return
    
    print("\n[4단계] 네임서버 업데이트 실행...")
    try:
        # 실제 API 키로 데이터 재구성
        data = {}
        for i, ns in enumerate(test_ns[:10], 1):
            data[f"ns{i}"] = ns
        
        result = client.update_nameservers(domain, test_ns)
        
        print("✅ 업데이트 성공!")
        print(f"응답: {result}")
        
    except Exception as e:
        print(f"❌ 업데이트 실패: {e}")
        print("\n문제 해결 방법:")
        print("1. 웹 대시보드에서 네임서버 상태 확인")
        print(f"   https://porkbun.com/account/domainsSpeedy?domain={domain}")
        print("2. 네임서버가 비어있다면 웹에서 먼저 Porkbun 기본값으로 설정")
        print("3. 그 후 다시 이 프로그램으로 시도")
        return
    
    # 5. 변경 확인
    print("\n[5단계] 변경 확인...")
    try:
        updated_ns = client.get_nameservers(domain)
        print(f"업데이트된 네임서버: {updated_ns}")
        
        if set(updated_ns) == set(test_ns):
            print("✅ 네임서버가 올바르게 업데이트되었습니다!")
        else:
            print("⚠️ 네임서버가 예상과 다릅니다.")
            print(f"예상: {test_ns}")
            print(f"실제: {updated_ns}")
            
    except Exception as e:
        print(f"확인 실패: {e}")

if __name__ == "__main__":
    try:
        test_nameserver_update_detailed()
    except KeyboardInterrupt:
        print("\n\n취소됨")
    except Exception as e:
        print(f"\n오류: {e}")
    
    input("\n엔터를 눌러 종료...")