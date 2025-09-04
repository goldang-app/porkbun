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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9ff);
                border: 1px solid #e3e8f0;
                border-radius: 8px;
                padding: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            }
            DomainItem:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f4ff, stop:1 #e8f0ff);
                border: 1px solid #6b7de8;
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(107, 125, 232, 0.15);
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
            self.label.setStyleSheet("font-size: 13px; color: #2c3e50; font-weight: 500;")
        else:
            self.label.setStyleSheet("font-size: 13px; color: #e74c3c; font-weight: 600;")
            self.label.setToolTip("외부 네임서버 사용 중")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        # Remove button (only for grouped domains)
        if self.show_remove:
            self.remove_btn = QToolButton()
            self.remove_btn.setText("−")  # Minus sign
            self.remove_btn.setStyleSheet("""
                QToolButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff6b75, stop:1 #ff5252);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 12px;
                    font-weight: 600;
                    box-shadow: 0 2px 4px rgba(255, 107, 117, 0.3);
                }
                QToolButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff4757, stop:1 #ff3742);
                    box-shadow: 0 4px 8px rgba(255, 107, 117, 0.4);
                }
                QToolButton:pressed {
                    background: #e63946;
                    box-shadow: 0 1px 2px rgba(255, 107, 117, 0.5);
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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5dcea4, stop:1 #4caf50);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
                box-shadow: 0 2px 4px rgba(76, 175, 80, 0.3);
            }
            QToolButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45a049, stop:1 #388e3c);
                box-shadow: 0 4px 8px rgba(76, 175, 80, 0.4);
            }
            QToolButton:pressed {
                background: #2e7d32;
                box-shadow: 0 1px 2px rgba(76, 175, 80, 0.5);
            }
        """)
        self.dns_btn.setToolTip("DNS 레코드 관리")
        self.dns_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dns_btn.clicked.connect(lambda: self.clicked.emit(self.domain))
        layout.addWidget(self.dns_btn)
        
        self.setLayout(layout)
        self.setMaximumHeight(45)
        self.setMinimumHeight(45)
        
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
        self.setMinimumHeight(180)
        self.setMinimumWidth(280)
        self.setMaximumWidth(320)
        self.update_style()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Group name label with icon
        self.name_label = QLabel(f"📁 {self.name}")
        self.name_label.setStyleSheet("""
            font-weight: 600;
            font-size: 16px;
            color: #2c3e50;
            padding: 4px 8px;
            background: rgba(255, 255, 255, 0.7);
            border-radius: 6px;
            margin-bottom: 4px;
        """)
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        # Settings button
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        self.settings_btn.setStyleSheet("""
            QToolButton {
                border: none;
                font-size: 16px;
                background: rgba(255, 255, 255, 0.6);
                border-radius: 6px;
                padding: 4px;
                color: #34495e;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.9);
                color: #2c3e50;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
        self.drop_hint = QLabel("🎯\n드래그하여 도메인 추가")
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_hint.setStyleSheet("""
            color: #7f8c8d;
            font-style: italic;
            font-size: 14px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.5);
            border: 2px dashed #bdc3c7;
            border-radius: 8px;
            margin: 8px;
        """)
        self.domains_layout.addWidget(self.drop_hint)
        
        self.setLayout(layout)
        
    def update_style(self):
        # Convert hex color to RGB for gradient
        color = QColor(self.color)
        r, g, b = color.red(), color.green(), color.blue()
        
        # Create lighter and darker variants
        lighter = QColor(min(255, r + 20), min(255, g + 20), min(255, b + 20))
        darker = QColor(max(0, r - 10), max(0, g - 10), max(0, b - 10))
        
        self.setStyleSheet(f"""
            DomainGroup {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {lighter.name()}, stop:1 {self.color});
                border: 2px solid {darker.name()};
                border-radius: 12px;
                margin: 4px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            DomainGroup:hover {{
                box-shadow: 0 6px 16px rgba(0,0,0,0.15);
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
            self.name_label.setText(f"📁 {text}")
            
    def change_color(self):
        color = QColorDialog.getColor(QColor(self.color), self, "그룹 색상 선택")
        if color.isValid():
            self.color = color.name()
            self.update_style()
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            # Highlight during drag
            color = QColor(self.color)
            r, g, b = color.red(), color.green(), color.blue()
            lighter = QColor(min(255, r + 30), min(255, g + 30), min(255, b + 30))
            
            self.setStyleSheet(f"""
                DomainGroup {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {lighter.name()}, stop:1 {self.color});
                    border: 3px solid #4CAF50;
                    border-radius: 12px;
                    margin: 4px;
                    box-shadow: 0 6px 20px rgba(76, 175, 80, 0.3);
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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Add background styling to main widget
        self.setStyleSheet("""
            DashboardWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
        """)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.add_group_btn = QPushButton("➕ 새 그룹")
        self.add_group_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #74b9ff, stop:1 #0984e3);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
                box-shadow: 0 3px 6px rgba(116, 185, 255, 0.3);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0984e3, stop:1 #0770d1);
                box-shadow: 0 4px 8px rgba(116, 185, 255, 0.4);
            }
            QPushButton:pressed {
                background: #0770d1;
                box-shadow: 0 2px 4px rgba(116, 185, 255, 0.5);
            }
        """)
        self.add_group_btn.clicked.connect(self.add_group)
        toolbar_layout.addWidget(self.add_group_btn)
        
        # Status info label
        self.status_label = QLabel("🔄 대시보드 및 도메인 그룹 관리")
        self.status_label.setStyleSheet("""
            color: #6c757d;
            font-size: 12px;
            font-style: italic;
            padding: 4px 8px;
        """)
        toolbar_layout.addWidget(self.status_label)
        
        toolbar_layout.addStretch()
        
        self.save_btn = QPushButton("💾 저장")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00b894, stop:1 #00a085);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
                box-shadow: 0 3px 6px rgba(0, 184, 148, 0.3);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00a085, stop:1 #008f76);
                box-shadow: 0 4px 8px rgba(0, 184, 148, 0.4);
            }
            QPushButton:pressed {
                background: #008f76;
                box-shadow: 0 2px 4px rgba(0, 184, 148, 0.5);
            }
        """)
        self.save_btn.clicked.connect(self.save_config)
        toolbar_layout.addWidget(self.save_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Main content area
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Ungrouped domains panel with modern design
        ungrouped_frame = QFrame()
        ungrouped_frame.setFrameStyle(QFrame.Shape.Box)
        ungrouped_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fafbff, stop:1 #f0f2ff);
                border: 2px solid #d1d9e6;
                border-radius: 12px;
                margin: 4px;
            }
        """)
        ungrouped_layout = QVBoxLayout()
        
        ungrouped_label = QLabel("📋 미분류 도메인")
        ungrouped_label.setStyleSheet("""
            font-weight: 600;
            font-size: 16px;
            color: #2c3e50;
            padding: 12px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 8px;
            margin: 8px;
            border-bottom: 2px solid #3498db;
        """)
        ungrouped_layout.addWidget(ungrouped_label)
        
        self.ungrouped_scroll = QScrollArea()
        self.ungrouped_scroll.setWidgetResizable(True)
        self.ungrouped_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
                border-radius: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0,0,0,0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #3498db;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2980b9;
            }
        """)
        self.ungrouped_container = QWidget()
        self.ungrouped_layout = QVBoxLayout()
        self.ungrouped_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.ungrouped_container.setLayout(self.ungrouped_layout)
        self.ungrouped_scroll.setWidget(self.ungrouped_container)
        ungrouped_layout.addWidget(self.ungrouped_scroll)
        
        ungrouped_frame.setLayout(ungrouped_layout)
        self.splitter.addWidget(ungrouped_frame)
        
        # Groups panel with enhanced styling
        self.groups_scroll = QScrollArea()
        self.groups_scroll.setWidgetResizable(True)
        self.groups_scroll.setStyleSheet("""
            QScrollArea {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 2px solid #dee2e6;
                border-radius: 12px;
                margin: 4px;
            }
            QScrollBar:horizontal {
                border: none;
                background: rgba(0,0,0,0.1);
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #6c757d;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #495057;
            }
        """)
        self.groups_container = QWidget()
        self.groups_layout = QHBoxLayout()
        self.groups_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.groups_layout.setContentsMargins(12, 12, 12, 12)
        self.groups_layout.setSpacing(16)
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
            else:
                # Use default color if user cancels color selection
                self.create_group(text, "#e8f5e8")
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
            # Create default groups with better colors
            self.create_group("개인", "#e8f5e8")
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
            # Create default groups on error with better colors
            self.create_group("개인", "#e8f5e8")
            self.create_group("업무", "#fff3e0")
            self.create_group("프로젝트", "#f3e5f5")