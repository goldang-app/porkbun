"""Dashboard Widget for Domain Group Management"""
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QInputDialog, QColorDialog, QSplitter, QFrame,
    QScrollArea, QGridLayout, QToolButton, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDrag, QColor, QPainter, QBrush, QPen, QFont, QIcon


class DomainItem(QFrame):
    """Custom widget for domain display in groups"""
    clicked = pyqtSignal(str)
    remove_clicked = pyqtSignal(str)  # Signal for remove button
    
    def __init__(self, domain: str, show_remove: bool = False, is_porkbun_ns: bool = True, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.show_remove = show_remove
        self.is_porkbun_ns = is_porkbun_ns
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            DomainItem {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
            DomainItem:hover {
                background-color: #f0f0f0;
                border: 1px solid #999;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Domain label with color based on nameserver status
        display_text = self.domain
        if not self.is_porkbun_ns:
            display_text = f"⚠️ {self.domain}"
        
        self.label = QLabel(display_text)
        if self.is_porkbun_ns:
            self.label.setStyleSheet("font-size: 12px; color: #333;")
        else:
            self.label.setStyleSheet("font-size: 12px; color: #d32f2f; font-weight: bold;")
            self.label.setToolTip("외부 네임서버 사용 중")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        # Remove button (only for grouped domains)
        if self.show_remove:
            self.remove_btn = QToolButton()
            self.remove_btn.setText("−")  # Minus sign
            self.remove_btn.setStyleSheet("""
                QToolButton {
                    background-color: #ff5252;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QToolButton:hover {
                    background-color: #ff1744;
                }
            """)
            self.remove_btn.setToolTip("미분류로 이동")
            self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.domain))
            layout.addWidget(self.remove_btn)
        
        # DNS control button
        self.dns_btn = QToolButton()
        self.dns_btn.setText("DNS")
        self.dns_btn.setStyleSheet("""
            QToolButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 10px;
            }
            QToolButton:hover {
                background-color: #45a049;
            }
        """)
        self.dns_btn.setToolTip("DNS 레코드 관리")
        self.dns_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dns_btn.clicked.connect(lambda: self.clicked.emit(self.domain))
        layout.addWidget(self.dns_btn)
        
        self.setLayout(layout)
        self.setMaximumHeight(40)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.domain)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)


