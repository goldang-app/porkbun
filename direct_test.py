#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""직접 테스트 - mailtestmaxxpassx.sbs 네임서버 변경"""
from porkbun_dns import PorkbunDNS
import json
from pathlib import Path
import sys
import io

# 한글 출력 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def direct_test():
    print("="*60)
    print("직접 네임서버 변경 테스트")
    print("도메인: mailtestmaxxpassx.sbs")
    print("목표: Cloudflare 네임서버로 변경")
    print("="*60)
    
    # 저장된 API 키 로드
    config_file = Path.home() / ".porkbun_dns" / "config.json"
    if config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)
            api_key = config.get("api_key")
            secret_key = config.get("secret_api_key")
            print("\n✅ 저장된 API 키 로드됨")
    else:
        print("❌ 저장된 API 키가 없습니다.")
        api_key = input("API Key: ").strip()
        secret_key = input("Secret API Key: ").strip()
    
    domain = "mailtestmaxxpassx.sbs"
    client = PorkbunDNS(api_key, secret_key)
    
    # 1. API 연결 테스트
    print("\n[1단계] API 연결 테스트...")
    if not client.ping():
        print("❌ API 연결 실패")
        return
    print("✅ API 연결 성공")
    
    # 2. 현재 네임서버 확인
    print(f"\n[2단계] 현재 네임서버 확인...")
    try:
        current_ns = client.get_nameservers(domain)
        print(f"현재 네임서버: {current_ns}")
        if not current_ns:
            print("⚠️ 네임서버가 비어있습니다!")
    except Exception as e:
        print(f"확인 실패: {e}")
    
    # 3. Cloudflare 네임서버로 변경 시도
    print(f"\n[3단계] Cloudflare 네임서버로 변경 시도...")
    cloudflare_ns = [
        "hans.ns.cloudflare.com",
        "lilith.ns.cloudflare.com"
    ]
    
    print(f"설정할 네임서버: {cloudflare_ns}")
    
    # API 요청 데이터 확인
    data = {
        "ns1": cloudflare_ns[0],
        "ns2": cloudflare_ns[1]
    }
    print(f"\nAPI 요청 데이터 (ns3~ns10 제외):")
    print(json.dumps(data, indent=2))
    
    try:
        result = client.update_nameservers(domain, cloudflare_ns)
        print(f"\n✅ 성공! 응답: {result}")
    except Exception as e:
        print(f"\n❌ 실패: {e}")
        
        # 실패 시 Porkbun 기본값으로 먼저 설정
        print("\n[대안] Porkbun 기본 네임서버로 먼저 변경...")
        porkbun_ns = [
            "curitiba.ns.porkbun.com",
            "fortaleza.ns.porkbun.com",
            "maceio.ns.porkbun.com",
            "salvador.ns.porkbun.com"
        ]
        
        try:
            result = client.update_nameservers(domain, porkbun_ns)
            print(f"✅ Porkbun 네임서버 설정 성공: {result}")
            
            # 다시 Cloudflare로 시도
            print("\n[재시도] 이제 Cloudflare로 변경...")
            result = client.update_nameservers(domain, cloudflare_ns)
            print(f"✅ Cloudflare 설정 성공: {result}")
            
        except Exception as e2:
            print(f"❌ Porkbun 기본값 설정도 실패: {e2}")
            return
    
    # 4. 변경 확인
    print(f"\n[4단계] 변경 확인...")
    try:
        updated_ns = client.get_nameservers(domain)
        print(f"현재 네임서버: {updated_ns}")
        
        if set([ns.lower() for ns in updated_ns]) == set([ns.lower() for ns in cloudflare_ns]):
            print("\n🎉 성공! Cloudflare 네임서버로 변경되었습니다.")
        else:
            print(f"\n⚠️ 네임서버가 예상과 다릅니다.")
            print(f"예상: {cloudflare_ns}")
            print(f"실제: {updated_ns}")
    except Exception as e:
        print(f"확인 실패: {e}")

if __name__ == "__main__":
    try:
        direct_test()
    except Exception as e:
        print(f"\n오류: {e}")