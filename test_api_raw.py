#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Porkbun API 직접 테스트"""
import requests
import json
from pathlib import Path

def test_raw_api():
    print("="*60)
    print("Porkbun API Raw 테스트")
    print("="*60)
    
    # API 키 로드
    config_file = Path.home() / ".porkbun_dns" / "config.json"
    with open(config_file, "r") as f:
        config = json.load(f)
        api_key = config.get("api_key")
        secret_key = config.get("secret_api_key")
    
    domain = "mailtestmaxxpassx.sbs"
    
    # 1. 현재 네임서버 확인
    print("\n[1] 현재 네임서버 확인...")
    url = f"https://api.porkbun.com/api/json/v3/domain/getNs/{domain}"
    data = {
        "apikey": api_key,
        "secretapikey": secret_key
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # 2. 다양한 형식으로 네임서버 업데이트 시도
    print("\n[2] 네임서버 업데이트 시도 (형식 1 - ns1, ns2만)...")
    url = f"https://api.porkbun.com/api/json/v3/domain/updateNs/{domain}"
    
    # 시도 1: ns1, ns2만 보내기
    data = {
        "apikey": api_key,
        "secretapikey": secret_key,
        "ns1": "hans.ns.cloudflare.com",
        "ns2": "lilith.ns.cloudflare.com"
    }
    
    print(f"Request data: {json.dumps({k: v for k, v in data.items() if k not in ['apikey', 'secretapikey']}, indent=2)}")
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success! Response: {json.dumps(result, indent=2)}")
    elif response.status_code == 500:
        print("500 Error")
        print(f"Headers: {dict(response.headers)}")
        print(f"Body: {response.text[:500] if response.text else 'Empty'}")
        
        # 시도 2: 모든 ns 필드를 명시적으로 설정
        print("\n[3] 네임서버 업데이트 시도 (형식 2 - 모든 필드)...")
        data = {
            "apikey": api_key,
            "secretapikey": secret_key,
            "ns1": "hans.ns.cloudflare.com",
            "ns2": "lilith.ns.cloudflare.com",
            "ns3": "",
            "ns4": "",
            "ns5": "",
            "ns6": "",
            "ns7": "",
            "ns8": "",
            "ns9": "",
            "ns10": ""
        }
        
        print("Request with all fields (empty for ns3-ns10)")
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success! Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Failed: {response.status_code}")
            
            # 시도 3: ns 배열로 보내기 (비표준)
            print("\n[4] 네임서버 업데이트 시도 (형식 3 - 배열)...")
            data = {
                "apikey": api_key,
                "secretapikey": secret_key,
                "ns": ["hans.ns.cloudflare.com", "lilith.ns.cloudflare.com"]
            }
            
            print("Request with ns array")
            response = requests.post(url, json=data)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Success! Response: {json.dumps(result, indent=2)}")
            else:
                print(f"Failed: {response.status_code}")
    
    # 3. 최종 확인
    print("\n[5] 최종 네임서버 확인...")
    url = f"https://api.porkbun.com/api/json/v3/domain/getNs/{domain}"
    data = {
        "apikey": api_key,
        "secretapikey": secret_key
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    print(f"Current nameservers: {result.get('ns', [])}")

if __name__ == "__main__":
    test_raw_api()