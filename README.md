# Porkbun DNS 관리 도구

Porkbun DNS 레코드를 관리하기 위한 GUI 기반 Python 애플리케이션입니다.

## 🚀 주요 기능

### DNS 레코드 관리
- DNS 레코드 생성, 수정, 삭제
- 지원하는 레코드 타입: A, AAAA, CNAME, MX, TXT, NS, SRV, TLSA, CAA, HTTPS, SVCB
- 실시간 레코드 상태 확인
- 레코드별 상세 정보 관리

### 도메인 관리
- 여러 도메인 동시 관리
- 도메인별 DNS 레코드 분리 표시
- Porkbun API를 통한 실시간 동기화
- 도메인 상태 모니터링

### Tempererror & 대량 DNS 템플릿
- "대량 작업" 탭에서 수십 개 도메인을 체크하고 한 번에 레코드 생성
- Tempererror SPF 버튼으로 30자 이상의 랜덤 서브도메인 체인을 자동 구성
- 생성된 서브도메인·결과를 토스트 및 로그 영역에서 즉시 확인
- Tempererror 체인 단계(랜덤 서브도메인 개수)를 1~10 사이에서 직접 지정 가능
- Tempererror 실행 시 기존 TXT 레코드는 모두 삭제한 뒤 새 체인을 생성하여 충돌을 방지
- 최종 `~all` 라인의 내용을 직접 입력하여 include 대상 등을 자유롭게 조정 가능

### 사용자 인터페이스
- 직관적인 PyQt6 기반 GUI
- 도메인별 탭 구성으로 편리한 관리
- 키보드 단축키 지원
- 실시간 상태 표시줄과 진행률 표시

### 네임서버 관리
- 도메인 네임서버 실시간 확인
- 백그라운드 작업으로 성능 최적화
- 네임서버 변경 감지 및 알림

## 🛠 설치 및 설정

### 시스템 요구사항
- Python 3.11 이상
- PyQt6
- 인터넷 연결 (Porkbun API 접근용)

### 설치 방법
```bash
# 저장소 복제
git clone <repository-url>
cd porkbun-dns-manager

# 가상환경 생성 (권장)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt
# 또는 uv 사용시
uv sync
```

## 🔧 사용 방법

### 1. API 키 설정
Porkbun API 키는 코드 내에 하드코딩되어 있습니다. 
실제 사용시에는 `.env` 파일을 생성하여 다음과 같이 설정하세요:

```env
PORKBUN_API_KEY=your_api_key_here
PORKBUN_SECRET_API_KEY=your_secret_key_here
```

### 2. 애플리케이션 실행
```bash
python main.py
```

### 3. 기본 사용법
1. 애플리케이션 시작 시 자동으로 도메인 목록 로드
2. 원하는 도메인 탭 선택
3. DNS 레코드 추가, 수정, 삭제
4. 실시간으로 변경사항이 Porkbun에 반영됨

### 4. Tempererror / 대량 작업 탭 사용법
1. 로그인 후 `대량 작업` 탭을 열어 도메인 목록을 확인합니다.
2. `전체 선택` 또는 개별 체크박스로 대상 도메인을 지정합니다.
3. 수동 폼으로 일반 DNS를 일괄 추가하거나 `Tempererror 체인 생성` 버튼을 사용합니다.
4. Tempererror 실행 전 체인 단계(1이면 `_spf` → 최종 ~all 직결, 2 이상이면 랜덤 서브도메인 체인)를 선택합니다.
5. 마지막 TXT 내용(기본값: `v=spf1 include:_spf.AUTUMNWINDZ.COM ~all`)을 원하는 값으로 입력합니다.
6. Tempererror를 실행하면 선택한 도메인의 기존 TXT 레코드가 모두 삭제된 뒤 새 체인이 적용됩니다.
7. 진행 상황과 결과가 하단 로그와 토스트 메시지로 표시됩니다.

## 📁 프로젝트 구조

```
porkbun-dns-manager/
├── main.py                     # 메인 GUI 애플리케이션
├── lib/                        # 라이브러리 모듈
│   ├── porkbun_dns.py         # Porkbun API 클라이언트
│   ├── dashboard_widget.py    # 대시보드 위젯
│   └── workers/               # 백그라운드 작업 모듈
│       └── domain_ns_worker.py # 도메인 네임서버 작업자
├── config/                     # 설정 파일 디렉토리
├── pyproject.toml             # 프로젝트 설정
└── README.md
```

## ⌨️ 키보드 단축키

- `Ctrl+R` - 새로고침
- `Ctrl+N` - 새 레코드 추가
- `Del` - 선택된 레코드 삭제
- `Ctrl+S` - 현재 상태 저장
- `F5` - 도메인 목록 새로고침

## 🎯 지원하는 레코드 타입

| 타입 | 설명 | 용도 |
|------|------|------|
| **A** | IPv4 주소 | 웹사이트 호스팅 |
| **AAAA** | IPv6 주소 | IPv6 웹사이트 호스팅 |
| **CNAME** | 별칭 | 서브도메인 연결 |
| **MX** | 메일 서버 | 이메일 라우팅 |
| **TXT** | 텍스트 | SPF, DKIM 등 |
| **NS** | 네임서버 | DNS 위임 |
| **SRV** | 서비스 | 특정 서비스 위치 |
| **TLSA** | TLS 인증 | SSL/TLS 보안 |
| **CAA** | 인증 기관 | SSL 인증서 제한 |

## 🔒 보안 고려사항

- API 키는 소스코드에서 분리하여 환경변수로 관리 권장
- HTTPS를 통한 안전한 API 통신
- 로컬 설정 파일의 권한 관리 필요

## 📄 라이센스

MIT License

## 🐛 버그 리포트

버그 발견 시 GitHub Issues를 통해 신고해 주세요.

## 🤝 기여 방법

기여를 원하시는 분은 Pull Request를 보내주세요.

---
DNS 관리를 더 쉽고 편리하게 만들기 위해 제작되었습니다.
