"""Dashboard Widget for Domain Group Management"""
import json
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QInputDialog, QColorDialog, QSplitter, QFrame,
    QScrollArea, QGridLayout, QToolButton, QApplication, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QTimer, QRect
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDrag, QColor, QFont


class DomainItem(QWidget):
    """Custom widget for domain display in groups"""
    clicked = pyqtSignal(str)
    remove_clicked = pyqtSignal(str)  # Signal for remove button
    selection_requested = pyqtSignal(object, object)

    def __init__(
        self,
        domain: str,
        show_remove: bool = False,
        is_porkbun_ns: bool = True,
        selection_enabled: bool = False,
        selection_provider: Optional[Callable[[], List[str]]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.domain = domain
        self.show_remove = show_remove
        self.is_porkbun_ns = is_porkbun_ns
        self.selection_enabled = selection_enabled
        self.selection_provider = selection_provider
        self._selected = False
        self._base_style = ""
        self._selected_style = ""
        self._pending_single_select = False
        self._drag_in_progress = False
        self.setObjectName("domainItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()

    def setup_ui(self):
        # 프레임 제거하고 단순한 배경색과 호버 효과만 적용
        self._base_style = """
            #domainItem {
                background: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 6px;
                padding: 4px 8px;
            }
            #domainItem:hover {
                background: #f0f8ff;
                border: 1px solid #007bff;
            }
        """
        self._selected_style = """
            #domainItem {
                background: #e7f1ff;
                border: 2px solid #5b9bff;
                border-radius: 6px;
                padding: 3px 7px;
            }
            #domainItem:hover {
                background: #d7e9ff;
                border: 2px solid #1c7cd6;
            }
        """
        self._apply_selection_style()
        
        layout = QHBoxLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)
        
        # Domain label with color based on nameserver status
        display_text = self.domain
        if not self.is_porkbun_ns:
            display_text = f"⚠ {self.domain}"
        
        self.label = QLabel(display_text)
        # 텍스트 표시 최적화 - 더 넉넉한 공간과 완전한 텍스트 표시
        self.label.setMinimumWidth(120)
        self.label.setMaximumWidth(200)
        self.label.setWordWrap(False)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        
        if self.is_porkbun_ns:
            self.label.setStyleSheet("""
                font-size: 12px; 
                color: #2c3e50; 
                font-weight: 500; 
                font-family: 'Segoe UI', Arial, sans-serif;
                background: transparent;
                border: none;
            """)
        else:
            self.label.setStyleSheet("""
                font-size: 12px; 
                color: #e74c3c; 
                font-weight: 600; 
                font-family: 'Segoe UI', Arial, sans-serif;
                background: transparent;
                border: none;
            """)
            self.label.setToolTip("외부 네임서버 사용 중")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        # Remove button (only for grouped domains)
        if self.show_remove:
            self.remove_btn = QToolButton()
            self.remove_btn.setText("×")  # Cross mark
            self.remove_btn.setStyleSheet("""
                QToolButton {
                    background: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    padding: 1px 3px;
                    font-size: 9px;
                    font-weight: 500;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QToolButton:hover {
                    background: #c82333;
                }
            """)
            self.remove_btn.setToolTip("미분류로 이동")
            self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.domain))
            layout.addWidget(self.remove_btn)
        
        # Copy button next to DNS controls
        self.copy_btn = QToolButton()
        self.copy_btn.setText("📋")
        self.copy_btn.setStyleSheet("""
            QToolButton {
                background: #17a2b8;
                color: white;
                border: none;
                border-radius: 2px;
                padding: 1px 4px;
                font-size: 9px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QToolButton:hover {
                background: #117a8b;
            }
        """)
        self.copy_btn.setToolTip("도메인 복사")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self.copy_domain)
        layout.addWidget(self.copy_btn)

        # DNS control button
        self.dns_btn = QToolButton()
        self.dns_btn.setText("DNS")
        self.dns_btn.setStyleSheet("""
            QToolButton {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 2px;
                padding: 1px 4px;
                font-size: 9px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QToolButton:hover {
                background: #0056b3;
            }
        """)
        self.dns_btn.setToolTip("DNS 레코드 관리")
        self.dns_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dns_btn.clicked.connect(lambda: self.clicked.emit(self.domain))
        layout.addWidget(self.dns_btn)
        
        self.setLayout(layout)
        self.setMaximumHeight(28)
        self.setMinimumHeight(28)
        self.setMinimumWidth(200)

    def _apply_selection_style(self):
        if self._selected:
            self.setStyleSheet(self._selected_style)
        else:
            self.setStyleSheet(self._base_style)

    def set_selected(self, selected: bool):
        if not self.selection_enabled:
            return
        if self._selected != selected:
            self._selected = selected
            self._apply_selection_style()

    def is_selected(self) -> bool:
        return self._selected

    def copy_domain(self):
        """Copy this domain name to clipboard"""
        QApplication.clipboard().setText(self.domain)
        QToolTip.showText(
            self.copy_btn.mapToGlobal(QPoint(0, self.copy_btn.height())),
            f"복사됨: {self.domain}",
            self.copy_btn,
            QRect(),
            2000,
        )
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            if self.selection_enabled:
                if (
                    modifiers == Qt.KeyboardModifier.NoModifier
                    and self._selected
                    and self.selection_provider
                ):
                    selected_now = self.selection_provider() or []
                    if len(selected_now) > 1:
                        self._pending_single_select = True
                    else:
                        self.selection_requested.emit(self, modifiers)
                        self._pending_single_select = False
                else:
                    self.selection_requested.emit(self, modifiers)
                    self._pending_single_select = False
            else:
                self._pending_single_select = False
            self.drag_start_position = event.pos()
            self._drag_in_progress = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        self._drag_in_progress = True
        self._pending_single_select = False
        drag = QDrag(self)
        mime_data = QMimeData()
        domains_to_drag = [self.domain]
        if self.selection_enabled and self.selection_provider:
            selected_domains = self.selection_provider()
            if selected_domains and self.domain in selected_domains:
                domains_to_drag = selected_domains
        mime_data.setText("\n".join(domains_to_drag))
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.selection_enabled
            and self._pending_single_select
            and not self._drag_in_progress
        ):
            self.selection_requested.emit(self, Qt.KeyboardModifier.NoModifier)
        self._pending_single_select = False
        self._drag_in_progress = False
        super().mouseReleaseEvent(event)


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
        self.setMinimumHeight(160)
        self.setMinimumWidth(240)
        self.setMaximumWidth(280)
        self.update_style()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Group name label
        self.name_label = QLabel(self.name)
        self.name_label.setStyleSheet("""
            font-weight: 600;
            font-size: 14px;
            color: #212529;
            padding: 2px 6px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        header_layout.addWidget(self.name_label)

        # Domain count badge
        self.count_label = QLabel()
        self.count_label.setStyleSheet("""
            color: #6c757d;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
            background: #e9ecef;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        header_layout.addWidget(self.count_label)
        
        header_layout.addStretch()

        # Group-level copy button
        self.copy_group_btn = QToolButton()
        self.copy_group_btn.setText("📋")
        self.copy_group_btn.setStyleSheet("""
            QToolButton {
                background: #17a2b8;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QToolButton:hover {
                background: #117a8b;
            }
            QToolButton:disabled {
                background: #cfe2f3;
                color: #6c757d;
            }
        """)
        self.copy_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_group_btn.setToolTip("그룹 도메인 전체 복사")
        self.copy_group_btn.clicked.connect(self.copy_group_domains)
        header_layout.addWidget(self.copy_group_btn)
        
        # Settings button
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⋯")
        self.settings_btn.setStyleSheet("""
            QToolButton {
                border: none;
                font-size: 12px;
                background: transparent;
                border-radius: 3px;
                padding: 2px;
                color: #6c757d;
            }
            QToolButton:hover {
                background: #e9ecef;
                color: #495057;
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
        self.drop_hint = QLabel("여기에 도메인을 드래그하세요")
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_hint.setStyleSheet("""
            color: #6c757d;
            font-style: italic;
            font-size: 12px;
            padding: 12px;
            background: transparent;
            border: 1px dashed #dee2e6;
            border-radius: 4px;
            margin: 4px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        self.domains_layout.addWidget(self.drop_hint)
        
        self.setLayout(layout)
        self.update_copy_button_state()
        self.update_count_label()
        
    def update_style(self):
        # Subtle professional styling
        color = QColor(self.color)
        
        self.setStyleSheet(f"""
            DomainGroup {{
                background: {self.color};
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin: 2px;
            }}
            DomainGroup:hover {{
                border: 1px solid #adb5bd;
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
            self.update_copy_button_state()
            self.update_count_label()
    
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
        self.update_copy_button_state()
        self.update_count_label()

    def update_count_label(self):
        if hasattr(self, "count_label"):
            self.count_label.setText(f"{len(self.domains)}개")

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
            # Highlight during drag
            self.setStyleSheet(f"""
                DomainGroup {{
                    background: {self.color};
                    border: 2px solid #007bff;
                    border-radius: 6px;
                    margin: 2px;
                }}
            """)
            
    def dragLeaveEvent(self, event):
        self.update_style()
        
    def dropEvent(self, event: QDropEvent):
        text = event.mimeData().text().strip()
        domains = [d.strip() for d in text.splitlines() if d.strip()]
        if not domains:
            self.update_style()
            return

        for domain in domains:
            self.domain_dropped.emit(domain, self.name)
        event.acceptProposedAction()
        self.update_style()

    def copy_group_domains(self):
        """Copy all domains in this group separated by newlines"""
        if not self.domains:
            QToolTip.showText(
                self.copy_group_btn.mapToGlobal(QPoint(0, self.copy_group_btn.height())),
                "복사할 도메인이 없습니다",
                self.copy_group_btn,
                QRect(),
                2000,
            )
            return

        text = "\n".join(self.domains)
        QApplication.clipboard().setText(text)
        QToolTip.showText(
            self.copy_group_btn.mapToGlobal(QPoint(0, self.copy_group_btn.height())),
            f"{len(self.domains)}개 도메인 복사됨",
            self.copy_group_btn,
            QRect(),
            2000,
        )

    def update_copy_button_state(self):
        if hasattr(self, "copy_group_btn"):
            self.copy_group_btn.setEnabled(bool(self.domains))


class DashboardWidget(QWidget):
    """Main Dashboard Widget for managing domain groups"""
    domain_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.groups = {}  # {group_name: DomainGroup}
        self.all_domains = []
        self.domain_info = {}  # {domain: {"is_porkbun": bool}}
        self.selection_anchor_domain: Optional[str] = None
        self.dashboard_store_file = Path.home() / ".porkbun_dns" / "dashboard_profiles.json"
        self.legacy_config_file = Path.home() / ".porkbun_dashboard.json"
        self.profile_id = "__default__"
        self.dashboard_store = self._load_store()
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Add background styling to main widget
        self.setStyleSheet("""
            DashboardWidget {
                background: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.add_group_btn = QPushButton("+ 새 그룹")
        self.add_group_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        self.add_group_btn.clicked.connect(self.add_group)
        toolbar_layout.addWidget(self.add_group_btn)
        
        # Status info label
        self.status_label = QLabel("도메인 관리 대시보드")
        self.status_label.setStyleSheet("""
            color: #6c757d;
            font-size: 11px;
            padding: 2px 6px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        toolbar_layout.addWidget(self.status_label)
        
        toolbar_layout.addStretch()
        
        self.save_btn = QPushButton("저장")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton:hover {
                background: #1e7e34;
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
        ungrouped_frame.setMinimumWidth(250)
        ungrouped_frame.setMaximumWidth(350)
        ungrouped_frame.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin: 2px;
            }
        """)
        ungrouped_layout = QVBoxLayout()
        
        self.ungrouped_label = QLabel("미분류 도메인")
        self.ungrouped_label.setStyleSheet("""
            font-weight: 600;
            font-size: 12px;
            color: #495057;
            padding: 6px 8px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        ungrouped_layout.addWidget(self.ungrouped_label)
        
        self.ungrouped_scroll = QScrollArea()
        self.ungrouped_scroll.setWidgetResizable(True)
        self.ungrouped_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f8f9fa;
                width: 4px;
            }
            QScrollBar::handle:vertical {
                background: #dee2e6;
                border-radius: 2px;
                min-height: 10px;
            }
            QScrollBar::handle:vertical:hover {
                background: #adb5bd;
            }
        """)
        self.ungrouped_container = QWidget()
        self.ungrouped_layout = QVBoxLayout()
        self.ungrouped_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.ungrouped_layout.setSpacing(4)
        self.ungrouped_layout.setContentsMargins(8, 8, 8, 8)
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
                background: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #f8f9fa;
                height: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #dee2e6;
                border-radius: 3px;
                min-width: 15px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #adb5bd;
            }
        """)
        self.groups_container = QWidget()
        self.groups_layout = QHBoxLayout()
        self.groups_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.groups_layout.setContentsMargins(8, 8, 8, 8)
        self.groups_layout.setSpacing(8)
        self.groups_container.setLayout(self.groups_layout)
        self.groups_scroll.setWidget(self.groups_container)
        self.splitter.addWidget(self.groups_scroll)

        self.splitter.setSizes([300, 800])
        self.update_ungrouped_count()
        layout.addWidget(self.splitter)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Profile-aware persistence helpers
    # ------------------------------------------------------------------
    def _load_store(self) -> Dict[str, Any]:
        data = {"profiles": {}}
        if self.dashboard_store_file.exists():
            try:
                with open(self.dashboard_store_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        data.update(loaded)
            except Exception:
                pass

        if "profiles" not in data or not isinstance(data["profiles"], dict):
            data["profiles"] = {}

        if not data["profiles"] and self.legacy_config_file.exists():
            try:
                with open(self.legacy_config_file, 'r', encoding='utf-8') as f:
                    legacy = json.load(f)
                    if isinstance(legacy, dict):
                        data["profiles"][self.profile_id] = legacy
                        self._save_store(data)
            except Exception:
                pass

        return data

    def _save_store(self, data: Optional[Dict[str, Any]] = None):
        payload = data or self.dashboard_store
        self.dashboard_store_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.dashboard_store_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _ensure_profile_bucket(self):
        self.dashboard_store.setdefault("profiles", {})
        self.dashboard_store["profiles"].setdefault(self.profile_id, {})

    def set_profile(self, profile_id: Optional[str]):
        """Switch dashboard data to a different profile."""
        new_id = profile_id or "__default__"
        if new_id == self.profile_id:
            return
        self.profile_id = new_id
        self._ensure_profile_bucket()
        self.load_config()

    def _clear_groups(self):
        """Remove all group widgets from layout."""
        for group in self.groups.values():
            group.setParent(None)
            group.deleteLater()
        self.groups.clear()

        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _create_default_groups(self):
        """Create default groups when no saved data exists."""
        default_groups = [
            ("개인", "#f1f3f4"),
            ("업무", "#fff2cc"),
            ("프로젝트", "#fce5cd")
        ]
        for name, color in default_groups:
            self.create_group(name, color)
        
    def add_group(self):
        text, ok = QInputDialog.getText(self, "새 그룹", "그룹 이름:")
        if ok and text and text not in self.groups:
            color = QColorDialog.getColor(QColor("#f8f9fa"), self, "그룹 색상 선택")
            if color.isValid():
                self.create_group(text, color.name())
                self.save_config()
            else:
                # Use default color if user cancels color selection
                self.create_group(text, "#f8f9fa")
                self.save_config()
                
    def create_group(self, name: str, color: str = "#f8f9fa"):
        group = DomainGroup(name, color)
        group.domain_dropped.connect(self.handle_domain_drop)
        group.domain_clicked.connect(self.domain_selected.emit)
        group.group_deleted.connect(self.delete_group)
        group.domain_removed.connect(self.handle_domain_removed)
        
        self.groups[name] = group
        self.groups_layout.addWidget(group)
        return group
        
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
                self._remove_domain_from_selection(domain)
                widget.deleteLater()
                break
        self.update_ungrouped_count()
                
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
        
        domain_item = DomainItem(
            domain,
            show_remove=False,
            is_porkbun_ns=is_porkbun,
            selection_enabled=True,
            selection_provider=self.get_selected_ungrouped_domains,
        )
        domain_item.clicked.connect(self.domain_selected.emit)
        domain_item.selection_requested.connect(self.handle_ungrouped_selection)
        self.ungrouped_layout.addWidget(domain_item)
        self.update_ungrouped_count()

    def _get_ungrouped_domain_widgets(self) -> List[DomainItem]:
        widgets: List[DomainItem] = []
        if not hasattr(self, "ungrouped_layout"):
            return widgets
        for i in range(self.ungrouped_layout.count()):
            widget = self.ungrouped_layout.itemAt(i).widget()
            if isinstance(widget, DomainItem):
                widgets.append(widget)
        return widgets

    def get_selected_ungrouped_domains(self) -> List[str]:
        return [widget.domain for widget in self._get_ungrouped_domain_widgets() if widget.is_selected()]

    def clear_ungrouped_selection(self):
        for widget in self._get_ungrouped_domain_widgets():
            if widget.is_selected():
                widget.set_selected(False)
        self.selection_anchor_domain = None

    def _find_ungrouped_index(
        self,
        domain: Optional[str],
        widgets: Optional[List[DomainItem]] = None,
    ) -> Optional[int]:
        if not domain:
            return None
        widgets = widgets or self._get_ungrouped_domain_widgets()
        for index, widget in enumerate(widgets):
            if widget.domain == domain:
                return index
        return None

    def handle_ungrouped_selection(self, domain_item: DomainItem, modifiers):
        widgets = self._get_ungrouped_domain_widgets()
        if not widgets or domain_item not in widgets:
            return

        index = widgets.index(domain_item)
        shift_pressed = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        additive = bool(
            modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        )

        if shift_pressed:
            anchor_index = self._find_ungrouped_index(self.selection_anchor_domain, widgets)
            if anchor_index is None:
                self.selection_anchor_domain = domain_item.domain
                anchor_index = index

            start = min(anchor_index, index)
            end = max(anchor_index, index)
            for i, widget in enumerate(widgets):
                widget.set_selected(start <= i <= end)
        elif additive:
            domain_item.set_selected(not domain_item.is_selected())
            if domain_item.is_selected():
                self.selection_anchor_domain = domain_item.domain
        else:
            self.clear_ungrouped_selection()
            domain_item.set_selected(True)
            self.selection_anchor_domain = domain_item.domain

        selected = self.get_selected_ungrouped_domains()
        if not selected:
            self.selection_anchor_domain = None
        elif self.selection_anchor_domain not in selected:
            self.selection_anchor_domain = selected[0]

    def _remove_domain_from_selection(self, domain: str):
        if self.selection_anchor_domain == domain:
            remaining = [d for d in self.get_selected_ungrouped_domains() if d != domain]
            self.selection_anchor_domain = remaining[0] if remaining else None

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
        self.clear_ungrouped_selection()
        # Clear ungrouped
        while self.ungrouped_layout.count():
            item = self.ungrouped_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.update_ungrouped_count()
        
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
            group.update_count_label()
            group.update_copy_button_state()
            
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
                
    def update_ungrouped_count(self):
        """Update the label showing how many ungrouped domains exist."""
        if not hasattr(self, "ungrouped_label"):
            return
        count = 0
        for i in range(self.ungrouped_layout.count()):
            widget = self.ungrouped_layout.itemAt(i).widget()
            if isinstance(widget, DomainItem):
                count += 1
        self.ungrouped_label.setText(f"미분류 도메인 ({count}개)")
                
    def save_config(self):
        """Save dashboard configuration"""
        self._ensure_profile_bucket()
        profile_entry = {
            "groups": {}
        }

        for name, group in self.groups.items():
            profile_entry["groups"][name] = {
                "color": group.color,
                "domains": group.domains
            }

        self.dashboard_store["profiles"][self.profile_id] = profile_entry

        try:
            self._save_store()
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
        """Load dashboard configuration for the current profile."""
        self._ensure_profile_bucket()
        profile_data = self.dashboard_store["profiles"].get(self.profile_id, {})
        groups_data = profile_data.get("groups") if isinstance(profile_data, dict) else None

        self._clear_groups()

        if not groups_data:
            self._create_default_groups()
            self.refresh_domains()
            return

        for name, group_data in groups_data.items():
            color = group_data.get("color", "#e3f2fd")
            group = self.create_group(name, color)
            group.domains = group_data.get("domains", []).copy()

        self.refresh_domains()
