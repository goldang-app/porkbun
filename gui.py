"""PyQt6 GUI for Porkbun DNS Manager"""
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox, QLabel,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QSpinBox, QTextEdit, QFileDialog, QMenu, QHeaderView, QSplitter,
    QGroupBox, QCheckBox, QToolBar, QStatusBar, QListWidget, QListWidgetItem,
    QProgressDialog, QStyledItemDelegate, QProgressBar, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QColor, QKeySequence, QShortcut
import os
from dotenv import load_dotenv
from porkbun_dns import PorkbunDNS, RecordType
from dashboard_widget import DashboardWidget
from workers.domain_ns_worker import DomainNSWorker


class ApiWorker(QThread):
    """Background worker for API calls"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, client, method, *args, **kwargs):
        super().__init__()
        self.client = client
        self.method = method
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            method = getattr(self.client, self.method)
            result = method(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))




class LoginWorker(QThread):
    """Background worker for login process"""
    success = pyqtSignal(object, list)  # PorkbunDNS 객체와 도메인 리스트 전달
    error = pyqtSignal(str)
    status = pyqtSignal(str)  # 상태 메시지
    
    def __init__(self, api_key: str, secret_key: str):
        super().__init__()
        self.api_key = api_key
        self.secret_key = secret_key
    
    def run(self):
        try:
            self.status.emit("API 연결 시도 중...")
            client = PorkbunDNS(self.api_key, self.secret_key)
            
            self.status.emit("API 인증 확인 중...")
            if client.ping():
                self.status.emit("도메인 목록 가져오는 중...")
                # 도메인 목록도 백그라운드에서 로드
                try:
                    domains = client.get_domains()
                    self.status.emit("로그인 성공!")
                    self.success.emit(client, domains)
                except Exception as e:
                    self.status.emit("로그인 성공!")
                    self.success.emit(client, [])  # 도메인 로드 실패해도 로그인은 성공
            else:
                self.error.emit("API 인증에 실패했습니다.")
        except Exception as e:
            self.error.emit(f"연결 실패: {str(e)}")


class SettingsDialog(QDialog):
    """Dialog for API settings"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 설정")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("API 키를 입력하세요")
        form_layout.addRow("API 키:", self.api_key_input)
        
        self.secret_key_input = QLineEdit()
        self.secret_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_key_input.setPlaceholderText("Secret API 키를 입력하세요")
        form_layout.addRow("Secret API 키:", self.secret_key_input)
        
        layout.addLayout(form_layout)
        
        # Info label
        info_label = QLabel("API 키 발급: <a href='https://porkbun.com/account/api'>porkbun.com/account/api</a>")
        info_label.setOpenExternalLinks(True)
        layout.addWidget(info_label)
        
        # Test button
        self.test_button = QPushButton("연결 테스트")
        self.test_button.clicked.connect(self.test_connection)
        layout.addWidget(self.test_button)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Load existing settings
        self.load_settings()
    
    def load_settings(self):
        """Load existing API settings"""
        config_file = Path.home() / ".porkbun_dns" / "config.json"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    self.api_key_input.setText(config.get("api_key", ""))
                    self.secret_key_input.setText(config.get("secret_api_key", ""))
            except Exception:
                pass
        
        # Also check environment variables
        load_dotenv()
        if os.getenv("PORKBUN_API_KEY"):
            self.api_key_input.setText(os.getenv("PORKBUN_API_KEY"))
        if os.getenv("PORKBUN_SECRET_API_KEY"):
            self.secret_key_input.setText(os.getenv("PORKBUN_SECRET_API_KEY"))
    
    def test_connection(self):
        """Test API connection"""
        api_key = self.api_key_input.text()
        secret_key = self.secret_key_input.text()
        
        if not api_key or not secret_key:
            QMessageBox.warning(self, "경고", "두 API 키를 모두 입력해주세요")
            return
        
        try:
            client = PorkbunDNS(api_key, secret_key)
            if client.ping():
                QMessageBox.information(self, "성공", "연결 성공!")
            else:
                QMessageBox.warning(self, "실패", "인증 실패")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"연결 오류: {str(e)}")
    
    def get_credentials(self):
        """Get the entered credentials"""
        return self.api_key_input.text(), self.secret_key_input.text()
    
    def save_settings(self):
        """Save settings to config file"""
        api_key, secret_key = self.get_credentials()
        if api_key and secret_key:
            config_file = Path.home() / ".porkbun_dns" / "config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w") as f:
                json.dump({
                    "api_key": api_key,
                    "secret_api_key": secret_key
                }, f, indent=2)