class DomainGroup(QFrame):
    """Custom widget for domain group"""
    domain_dropped = pyqtSignal(str, str)  # domain, group_name
    domain_clicked = pyqtSignal(str)
    group_deleted = pyqtSignal(str)
    domain_removed = pyqtSignal(str)  # Signal when domain is removed from group
    
    def __init__(self, name: str, color: str = "#f0f0f0", parent=None):
        super().__init__(parent)
        self.name = name
        self.color = color
        self.domains = []
        self.setup_ui()
        self.setAcceptDrops(True)
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setMinimumHeight(150)
        self.update_style()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Group name label
        self.name_label = QLabel(self.name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        # Settings button
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        self.settings_btn.setStyleSheet("""
            QToolButton {
                border: none;
                font-size: 16px;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        self.settings_btn.clicked.connect(self.show_context_menu)
        header_layout.addWidget(self.settings_btn)
        
        layout.addLayout(header_layout)
        
        # Domains container with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.domains_container = QWidget()
        self.domains_layout = QVBoxLayout()
        self.domains_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.domains_container.setLayout(self.domains_layout)
        scroll.setWidget(self.domains_container)
        
        layout.addWidget(scroll)
        
        # Drop hint label (shown when empty)
        self.drop_hint = QLabel("드래그하여 도메인 추가")
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_hint.setStyleSheet("color: #999; font-style: italic;")
        self.domains_layout.addWidget(self.drop_hint)
        
        self.setLayout(layout)
        
    def update_style(self):
        self.setStyleSheet(f"""
            DomainGroup {{
                background-color: {self.color};
                border: 2px solid #ddd;
                border-radius: 8px;
            }}
        """)
        
    def add_domain(self, domain: str, is_porkbun: bool = True):
        if domain not in self.domains:
            self.domains.append(domain)
            
            # Hide drop hint
            self.drop_hint.hide()
            
            # Add domain item with remove button
            domain_item = DomainItem(domain, show_remove=True, is_porkbun_ns=is_porkbun)
            domain_item.clicked.connect(self.domain_clicked.emit)
            domain_item.remove_clicked.connect(self.handle_remove_domain)
            self.domains_layout.addWidget(domain_item)
    
    def handle_remove_domain(self, domain: str):
        """Handle domain removal from group"""
        self.remove_domain(domain)
        # Emit signal to parent widget
        self.domain_removed.emit(domain)
            
    def remove_domain(self, domain: str):
        if domain in self.domains:
            self.domains.remove(domain)
            
            # Remove domain widget
            for i in range(self.domains_layout.count()):
                widget = self.domains_layout.itemAt(i).widget()
                if isinstance(widget, DomainItem) and widget.domain == domain:
                    widget.deleteLater()
                    break
                    
            # Show drop hint if empty (but make sure drop_hint still exists)
            if not self.domains and hasattr(self, 'drop_hint'):
                self.drop_hint.show()
                
    def show_context_menu(self):
        menu = QMenu(self)
        
        rename_action = menu.addAction("이름 변경")
        rename_action.triggered.connect(self.rename_group)
        
        color_action = menu.addAction("색상 변경")
        color_action.triggered.connect(self.change_color)
        
        menu.addSeparator()
        
        delete_action = menu.addAction("그룹 삭제")
        delete_action.triggered.connect(lambda: self.group_deleted.emit(self.name))
        
        menu.exec(self.settings_btn.mapToGlobal(QPoint(0, self.settings_btn.height())))
        
    def rename_group(self):
        text, ok = QInputDialog.getText(self, "그룹 이름 변경", "새 이름:", text=self.name)
        if ok and text:
            self.name = text
            self.name_label.setText(text)
            
    def change_color(self):
        color = QColorDialog.getColor(QColor(self.color), self, "그룹 색상 선택")
        if color.isValid():
            self.color = color.name()
            self.update_style()
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                DomainGroup {{
                    background-color: {self.color};
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                }}
            """)
            
    def dragLeaveEvent(self, event):
        self.update_style()
        
    def dropEvent(self, event: QDropEvent):
        domain = event.mimeData().text()
        self.domain_dropped.emit(domain, self.name)
        event.acceptProposedAction()
        self.update_style()


class DashboardWidget(QWidget):
    """Main Dashboard Widget for managing domain groups"""
    domain_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.groups = {}  # {group_name: DomainGroup}
        self.all_domains = []
        self.domain_info = {}  # {domain: {"is_porkbun": bool}}
        self.config_file = Path.home() / ".porkbun_dashboard.json"
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.add_group_btn = QPushButton("➕ 새 그룹")
        self.add_group_btn.clicked.connect(self.add_group)
        toolbar_layout.addWidget(self.add_group_btn)
        
        toolbar_layout.addStretch()
        
        self.save_btn = QPushButton("💾 저장")
        self.save_btn.clicked.connect(self.save_config)
        toolbar_layout.addWidget(self.save_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Main content area
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Ungrouped domains panel
        ungrouped_frame = QFrame()
        ungrouped_frame.setFrameStyle(QFrame.Shape.Box)
        ungrouped_layout = QVBoxLayout()
        
        ungrouped_label = QLabel("미분류 도메인")
        ungrouped_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        ungrouped_layout.addWidget(ungrouped_label)
        
        self.ungrouped_scroll = QScrollArea()
        self.ungrouped_scroll.setWidgetResizable(True)
        self.ungrouped_container = QWidget()
        self.ungrouped_layout = QVBoxLayout()
        self.ungrouped_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.ungrouped_container.setLayout(self.ungrouped_layout)
        self.ungrouped_scroll.setWidget(self.ungrouped_container)
        ungrouped_layout.addWidget(self.ungrouped_scroll)
        
        ungrouped_frame.setLayout(ungrouped_layout)
        self.splitter.addWidget(ungrouped_frame)
        
        # Groups panel
        self.groups_scroll = QScrollArea()
        self.groups_scroll.setWidgetResizable(True)
        self.groups_container = QWidget()
        self.groups_layout = QHBoxLayout()
        self.groups_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.groups_container.setLayout(self.groups_layout)
        self.groups_scroll.setWidget(self.groups_container)
        self.splitter.addWidget(self.groups_scroll)
        
        self.splitter.setSizes([200, 800])
        
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        
    def add_group(self):
        text, ok = QInputDialog.getText(self, "새 그룹", "그룹 이름:")
        if ok and text and text not in self.groups:
            color = QColorDialog.getColor(QColor("#e3f2fd"), self, "그룹 색상 선택")
            if color.isValid():
                self.create_group(text, color.name())
                self.save_config()
                
    def create_group(self, name: str, color: str = "#e3f2fd"):
        group = DomainGroup(name, color)
        group.domain_dropped.connect(self.handle_domain_drop)
        group.domain_clicked.connect(self.domain_selected.emit)
        group.group_deleted.connect(self.delete_group)
        group.domain_removed.connect(self.handle_domain_removed)
        
        self.groups[name] = group
        self.groups_layout.addWidget(group)
        
    def delete_group(self, name: str):
        reply = QMessageBox.question(self, "그룹 삭제", 
                                    f"'{name}' 그룹을 삭제하시겠습니까?\n그룹 내 도메인은 미분류로 이동합니다.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if name in self.groups:
                group = self.groups[name]
                
                # Move domains back to ungrouped
                for domain in group.domains[:]:
                    self.add_ungrouped_domain(domain)
                    
                # Remove group
                group.deleteLater()
                del self.groups[name]
                self.save_config()
                
    def handle_domain_drop(self, domain: str, group_name: str):
        # Remove from all other groups and ungrouped
        self.remove_domain_from_all(domain)
        
        # Add to target group with nameserver status
        if group_name in self.groups:
            is_porkbun = self.domain_info.get(domain, {}).get("is_porkbun", True)
            self.groups[group_name].add_domain(domain, is_porkbun)
            self.save_config()
    
    def handle_domain_removed(self, domain: str):
        """Handle domain removal from a group - move back to ungrouped"""
        self.add_ungrouped_domain(domain)
        self.save_config()
            
    def remove_domain_from_all(self, domain: str):
        # Remove from ungrouped
        for i in range(self.ungrouped_layout.count()):
            widget = self.ungrouped_layout.itemAt(i).widget()
            if isinstance(widget, DomainItem) and widget.domain == domain:
                widget.deleteLater()
                break
                
        # Remove from all groups
        for group in self.groups.values():
            group.remove_domain(domain)
            
    def add_ungrouped_domain(self, domain: str):
        # Check if already exists in ungrouped
        for i in range(self.ungrouped_layout.count()):
            widget = self.ungrouped_layout.itemAt(i).widget()
            if isinstance(widget, DomainItem) and widget.domain == domain:
                return  # Already exists
        
        # Check nameserver status
        is_porkbun = self.domain_info.get(domain, {}).get("is_porkbun", True)
        
        domain_item = DomainItem(domain, show_remove=False, is_porkbun_ns=is_porkbun)
        domain_item.clicked.connect(self.domain_selected.emit)
        self.ungrouped_layout.addWidget(domain_item)
        
    def set_domains(self, domains: List[str]):
        """Set the list of all domains"""
        self.all_domains = domains
        self.refresh_domains()
    
    def update_domain_info(self, domain_info: Dict[str, Dict]):
        """Update domain nameserver information"""
        self.domain_info = domain_info
        self.refresh_domains()  # Refresh display with new info
        
    def refresh_domains(self):
        """Refresh domain display based on current grouping"""
        # Clear ungrouped
        while self.ungrouped_layout.count():
            item = self.ungrouped_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Refresh all group displays with updated nameserver info
        for group_name, group in self.groups.items():
            # Clear current domains in group (but keep drop_hint)
            for i in reversed(range(group.domains_layout.count())):
                item = group.domains_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), DomainItem):
                    item.widget().deleteLater()
            
            # Re-add domains with updated status
            domains_copy = group.domains.copy()
            group.domains = []
            
            # Show drop_hint if no domains
            if not domains_copy and hasattr(group, 'drop_hint'):
                group.drop_hint.show()
            
            for domain in domains_copy:
                if domain in self.all_domains:
                    is_porkbun = self.domain_info.get(domain, {}).get("is_porkbun", True)
                    group.add_domain(domain, is_porkbun)
        
        # Get grouped domains
        grouped_domains = set()
        for group in self.groups.values():
            grouped_domains.update(group.domains)
            
        # Add ungrouped domains
        for domain in self.all_domains:
            if domain not in grouped_domains:
                self.add_ungrouped_domain(domain)
                
    def save_config(self):
        """Save dashboard configuration"""
        config = {
            "groups": {}
        }
        
        for name, group in self.groups.items():
            config["groups"][name] = {
                "color": group.color,
                "domains": group.domains
            }
            
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "저장 실패", f"설정 저장 실패: {str(e)}")
            
    def load_group_domains(self, group_name: str, domains: List[str]):
        """Load domains into a group"""
        if group_name in self.groups:
            for domain in domains:
                # Only add if domain exists in all_domains
                if not self.all_domains or domain in self.all_domains:
                    is_porkbun = self.domain_info.get(domain, {}).get("is_porkbun", True)
                    self.groups[group_name].add_domain(domain, is_porkbun)
    
    def load_config(self):
        """Load dashboard configuration"""
        if not self.config_file.exists():
            # Create default groups
            self.create_group("개인", "#e3f2fd")
            self.create_group("업무", "#fff3e0")
            self.create_group("프로젝트", "#f3e5f5")
            return
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            for name, group_data in config.get("groups", {}).items():
                self.create_group(name, group_data.get("color", "#e3f2fd"))
                # Load domains for this group after GUI loads
                if "domains" in group_data:
                    QTimer.singleShot(100, lambda n=name, d=group_data["domains"]: self.load_group_domains(n, d))
                
        except Exception as e:
            QMessageBox.warning(self, "로드 실패", f"설정 로드 실패: {str(e)}")
            # Create default groups on error
            self.create_group("개인", "#e3f2fd")
            self.create_group("업무", "#fff3e0")
            self.create_group("프로젝트", "#f3e5f5")