class RecordDialog(QDialog):
    """Dialog for adding/editing DNS records"""
    def __init__(self, domain: str, record: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.record = record
        self.setWindowTitle("레코드 수정" if record else "레코드 추가")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Record type
        self.type_combo = QComboBox()
        self.type_combo.addItems([rt.value for rt in RecordType])
        if record:
            self.type_combo.setCurrentText(record.get("type", "A"))
            self.type_combo.setEnabled(False)  # Can't change type when editing
        else:
            self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form_layout.addRow("타입:", self.type_combo)
        
        # Subdomain
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("루트 도메인은 비워두세요")
        if record:
            name = record.get("name", "")
            if name and name != domain:
                # Remove domain from full name
                subdomain = name.replace(f".{domain}", "")
                self.name_input.setText(subdomain)
        form_layout.addRow("서브도메인:", self.name_input)
        
        # Content
        self.content_input = QLineEdit()
        self.content_input.setPlaceholderText("IP 주소, 도메인 이름, 또는 텍스트 값")
        if record:
            self.content_input.setText(record.get("content", ""))
        form_layout.addRow("값:", self.content_input)
        
        # TTL
        self.ttl_input = QSpinBox()
        self.ttl_input.setMinimum(600)
        self.ttl_input.setMaximum(86400)
        self.ttl_input.setSingleStep(300)
        self.ttl_input.setValue(record.get("ttl", 600) if record else 600)
        form_layout.addRow("TTL (초):", self.ttl_input)
        
        # Priority (for MX records)
        self.priority_label = QLabel("우선순위:")
        self.priority_input = QSpinBox()
        self.priority_input.setMinimum(0)
        self.priority_input.setMaximum(65535)
        self.priority_input.setValue(record.get("prio", 10) if record else 10)
        form_layout.addRow(self.priority_label, self.priority_input)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        self.notes_input.setPlaceholderText("메모 (선택사항)")
        if record:
            self.notes_input.setPlainText(record.get("notes", ""))
        form_layout.addRow("메모:", self.notes_input)
        
        layout.addLayout(form_layout)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Update priority visibility
        self.on_type_changed(self.type_combo.currentText())
    
    def on_type_changed(self, record_type: str):
        """Handle record type change"""
        # Show/hide priority field based on record type
        show_priority = record_type in ["MX", "SRV"]
        self.priority_label.setVisible(show_priority)
        self.priority_input.setVisible(show_priority)
    
    def get_record_data(self):
        """Get the record data from the form"""
        data = {
            "type": self.type_combo.currentText(),
            "name": self.name_input.text(),
            "content": self.content_input.text(),
            "ttl": self.ttl_input.value(),
            "notes": self.notes_input.toPlainText()
        }
        
        if self.type_combo.currentText() in ["MX", "SRV"]:
            data["prio"] = self.priority_input.value()
        
        if self.record:
            data["id"] = self.record.get("id")
        
        return data


class NameserverDialog(QDialog):
    """Dialog to manage nameservers for a domain"""
    def __init__(self, client: PorkbunDNS, domain: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.domain = domain
        self.setWindowTitle(f"네임서버 관리 - {domain}")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Current status
        self.status_label = QLabel("네임서버 확인 중...")
        self.status_label.setStyleSheet("padding: 10px; font-size: 11pt;")
        layout.addWidget(self.status_label)
        
        # Nameserver list
        form_layout = QFormLayout()
        self.ns_inputs = []
        
        for i in range(4):  # Show 4 nameserver inputs by default
            ns_input = QLineEdit()
            ns_input.setPlaceholderText(f"네임서버 {i+1} (예: ns1.example.com)")
            self.ns_inputs.append(ns_input)
            form_layout.addRow(f"네임서버 {i+1}:", ns_input)
        
        layout.addLayout(form_layout)
        
        # Quick set buttons
        quick_layout = QHBoxLayout()
        
        self.porkbun_btn = QPushButton("🐷 Porkbun 기본 네임서버로 복원")
        self.porkbun_btn.clicked.connect(self.set_porkbun_nameservers)
        self.porkbun_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
        quick_layout.addWidget(self.porkbun_btn)
        
        self.clear_btn = QPushButton("🗑️ 모두 지우기")
        self.clear_btn.clicked.connect(self.clear_all_nameservers)
        quick_layout.addWidget(self.clear_btn)
        
        layout.addLayout(quick_layout)
        
        # Info text
        info_text = QLabel(
            "💡 팁: Porkbun에서 DNS 레코드를 관리하려면 Porkbun 네임서버를 사용해야 합니다.\n"
            "외부 네임서버(Cloudflare, Google 등)를 사용하면 해당 서비스에서 DNS를 관리해야 합니다."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #666; padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        layout.addWidget(info_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 저장")
        self.save_btn.clicked.connect(self.save_nameservers)
        button_layout.addWidget(self.save_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("닫기")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Load current nameservers
        self.load_current_nameservers()
    
    def load_current_nameservers(self):
        """Load current nameservers for the domain"""
        try:
            nameservers = self.client.get_nameservers(self.domain)
            
            # Clear inputs
            for input in self.ns_inputs:
                input.clear()
            
            # Fill inputs with current nameservers
            for i, ns in enumerate(nameservers[:4]):
                if i < len(self.ns_inputs):
                    self.ns_inputs[i].setText(ns)
            
            # Check if using Porkbun nameservers
            if self.client.is_using_porkbun_nameservers(nameservers):
                self.status_label.setText(
                    "✅ 현재 Porkbun 네임서버를 사용 중입니다.\n"
                    "DNS 레코드를 이 프로그램에서 관리할 수 있습니다."
                )
                self.status_label.setStyleSheet("padding: 10px; font-size: 11pt; background-color: #e8f5e9; color: #2e7d32; border-radius: 5px;")
                self.porkbun_btn.setEnabled(False)
                self.porkbun_btn.setText("🐷 이미 Porkbun 네임서버 사용 중")
            else:
                # Show which service might be in use
                if any("cloudflare" in ns.lower() for ns in nameservers):
                    service = "Cloudflare"
                elif any("google" in ns.lower() or "ns-cloud" in ns.lower() for ns in nameservers):
                    service = "Google Cloud DNS"
                elif any("awsdns" in ns.lower() for ns in nameservers):
                    service = "AWS Route53"
                elif any("hostinger" in ns.lower() for ns in nameservers):
                    service = "Hostinger"
                elif any("namecheap" in ns.lower() for ns in nameservers):
                    service = "Namecheap"
                else:
                    service = "외부"
                
                self.status_label.setText(
                    f"⚠️ {service} 네임서버를 사용 중입니다.\n"
                    f"DNS 레코드를 Porkbun에서 관리하려면 네임서버를 변경해야 합니다."
                )
                self.status_label.setStyleSheet("padding: 10px; font-size: 11pt; background-color: #fff3e0; color: #e65100; border-radius: 5px;")
                self.porkbun_btn.setEnabled(True)
                self.porkbun_btn.setText("🐷 Porkbun 기본 네임서버로 복원")
                
        except Exception as e:
            self.status_label.setText(f"❌ 네임서버 로드 실패: {str(e)}")
            self.status_label.setStyleSheet("padding: 10px; font-size: 11pt; background-color: #ffebee; color: #c62828;")
    
    def set_porkbun_nameservers(self):
        """Set Porkbun default nameservers"""
        porkbun_ns = self.client.get_default_nameservers()
        for i, ns in enumerate(porkbun_ns):
            if i < len(self.ns_inputs):
                self.ns_inputs[i].setText(ns)
        # Clear remaining inputs
        for i in range(len(porkbun_ns), len(self.ns_inputs)):
            self.ns_inputs[i].clear()
    
    def clear_all_nameservers(self):
        """Clear all nameserver inputs"""
        for input in self.ns_inputs:
            input.clear()
    
    def save_nameservers(self):
        """Save the nameservers"""
        nameservers = []
        for input in self.ns_inputs:
            ns = input.text().strip()
            if ns:
                nameservers.append(ns)
        
        if not nameservers:
            # 네임서버가 비어있을 때 Porkbun 기본값 사용 제안
            reply = QMessageBox.question(
                self,
                "네임서버 비어있음",
                "네임서버가 입력되지 않았습니다.\n\n"
                "Porkbun 기본 네임서버로 설정하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.set_porkbun_nameservers()
                nameservers = []
                for input in self.ns_inputs:
                    ns = input.text().strip()
                    if ns:
                        nameservers.append(ns)
            else:
                return
        
        try:
            result = self.client.update_nameservers(self.domain, nameservers)
            if result.get("status") == "SUCCESS":
                QMessageBox.information(self, "성공", "네임서버가 성공적으로 업데이트되었습니다.")
                self.accept()
            else:
                QMessageBox.warning(self, "실패", f"네임서버 업데이트 실패: {result.get('message')}")
        except Exception as e:
            error_msg = str(e)
            if "500" in error_msg or "Internal Server Error" in error_msg:
                # 500 에러 시 특별 처리
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("네임서버 업데이트 실패")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText("네임서버 업데이트에 실패했습니다.")
                msg_box.setInformativeText(
                    "현재 도메인의 네임서버가 비어있는 상태일 수 있습니다.\n\n"
                    "1. 먼저 Porkbun 기본 네임서버로 설정해보세요.\n"
                    "2. 그 다음 원하는 네임서버로 변경하세요."
                )
                msg_box.setDetailedText(error_msg)
                
                # 커스텀 버튼 추가
                porkbun_btn = msg_box.addButton("Porkbun 기본값 사용", QMessageBox.ButtonRole.ActionRole)
                web_btn = msg_box.addButton("웹사이트에서 설정", QMessageBox.ButtonRole.ActionRole)
                cancel_btn = msg_box.addButton(QMessageBox.StandardButton.Cancel)
                
                msg_box.exec()
                
                if msg_box.clickedButton() == porkbun_btn:
                    self.set_porkbun_nameservers()
                elif msg_box.clickedButton() == web_btn:
                    import webbrowser
                    webbrowser.open(f"https://porkbun.com/account/domainsSpeedy?domain={self.domain}")
            else:
                QMessageBox.critical(self, "오류", f"네임서버 업데이트 오류:\n\n{error_msg}")


class APIAccessDialog(QDialog):
    """Dialog to show API access status for all domains"""
    def __init__(self, client: PorkbunDNS, parent=None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle("도메인 API 접근 상태")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel(
            "각 도메인의 API 접근 상태를 확인합니다.\n"
            "❌ 표시된 도메인은 Porkbun 웹사이트에서 API ACCESS를 활성화해야 합니다."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Domain list
        self.domain_list = QListWidget()
        layout.addWidget(self.domain_list)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setMaximumHeight(150)
        instructions.setHtml(
            "<h3>API ACCESS 활성화 방법:</h3>"
            "<ol>"
            "<li><a href='https://porkbun.com'>porkbun.com</a> 로그인</li>"
            "<li>Domain Management 페이지 이동</li>"
            "<li>도메인 이름 클릭</li>"
            "<li>Details 탭에서 'API ACCESS' 섹션 찾기</li>"
            "<li>API ACCESS 토글을 <b>ON</b>으로 변경</li>"
            "<li>모든 도메인에 대해 반복</li>"
            "</ol>"
            "<p><b>팁:</b> 새 탭에서 여러 도메인을 동시에 열어두고 작업하면 빠릅니다.</p>"
        )
        layout.addWidget(instructions)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.check_button = QPushButton("🔄 다시 확인")
        self.check_button.clicked.connect(self.check_all_domains)
        button_layout.addWidget(self.check_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("닫기")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Check domains on init
        self.check_all_domains()
    
    def check_all_domains(self):
        """Check API access for all domains"""
        self.domain_list.clear()
        self.check_button.setEnabled(False)
        
        try:
            domains = self.client.get_domains()
            
            # Create progress dialog
            progress = QProgressDialog(
                "도메인 API 접근 상태 확인 중...",
                "취소",
                0,
                len(domains),
                self
            )
            progress.setWindowTitle("확인 중")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            enabled_count = 0
            disabled_count = 0
            
            for i, domain in enumerate(domains):
                if progress.wasCanceled():
                    break
                    
                domain_name = domain.get("domain", "")
                progress.setLabelText(f"{domain_name} 확인 중...")
                progress.setValue(i)
                
                # Check if domain is active
                if domain.get("status") != "ACTIVE":
                    item = QListWidgetItem(f"⚫ {domain_name} - 비활성 도메인")
                    self.domain_list.addItem(item)
                    continue
                
                # Check API access
                has_access = self.client.check_domain_api_access(domain_name)
                
                if has_access:
                    item = QListWidgetItem(f"✅ {domain_name} - API 접근 활성화됨")
                    item.setForeground(QColor(0, 128, 0))
                    enabled_count += 1
                else:
                    item = QListWidgetItem(f"❌ {domain_name} - API 접근 비활성화 (활성화 필요!)")
                    item.setForeground(QColor(200, 0, 0))
                    disabled_count += 1
                
                self.domain_list.addItem(item)
            
            progress.setValue(len(domains))
            progress.close()
            
            # Show summary
            summary = f"\n총 {len(domains)}개 도메인 중:\n"
            summary += f"✅ 활성화: {enabled_count}개\n"
            summary += f"❌ 비활성화: {disabled_count}개"
            
            if disabled_count > 0:
                summary += f"\n\n{disabled_count}개 도메인의 API ACCESS를 활성화해주세요."
            
            summary_item = QListWidgetItem(summary)
            bold_font = QFont()
            bold_font.setPointSize(10)
            bold_font.setBold(True)
            summary_item.setFont(bold_font)
            self.domain_list.addItem(summary_item)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"도메인 확인 실패: {str(e)}")
        finally:
            self.check_button.setEnabled(True)


class DNSManagerGUI(QMainWindow):
    """Main GUI application"""
    def __init__(self):
        super().__init__()
        self.client = None
        self.current_domain = None
        self.current_records = []
        self.modified_records = {}  # Track modified records
        self.domain_info = {}  # Store domain nameserver info
        self.is_logged_in = False
        self.login_worker = None  # 로그인 쓰레드
        self.dashboard_widget = None  # 대시보드 위젯
        self.ns_check_worker = None  # 네임서버 체크 워커
        self.ns_progress_dialog = None  # 진행 표시 대화상자
        self.init_ui()
        self.setup_shortcuts()
        # GUI를 먼저 표시하고 로그인은 사용자가 버튼을 누를 때 수행
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Porkbun DNS 관리자")
        self.setGeometry(100, 100, 1200, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Login status and button
        login_layout = QHBoxLayout()
        
        self.login_status_label = QLabel("⚠️ 로그인되지 않음")
        self.login_status_label.setStyleSheet("padding: 5px; font-weight: bold; color: #ff6600;")
        login_layout.addWidget(self.login_status_label)
        
        # 로그인 진행 표시용 프로그레스 바 (평소에는 숨김)
        self.login_progress = QProgressBar()
        self.login_progress.setMaximumHeight(20)
        self.login_progress.setTextVisible(False)
        self.login_progress.setRange(0, 0)  # Indeterminate progress
        self.login_progress.hide()
        login_layout.addWidget(self.login_progress)
        
        self.login_btn = QPushButton("🔐 로그인")
        self.login_btn.clicked.connect(self.perform_login)
        self.login_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 15px; }")
        login_layout.addWidget(self.login_btn)
        
        login_layout.addStretch()
        main_layout.addLayout(login_layout)
        
        # Tab widget for dashboard and DNS control
        self.tab_widget = QTabWidget()
        
        # Dashboard tab
        self.dashboard_widget = DashboardWidget()
        self.dashboard_widget.domain_selected.connect(self.on_dashboard_domain_selected)
        self.tab_widget.addTab(self.dashboard_widget, "📊 대시보드")
        
        # DNS Control tab
        dns_control_widget = QWidget()
        dns_control_layout = QVBoxLayout()
        
        # Domain selection
        domain_layout = QHBoxLayout()
        domain_layout.addWidget(QLabel("도메인:"))
        
        self.domain_combo = QComboBox()
        self.domain_combo.setMinimumWidth(250)
        self.domain_combo.currentTextChanged.connect(self.on_domain_changed)
        self.domain_combo.setEnabled(False)  # 로그인 전에는 비활성화
        domain_layout.addWidget(self.domain_combo)
        
        self.nameserver_btn = QPushButton("🌐 네임서버 관리")
        self.nameserver_btn.clicked.connect(self.manage_nameservers)
        self.nameserver_btn.setEnabled(False)
        domain_layout.addWidget(self.nameserver_btn)
        
        self.refresh_domains_btn = QPushButton("🔄 도메인 새로고침")
        self.refresh_domains_btn.clicked.connect(self.load_domains)
        self.refresh_domains_btn.setEnabled(False)  # 로그인 전에는 비활성화
        domain_layout.addWidget(self.refresh_domains_btn)
        
        domain_layout.addStretch()
        dns_control_layout.addLayout(domain_layout)
        
        # Records table
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(7)
        self.records_table.setHorizontalHeaderLabels(["ID", "이름", "타입", "값", "TTL", "우선순위", "메모"])
        self.records_table.horizontalHeader().setStretchLastSection(True)
        self.records_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.records_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.records_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enable editing
        self.records_table.itemChanged.connect(self.on_item_changed)
        
        # Hide ID column
        self.records_table.setColumnHidden(0, True)
        
        # Adjust column widths
        header = self.records_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        dns_control_layout.addWidget(self.records_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ 레코드 추가")
        self.add_btn.clicked.connect(self.add_record)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ 레코드 수정")
        self.edit_btn.clicked.connect(self.edit_record)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ 레코드 삭제")
        self.delete_btn.clicked.connect(self.delete_record)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("💾 변경사항 저장")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("")
        button_layout.addWidget(self.save_btn)
        
        self.refresh_btn = QPushButton("🔄 레코드 새로고침")
        self.refresh_btn.clicked.connect(self.refresh_current_domain)
        button_layout.addWidget(self.refresh_btn)
        
        dns_control_layout.addLayout(button_layout)
        
        dns_control_widget.setLayout(dns_control_layout)
        self.tab_widget.addTab(dns_control_widget, "🔧 DNS 컨트롤")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("준비됨")
        
        # Initially disable buttons
        self.set_buttons_enabled(False)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+S for save
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_changes)
        
        # F5 for refresh
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self.refresh_current_domain)
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("파일")
        
        settings_action = QAction("⚙️ 설정", self)
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        api_status_action = QAction("🔍 API 접근 상태 확인", self)
        api_status_action.triggered.connect(self.show_api_status)
        file_menu.addAction(api_status_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("📥 레코드 내보내기", self)
        export_action.triggered.connect(self.export_records)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("편집")
        
        add_action = QAction("➕ 레코드 추가", self)
        add_action.triggered.connect(self.add_record)
        edit_menu.addAction(add_action)
        
        edit_action = QAction("✏️ 레코드 수정", self)
        edit_action.triggered.connect(self.edit_record)
        edit_menu.addAction(edit_action)
        
        delete_action = QAction("🗑️ 레코드 삭제", self)
        delete_action.triggered.connect(self.delete_record)
        edit_menu.addAction(delete_action)
        
        # Help menu
        help_menu = menubar.addMenu("도움말")
        
        about_action = QAction("정보", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        settings_action = QAction("⚙️ 설정", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
        api_status_action = QAction("🔍 API 상태", self)
        api_status_action.triggered.connect(self.show_api_status)
        toolbar.addAction(api_status_action)
        
        toolbar.addSeparator()
        
        # 전체 NS 체크 액션 추가
        self.check_ns_action = QAction("🔍 전체 NS 체크", self)
        self.check_ns_action.triggered.connect(self.check_all_nameservers)
        self.check_ns_action.setEnabled(False)  # 로그인 전까지 비활성화
        toolbar.addAction(self.check_ns_action)
        
        toolbar.addSeparator()
        
        refresh_action = QAction("🔄 새로고침", self)
        refresh_action.triggered.connect(self.load_records)
        toolbar.addAction(refresh_action)
        
        export_action = QAction("📥 내보내기", self)
        export_action.triggered.connect(self.export_records)
        toolbar.addAction(export_action)
    
    def on_dashboard_domain_selected(self, domain: str):
        """Handle domain selection from dashboard"""
        # Switch to DNS control tab
        self.tab_widget.setCurrentIndex(1)  # DNS 컨트롤 탭
        
        # Select domain in combo box
        for i in range(self.domain_combo.count()):
            item_data = self.domain_combo.itemData(i)
            if item_data == domain:
                self.domain_combo.setCurrentIndex(i)
                break
            # Also check text without indicators
            item_text = self.domain_combo.itemText(i)
            if domain in item_text:
                self.domain_combo.setCurrentIndex(i)
                break
    
    def show_context_menu(self, position):
        """Show context menu for records table"""
        if not self.records_table.selectedItems():
            return
        
        menu = QMenu()
        
        edit_action = QAction("✏️ 수정", self)
        edit_action.triggered.connect(self.edit_record)
        menu.addAction(edit_action)
        
        delete_action = QAction("🗑️ 삭제", self)
        delete_action.triggered.connect(self.delete_record)
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        copy_action = QAction("📋 내용 복사", self)
        copy_action.triggered.connect(self.copy_content)
        menu.addAction(copy_action)
        
        menu.exec(self.records_table.mapToGlobal(position))
    
    def copy_content(self):
        """Copy selected record content to clipboard"""
        current_row = self.records_table.currentRow()
        if current_row >= 0:
            content = self.records_table.item(current_row, 3).text()
            QApplication.clipboard().setText(content)
            self.status_bar.showMessage(f"복사됨: {content}", 2000)
    
    def set_buttons_enabled(self, enabled: bool):
        """Enable/disable action buttons"""
        self.add_btn.setEnabled(enabled)
        self.edit_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
    
    def check_all_nameservers(self):
        """Check nameservers for all domains with progress dialog"""
        if not self.client or not self.is_logged_in:
            QMessageBox.warning(self, "경고", "먼저 로그인해주세요")
            return
        
        # Get all active domains
        domains = []
        for i in range(1, self.domain_combo.count()):
            domain = self.domain_combo.itemData(i)
            if domain:
                domains.append(domain)
        
        if not domains:
            QMessageBox.information(self, "알림", "체크할 도메인이 없습니다")
            return
        
        # Create progress dialog
        self.ns_progress_dialog = QProgressDialog(
            "네임서버 체크 중...",
            "취소",
            0,
            len(domains),
            self
        )
        self.ns_progress_dialog.setWindowTitle("네임서버 체크")
        self.ns_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.ns_progress_dialog.setAutoClose(False)
        self.ns_progress_dialog.setAutoReset(False)
        self.ns_progress_dialog.show()
        
        # Disable check action during operation
        self.check_ns_action.setEnabled(False)
        self.check_ns_action.setText("🔄 체크 중...")
        
        # Create and start worker thread
        self.ns_check_worker = DomainNSWorker()
        self.ns_check_worker.set_credentials(
            self.client.api_key, 
            self.client.secret_api_key
        )
        self.ns_check_worker.progress_updated.connect(self.on_ns_check_progress)
        self.ns_check_worker.check_completed.connect(self.on_ns_check_completed)
        self.ns_check_worker.error_occurred.connect(self.on_ns_check_error)
        
        # Start check in thread
        from threading import Thread
        check_thread = Thread(target=self.ns_check_worker.start_check, args=(domains,))
        check_thread.daemon = True
        check_thread.start()
    
    def on_ns_check_progress(self, current: int, total: int, message: str):
        """Handle nameserver check progress updates"""
        if self.ns_progress_dialog:
            self.ns_progress_dialog.setValue(current)
            self.ns_progress_dialog.setLabelText(message)
            
            # Check if canceled
            if self.ns_progress_dialog.wasCanceled():
                # TODO: Implement cancellation in worker
                pass
    
    def on_ns_check_completed(self, external_ns_domains: list):
        """Handle nameserver check completion"""
        # Close progress dialog
        if self.ns_progress_dialog:
            self.ns_progress_dialog.close()
            self.ns_progress_dialog = None
        
        # Re-enable action
        self.check_ns_action.setEnabled(True)
        self.check_ns_action.setText("🔍 전체 NS 체크")
        
        # Update domain info with cached data
        cached_domains = self.ns_check_worker.get_cached_external_domains()
        for domain_info in cached_domains:
            domain = domain_info["domain"]
            self.domain_info[domain] = {
                "nameservers": domain_info["nameservers"],
                "is_porkbun": False
            }
        
        # Show summary
        if external_ns_domains:
            summary = f"외부 네임서버를 사용하는 도메인: {len(external_ns_domains)}개\n\n"
            for item in external_ns_domains[:10]:  # Show first 10
                domain = item["domain"]
                ns = item["nameservers"][0] if item["nameservers"] else "Unknown"
                summary += f"• {domain}: {ns}\n"
            if len(external_ns_domains) > 10:
                summary += f"... 외 {len(external_ns_domains) - 10}개"
            
            QMessageBox.information(self, "네임서버 체크 완료", summary)
        else:
            QMessageBox.information(
                self,
                "네임서버 체크 완료",
                "모든 도메인이 Porkbun 네임서버를 사용하고 있습니다."
            )
        
        # Update dashboard
        if self.dashboard_widget:
            self.dashboard_widget.update_domain_info(self.domain_info)
        
        # Update domain combo colors
        self.update_domain_combo_colors()
    
    def on_ns_check_error(self, error_msg: str):
        """Handle nameserver check error"""
        if self.ns_progress_dialog:
            self.ns_progress_dialog.close()
            self.ns_progress_dialog = None
        
        self.check_ns_action.setEnabled(True)
        self.check_ns_action.setText("🔍 전체 NS 체크")
        
        QMessageBox.critical(self, "오류", f"네임서버 체크 실패:\n{error_msg}")
    
    def update_domain_combo_colors(self):
        """Update domain combo box colors based on nameserver status"""
        for i in range(1, self.domain_combo.count()):
            domain_name = self.domain_combo.itemData(i)
            if domain_name and domain_name in self.domain_info:
                if not self.domain_info[domain_name].get("is_porkbun", True):
                    # 외부 네임서버 사용 시 빨간색
                    self.domain_combo.setItemData(i, QColor(255, 0, 0), Qt.ItemDataRole.ForegroundRole)
    
    def manage_nameservers(self):
        """Open nameserver management dialog"""
        if not self.current_domain:
            return
        
        dialog = NameserverDialog(self.client, self.current_domain, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reload domain list to update nameserver status
            self.load_domains()
    
    def perform_login(self):
        """Perform login with API credentials"""
        if self.is_logged_in:
            # 로그아웃
            reply = QMessageBox.question(
                self,
                "로그아웃",
                "로그아웃하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.logout()
            return
        
        # 로그인 중이면 중복 실행 방지
        if self.login_worker and self.login_worker.isRunning():
            QMessageBox.information(self, "알림", "이미 로그인 중입니다...")
            return
        
        # Try to load from config first
        config_file = Path.home() / ".porkbun_dns" / "config.json"
        
        # Load from environment or config
        load_dotenv()
        api_key = os.getenv("PORKBUN_API_KEY")
        secret_key = os.getenv("PORKBUN_SECRET_API_KEY")
        
        if not api_key and config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    api_key = config.get("api_key")
                    secret_key = config.get("secret_api_key")
            except Exception:
                pass
        
        if api_key and secret_key:
            # 저장된 자격증명으로 비동기 로그인
            self.start_async_login(api_key, secret_key)
        else:
            # 설정 대화상자 표시
            self.show_settings()
    
    def start_async_login(self, api_key: str, secret_key: str):
        """Start asynchronous login process"""
        # UI 상태 업데이트
        self.login_status_label.setText("🔄 로그인 중...")
        self.login_status_label.setStyleSheet("padding: 5px; font-weight: bold; color: #FF9800;")
        self.login_btn.setEnabled(False)  # 로그인 버튼 비활성화
        self.login_progress.show()  # 프로그레스 바 표시
        self.status_bar.showMessage("로그인 진행 중...")
        
        # 로그인 쓰레드 생성 및 실행
        self.login_worker = LoginWorker(api_key, secret_key)
        self.login_worker.success.connect(self.on_login_success)
        self.login_worker.error.connect(self.on_login_error)
        self.login_worker.status.connect(self.on_login_status)
        self.login_worker.start()
    
    def on_login_status(self, message: str):
        """Handle login status updates"""
        self.status_bar.showMessage(message)
    
    def on_login_success(self, client: PorkbunDNS, domains: list):
        """Handle successful login"""
        self.client = client
        self.is_logged_in = True
        self.login_status_label.setText("✅ 로그인됨")
        self.login_status_label.setStyleSheet("padding: 5px; font-weight: bold; color: #4CAF50;")
        self.login_btn.setText("🚪 로그아웃")
        self.login_btn.setEnabled(True)  # 버튼 다시 활성화
        self.login_progress.hide()  # 프로그레스 바 숨김
        
        # 로그인 성공 시 UI 활성화
        self.domain_combo.setEnabled(True)
        self.refresh_domains_btn.setEnabled(True)
        self.check_ns_action.setEnabled(True)  # 툴바의 NS 체크 액션 활성화
        self.set_buttons_enabled(False)  # 도메인 선택 전까지는 비활성화
        
        self.status_bar.showMessage("Porkbun API 연결됨", 2000)
        
        # 이미 로드된 도메인 목록 처리
        if domains:
            self.process_domains(domains)
            # 저장된 네임서버 설정 로드
            self.load_cached_ns_info()
        else:
            # 도메인이 없거나 로드 실패 시 다시 시도
            self.load_domains()
    
    def on_login_error(self, error_msg: str):
        """Handle login error"""
        self.login_status_label.setText("⚠️ 로그인되지 않음")
        self.login_status_label.setStyleSheet("padding: 5px; font-weight: bold; color: #ff6600;")
        self.login_btn.setEnabled(True)  # 버튼 다시 활성화
        self.login_progress.hide()  # 프로그레스 바 숨김
        self.status_bar.showMessage("로그인 실패", 3000)
        
        QMessageBox.warning(self, "로그인 실패", error_msg)
        # 설정 대화상자 표시
        self.show_settings()
    
    def load_cached_ns_info(self):
        """Load cached nameserver information"""
        try:
            # Create worker to load cached info
            worker = DomainNSWorker()
            cached_domains = worker.get_cached_external_domains()
            
            if cached_domains:
                # Update domain info with cached data
                for domain_info in cached_domains:
                    domain = domain_info["domain"]
                    self.domain_info[domain] = {
                        "nameservers": domain_info["nameservers"],
                        "is_porkbun": False
                    }
                
                # Update UI
                if self.dashboard_widget:
                    self.dashboard_widget.update_domain_info(self.domain_info)
                
                self.update_domain_combo_colors()
                
                # Show status
                self.status_bar.showMessage(
                    f"캐시된 네임서버 정보 로드됨: 외부 NS {len(cached_domains)}개 도메인",
                    3000
                )
        except Exception as e:
            # Silently ignore if no cached data
            pass
    
    def logout(self):
        """Logout and clear session"""
        # 로그인 쓰레드가 실행 중이면 중지
        if self.login_worker and self.login_worker.isRunning():
            self.login_worker.terminate()
            self.login_worker.wait()
        
        self.client = None
        self.is_logged_in = False
        self.current_domain = None
        self.current_records = []
        self.modified_records = {}
        self.domain_info = {}
        
        # UI 업데이트
        self.login_status_label.setText("⚠️ 로그인되지 않음")
        self.login_status_label.setStyleSheet("padding: 5px; font-weight: bold; color: #ff6600;")
        self.login_btn.setText("🔐 로그인")
        self.login_btn.setEnabled(True)
        
        # 컨트롤 비활성화
        self.domain_combo.setEnabled(False)
        self.domain_combo.clear()
        self.refresh_domains_btn.setEnabled(False)
        self.nameserver_btn.setEnabled(False)
        self.set_buttons_enabled(False)
        self.records_table.setRowCount(0)
        
        self.status_bar.showMessage("로그아웃됨", 2000)
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            api_key, secret_key = dialog.get_credentials()
            if api_key and secret_key:
                dialog.save_settings()  # 설정 저장
                self.start_async_login(api_key, secret_key)
    
    def process_domains(self, domains: list):
        """Process and display domains (called from login thread)"""
        # Save current selection
        current_selection = self.current_domain
        
        # Temporarily disconnect the signal to prevent auto-loading
        if self.domain_combo.receivers(self.domain_combo.currentTextChanged) > 0:
            self.domain_combo.currentTextChanged.disconnect()
        self.domain_combo.clear()
        
        # Add empty item first for no selection
        self.domain_combo.addItem("-- 도메인을 선택하세요 --")
        
        domain_count = 0
        self.domain_info = {}
        active_domains = []
        
        for domain in domains:
            if domain.get("status") == "ACTIVE":
                domain_name = domain.get("domain")
                domain_count += 1
                active_domains.append(domain_name)
                
                # 간단한 도메인 정보만 저장 (네임서버 체크는 나중에)
                self.domain_combo.addItem(domain_name, domain_name)
                self.domain_info[domain_name] = {
                    "nameservers": [],
                    "is_porkbun": True
                }
        
        # Restore previous selection if it exists
        if current_selection:
            index = self.domain_combo.findText(current_selection)
            if index >= 0:
                self.domain_combo.setCurrentIndex(index)
        
        if domain_count > 0:
            self.status_bar.showMessage(f"{domain_count}개 도메인 로드됨", 2000)
            
            # Update dashboard with domains and initial domain info
            if self.dashboard_widget:
                self.dashboard_widget.set_domains(active_domains)
                # Pass initial domain info (all assumed Porkbun until checked)
                self.dashboard_widget.update_domain_info(self.domain_info)
            
            # 백그라운드에서 네임서버 정보 체크 (GUI 차단 없이)
            # 새로운 DomainNSWorker는 이미 재작성되어 별도 구현이 있음
            # 기존 체크는 주석 처리 (전체 NS 체크 버튼 사용)
            # if self.client and active_domains:
            #     self.ns_worker = DomainNSWorker(self.client, active_domains)
            #     self.ns_worker.finished.connect(self.update_domain_info)
            #     self.ns_worker.start()
        else:
            self.status_bar.showMessage("활성 도메인이 없음", 2000)
        
        # Reconnect the signal
        self.domain_combo.currentTextChanged.connect(self.on_domain_changed)
    
    
    def load_domains(self):
        """Load domains from API"""
        if not self.client or not self.is_logged_in:
            QMessageBox.warning(self, "경고", "먼저 로그인해주세요")
            return
        
        self.status_bar.showMessage("도메인 불러오는 중...")
        
        try:
            domains = self.client.get_domains()
            self.process_domains(domains)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"도메인 로드 실패: {str(e)}")
            self.status_bar.showMessage("도메인 로드 실패", 2000)
    
    def on_domain_changed(self, domain_text: str):
        """Handle domain selection change"""
        # Get actual domain name from user data
        current_index = self.domain_combo.currentIndex()
        if current_index > 0:  # Skip placeholder
            domain = self.domain_combo.itemData(current_index)
            if not domain:  # Fallback to text if no data
                # Remove indicators from text
                domain = domain_text.replace("🐷 ", "").replace("⚠️ ", "").replace(" (외부 NS)", "")
            
            if domain:
                self.current_domain = domain
                self.set_buttons_enabled(True)
                self.nameserver_btn.setEnabled(True)
                
                # Show nameserver status in status bar
                if domain in self.domain_info:
                    if self.domain_info[domain].get("is_porkbun", True):
                        self.status_bar.showMessage(f"{domain} - Porkbun 네임서버 사용 중", 3000)
                    else:
                        ns_list = self.domain_info[domain].get("nameservers", [])
                        if ns_list:
                            self.status_bar.showMessage(f"{domain} - ⚠️ 외부 네임서버 ({ns_list[0]}...)", 3000)
                        else:
                            self.status_bar.showMessage(f"{domain} - ⚠️ 외부 네임서버 사용 중", 3000)
                
                self.load_records()
            return
        
        # No domain selected
        self.current_domain = None
        self.set_buttons_enabled(False)
        self.nameserver_btn.setEnabled(False)
        self.records_table.setRowCount(0)
        if domain_text == "-- 도메인을 선택하세요 --":
            self.status_bar.showMessage("도메인을 선택해주세요", 2000)
    
    def load_records(self):
        """Load DNS records for current domain"""
        if not self.client or not self.current_domain:
            return
        
        self.status_bar.showMessage(f"{self.current_domain}의 레코드 불러오는 중...")
        
        try:
            self.current_records = self.client.get_dns_records(self.current_domain)
            self.populate_table()
            self.status_bar.showMessage(f"{len(self.current_records)}개 레코드 로드됨", 2000)
        except Exception as e:
            error_msg = str(e)
            if "API 접근이 비활성화" in error_msg:
                # Show detailed message for API access error
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("API 접근 설정 필요")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText(f"도메인 '{self.current_domain}'에 대한 API 접근이 비활성화되어 있습니다.")
                msg_box.setDetailedText(error_msg)
                msg_box.setInformativeText("Porkbun 웹사이트에서 API ACCESS를 활성화해주세요.")
                msg_box.exec()
            else:
                QMessageBox.critical(self, "오류", f"레코드 로드 실패: {error_msg}")
            self.status_bar.showMessage("레코드 로드 실패", 2000)
    
    def populate_table(self):
        """Populate the records table"""
        # Temporarily disconnect item changed signal
        self.records_table.itemChanged.disconnect()
        
        self.records_table.setRowCount(len(self.current_records))
        self.modified_records.clear()  # Clear modifications when reloading
        
        for row, record in enumerate(self.current_records):
            # ID (hidden)
            id_item = QTableWidgetItem(record.get("id", ""))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Non-editable
            self.records_table.setItem(row, 0, id_item)
            
            # Name
            name = record.get("name", "@")
            if name == self.current_domain:
                name = "@"
            name_item = QTableWidgetItem(name)
            self.records_table.setItem(row, 1, name_item)
            
            # Type (non-editable)
            type_item = QTableWidgetItem(record.get("type", ""))
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Non-editable
            bold_font = QFont()
            bold_font.setPointSize(9)
            bold_font.setBold(True)
            type_item.setFont(bold_font)
            
            # Color code by type
            record_type = record.get("type", "")
            if record_type == "A":
                type_item.setForeground(QColor(0, 128, 0))
            elif record_type == "AAAA":
                type_item.setForeground(QColor(0, 100, 0))
            elif record_type == "CNAME":
                type_item.setForeground(QColor(0, 0, 200))
            elif record_type == "MX":
                type_item.setForeground(QColor(200, 0, 0))
            elif record_type == "TXT":
                type_item.setForeground(QColor(128, 0, 128))
            
            self.records_table.setItem(row, 2, type_item)
            
            # Content (editable)
            content_item = QTableWidgetItem(record.get("content", ""))
            self.records_table.setItem(row, 3, content_item)
            
            # TTL (editable)
            ttl_item = QTableWidgetItem(str(record.get("ttl", "")))
            self.records_table.setItem(row, 4, ttl_item)
            
            # Priority (editable for MX records)
            prio = record.get("prio", "")
            prio_item = QTableWidgetItem(str(prio) if prio else "")
            if record_type not in ["MX", "SRV"]:
                prio_item.setFlags(prio_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.records_table.setItem(row, 5, prio_item)
            
            # Notes (editable)
            notes_item = QTableWidgetItem(record.get("notes", ""))
            self.records_table.setItem(row, 6, notes_item)
        
        # Reconnect the signal
        self.records_table.itemChanged.connect(self.on_item_changed)
        
        # Reset save button
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("")
    
    def add_record(self):
        """Add a new DNS record"""
        if not self.client or not self.current_domain:
            return
        
        dialog = RecordDialog(self.current_domain, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_record_data()
            
            self.status_bar.showMessage("Adding record...")
            
            try:
                result = self.client.create_dns_record(
                    domain=self.current_domain,
                    record_type=data["type"],
                    content=data["content"],
                    name=data["name"],
                    ttl=data["ttl"],
                    prio=data.get("prio"),
                    notes=data["notes"] if data["notes"] else None
                )
                
                if result.get("status") == "SUCCESS":
                    QMessageBox.information(self, "Success", "Record added successfully!")
                    self.load_records()
                else:
                    QMessageBox.warning(self, "Failed", f"Failed to add record: {result.get('message')}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error adding record: {str(e)}")
                self.status_bar.showMessage("Failed to add record", 2000)
    
    def edit_record(self):
        """Edit selected DNS record"""
        current_row = self.records_table.currentRow()
        if current_row < 0 or current_row >= len(self.current_records):
            QMessageBox.warning(self, "Warning", "Please select a record to edit")
            return
        
        record = self.current_records[current_row]
        dialog = RecordDialog(self.current_domain, record, parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_record_data()
            
            self.status_bar.showMessage("Updating record...")
            
            try:
                result = self.client.edit_dns_record(
                    domain=self.current_domain,
                    record_id=record.get("id"),
                    record_type=data["type"],
                    content=data["content"],
                    name=data["name"],
                    ttl=data["ttl"],
                    prio=data.get("prio"),
                    notes=data["notes"] if data["notes"] else None
                )
                
                if result.get("status") == "SUCCESS":
                    QMessageBox.information(self, "Success", "Record updated successfully!")
                    self.load_records()
                else:
                    QMessageBox.warning(self, "Failed", f"Failed to update record: {result.get('message')}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error updating record: {str(e)}")
                self.status_bar.showMessage("Failed to update record", 2000)
    
    def delete_record(self):
        """Delete selected DNS record(s)"""
        selected_rows = set()
        for item in self.records_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select record(s) to delete")
            return
        
        record_count = len(selected_rows)
        msg = f"Are you sure you want to delete {record_count} record(s)?"
        
        reply = QMessageBox.question(self, "Confirm Delete", msg,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.status_bar.showMessage("Deleting records...")
            
            errors = []
            for row in selected_rows:
                if row < len(self.current_records):
                    record = self.current_records[row]
                    try:
                        result = self.client.delete_dns_record(self.current_domain, record.get("id"))
                        if result.get("status") != "SUCCESS":
                            errors.append(f"Failed to delete {record.get('name')}: {result.get('message')}")
                    except Exception as e:
                        errors.append(f"Error deleting {record.get('name')}: {str(e)}")
            
            if errors:
                QMessageBox.warning(self, "Errors", "\n".join(errors))
            else:
                QMessageBox.information(self, "Success", f"Deleted {record_count} record(s)")
            
            self.load_records()
    
    def export_records(self):
        """Export DNS records"""
        if not self.current_domain or not self.current_records:
            QMessageBox.warning(self, "Warning", "No records to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Records", f"{self.current_domain}_dns_records.json",
            "JSON Files (*.json);;CSV Files (*.csv);;Zone Files (*.zone);;All Files (*.*)"
        )
        
        if file_path:
            try:
                if file_path.endswith(".csv"):
                    content = self.client.export_dns_records(self.current_domain, "csv")
                elif file_path.endswith(".zone"):
                    content = self.client.export_dns_records(self.current_domain, "zone")
                else:
                    content = self.client.export_dns_records(self.current_domain, "json")
                
                with open(file_path, "w") as f:
                    f.write(content)
                
                QMessageBox.information(self, "성공", f"레코드가 {file_path}로 내보내짐")
                self.status_bar.showMessage(f"{file_path}로 내보내짐", 3000)
            except Exception as e:
                QMessageBox.critical(self, "오류", f"내보내기 실패: {str(e)}")
    
    def on_item_changed(self, item):
        """Handle item changes in the table"""
        if not item:
            return
        
        row = item.row()
        col = item.column()
        
        # Don't track changes to ID or Type columns
        if col in [0, 2]:
            return
        
        # Get the record ID
        record_id = self.records_table.item(row, 0).text()
        
        if record_id not in self.modified_records:
            self.modified_records[record_id] = {}
        
        # Map column to field name
        field_map = {
            1: "name",
            3: "content",
            4: "ttl",
            5: "prio",
            6: "notes"
        }
        
        field = field_map.get(col)
        if field:
            # Store the new value
            value = item.text()
            
            # Convert TTL to int if it's a number
            if field == "ttl":
                try:
                    value = int(value) if value else 600
                except ValueError:
                    value = 600
                    item.setText(str(value))
            
            # Convert priority to int if it's a number
            if field == "prio" and value:
                try:
                    value = int(value)
                except ValueError:
                    value = ""
                    item.setText("")
            
            self.modified_records[record_id][field] = value
            
            # Highlight the modified cell
            item.setBackground(QColor(255, 255, 200))  # Light yellow
            
            # Enable save button
            self.save_btn.setEnabled(True)
            self.save_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
            
            # Update status
            self.status_bar.showMessage(f"수정됨: {len(self.modified_records)}개 레코드 변경됨", 2000)
    
    def refresh_current_domain(self):
        """Refresh records for the current domain"""
        if self.modified_records:
            reply = QMessageBox.question(
                self,
                "저장되지 않은 변경사항",
                "저장되지 않은 변경사항이 있습니다. 새로고침하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        if self.current_domain:
            self.load_records()
        else:
            self.status_bar.showMessage("선택된 도메인이 없습니다", 2000)
    
    def save_changes(self):
        """Save all modified records"""
        if not self.modified_records:
            self.status_bar.showMessage("변경사항이 없습니다", 2000)
            return
        
        if not self.client or not self.current_domain:
            return
        
        errors = []
        success_count = 0
        
        self.status_bar.showMessage("변경사항 저장 중...")
        
        for record_id, changes in self.modified_records.items():
            # Find the original record
            original_record = None
            for record in self.current_records:
                if record.get("id") == record_id:
                    original_record = record
                    break
            
            if not original_record:
                continue
            
            # Prepare the update data
            try:
                result = self.client.edit_dns_record(
                    domain=self.current_domain,
                    record_id=record_id,
                    record_type=original_record.get("type"),
                    content=changes.get("content", original_record.get("content")),
                    name=changes.get("name", original_record.get("name", "")),
                    ttl=changes.get("ttl", original_record.get("ttl", 600)),
                    prio=changes.get("prio", original_record.get("prio")) if original_record.get("type") in ["MX", "SRV"] else None,
                    notes=changes.get("notes", original_record.get("notes", ""))
                )
                
                if result.get("status") == "SUCCESS":
                    success_count += 1
                else:
                    errors.append(f"레코드 {record_id} 업데이트 실패: {result.get('message')}")
            except Exception as e:
                errors.append(f"레코드 {record_id} 업데이트 오류: {str(e)}")
        
        if errors:
            QMessageBox.warning(self, "일부 오류 발생", "\n".join(errors))
        
        if success_count > 0:
            QMessageBox.information(self, "저장 완료", f"{success_count}개 레코드가 성공적으로 업데이트되었습니다.")
            # Reload to get fresh data
            self.load_records()
        
        self.status_bar.showMessage(f"{success_count}개 레코드 저장됨", 2000)
    
    def show_api_status(self):
        """Show API access status dialog"""
        if not self.client or not self.is_logged_in:
            QMessageBox.warning(self, "경고", "먼저 로그인해주세요")
            return
        
        dialog = APIAccessDialog(self.client, self)
        dialog.exec()
        
        # Reload domains after checking
        self.load_domains()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "Porkbun DNS 관리자 정보",
                         "Porkbun DNS 관리자 v0.1.0\n\n"
                         "Porkbun API를 사용한\n"
                         "DNS 레코드 관리 GUI 프로그램\n\n"
                         "PyQt6와 Python으로 개발")


def main():
    """Main entry point for GUI"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look
    
    # Set default font to avoid font warnings on Windows
    from PyQt6.QtGui import QFont
    if sys.platform == "win32":
        # Use a standard Windows font
        default_font = QFont("Segoe UI", 9)
        app.setFont(default_font)
    
    window = DNSManagerGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()