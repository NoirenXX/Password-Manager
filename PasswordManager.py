# ███╗   ██╗ ██████╗ ██╗██████╗ ███████╗███╗   ██╗    ██╗  ██╗██╗  ██╗
# ████╗  ██║██╔═══██╗██║██╔══██╗██╔════╝████╗  ██║    ╚██╗██╔╝╚██╗██╔╝
# ██╔██╗ ██║██║   ██║██║██████╔╝█████╗  ██╔██╗ ██║     ╚███╔╝  ╚███╔╝
# ██║╚██╗██║██║   ██║██║██╔══██╗██╔══╝  ██║╚██╗██║     ██╔██╗  ██╔██╗
# ██║ ╚████║╚██████╔╝██║██║  ██║███████╗██║ ╚████║    ██╔╝ ██╗██╔╝ ██╗
# ╚═╝  ╚═══╝ ╚═════╝ ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝    ╚═╝  ╚═╝╚═╝  ╚═╝


from PyQt6.QtCore import (Qt, QSettings, QSize, QTimer, QObject, QEvent, QLocale)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QListWidget, QLineEdit,
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QStackedWidget, QInputDialog, QMessageBox
)
import json
from PyQt6.QtGui import (QIcon, QCursor)
from qt_material import apply_stylesheet
from cryptography.fernet import Fernet, InvalidToken
from argon2.low_level import hash_secret_raw, Type
import base64
from os import (urandom, replace)
import resources_rc
from pathlib import Path
import sys, ctypes
import secrets
import string

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mycompany.mpassword.1")

app = QApplication([])
app.setWindowIcon(QIcon(":/icons/icon.ico"))

settings = QSettings("App", "ManagerPasswords")
theme = settings.value("theme", "light")
language = settings.value("language", "english")

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = BASE_DIR / "setract"
SALT_LEN = 16

raw = DATA_FILE.read_bytes() if DATA_FILE.exists() else None
is_new = raw is None

ui_langs = QLocale.system().uiLanguages()
system_language = ui_langs[0].split("-")[0].lower() if ui_langs else "en"
texts = {
    "ru": {
        "verify": ("Проверка", "Введите мастер-пароль"),
        "create": ("Придумайте мастер-пароль",
                   "Не потеряйте его, иначе вы потеряете доступ к своим данным!"),
    },
    "en": {
        "verify": ("Verification", "Enter master password"),
        "create": ("Create Master Password",
                   "Don't lose it, otherwise you'll lose access to your data!"),
    },
}

lang_key = "ru" if system_language == "ru" else "en"
title, label = texts[lang_key]["create" if is_new else "verify"]
master_password, ok = QInputDialog.getText(None, title, label, QLineEdit.EchoMode.Password)
if not ok or not master_password.strip():
    raise SystemExit
master_password = master_password.strip().encode()

if is_new:
    salt = urandom(SALT_LEN)
    encrypted = None
else:
    salt = raw[:SALT_LEN]
    encrypted = raw[SALT_LEN:]
def derive_key(pwd, s) -> bytes:
    raw_key = hash_secret_raw(
        secret=pwd,
        salt=s,
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        type=Type.ID
    )
    return base64.urlsafe_b64encode(raw_key)
key = derive_key(master_password, salt)
cipher = Fernet(key)

accounts = {}

if encrypted is not None:
    try:
        accounts = json.loads(cipher.decrypt(encrypted).decode())
    except InvalidToken:
        QMessageBox.critical(None, "Error", "Неверный мастер-пароль или файл повреждён") if system_language == "ru" else QMessageBox.critical(None, "Error", "Invalid master password or corrupted file")
        raise SystemExit

def save_accounts():
    encrypted = cipher.encrypt(json.dumps(accounts).encode())
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_bytes(salt + encrypted)
    replace(tmp, DATA_FILE)

win = QWidget()
win.setWindowTitle("Password Manager")
win.setWindowIcon(QIcon(":/icons/icon.ico"))
win.setWindowFlags(Qt.WindowType.FramelessWindowHint)
win.setMinimumSize(900, 700)
win.resize(900, 700)

theme = settings.value("theme", "light")

class TitleBar(QWidget):
    def __init__(self, WidgetWin, target, parent = None):
        super().__init__(parent)
        self.setObjectName("title_bar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.target = target
        
        self.mouse_held = False
        self.x_offset = QCursor.pos().x() - self.target.x()
        self.y_offset = QCursor.pos().y() - self.target.y()
        self.timer = QTimer()
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.moved)
        
        self.WidgetWin = WidgetWin

        if WidgetWin == "main":
            self.setFixedHeight(35)
            a = 23
        elif WidgetWin == "dialog":
            self.setFixedHeight(20)
            a = 10
        if self.WidgetWin == "main":
            self.title_label = QLabel("Password Manager")
            self.title_label.setFixedHeight(a)
            self.title_label.setStyleSheet("""
                QLabel {
                    color: #4079D8;
                    font-weight: bold;
                    padding: 0px;
                    font-size: 15px;
                    }
                """)
        
        self.hide_b = QPushButton("")
        self.hide_b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.icon_hide = QIcon(":/icons/hide.svg")
        self.hide_b.setIcon(self.icon_hide)
        self.hide_b.setFixedSize(a, a)
        self.hide_b.setStyleSheet("border: none; font-weight: bold;")

        if self.WidgetWin == "main":
            self.max_size_b = QPushButton()
            self.max_size_b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.max_size_b.setFixedSize(a, a)
            self.icon_maxSize = QIcon(":/icons/maxSize.svg")
            self.max_size_b.setStyleSheet("border: none;")
            self.max_size_b.setIcon(self.icon_maxSize)

            self.min_size_b = QPushButton()
            self.min_size_b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.min_size_b.setFixedSize(a, a)
            self.icon_minSize = QIcon(":/icons/minSize.svg")
            self.min_size_b.setStyleSheet("border: none;")
            self.min_size_b.setIcon(self.icon_minSize)

            self.sizeButStack = QStackedWidget()
            self.sizeButStack.addWidget(self.max_size_b)
            self.sizeButStack.addWidget(self.min_size_b)
            self.sizeButStack.setCurrentWidget(self.max_size_b)
            self.sizeButStack.setFixedSize(a, a)

        self.close_b = QPushButton()
        self.icon_close_b = QIcon(":/icons/cross.svg")
        self.close_b.setFixedSize(a, a)
        self.close_b.setIcon(self.icon_close_b)
        self.close_b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_b.setStyleSheet("""
            QPushButton {
                border: none
            }
            QPushButton:pressed {
                background-color: #FF0000;
            }
        """)
        self.close_b.enterEvent = lambda event: self.close_b.setIcon(
            QIcon(":/icons/pressedCross.svg")
        )
        self.close_b.leaveEvent = lambda event: self.close_b.setIcon(
            QIcon(":/icons/cross.svg")
        )

        def maximize_win():
            win.showMaximized()
            self.sizeButStack.setCurrentWidget(self.min_size_b)
        def minimize_win():
            win.showNormal()
            self.sizeButStack.setCurrentWidget(self.max_size_b)
        def close_app():
            if WidgetWin == "main":
                win.close()
            elif WidgetWin == "dialog":
                self.target.reject()

        if WidgetWin == "main":
            self.hide_b.clicked.connect(lambda: win.showMinimized())
        elif WidgetWin == "dialog":
            self.hide_b.clicked.connect(lambda: self.target.hide())
        if self.WidgetWin == "main":
            self.max_size_b.clicked.connect(maximize_win)
            self.min_size_b.clicked.connect(minimize_win)
        self.close_b.clicked.connect(close_app)
        
        self.style_titleBar(theme)

        line_title = QHBoxLayout()
        if self.WidgetWin == "main": line_title.addWidget(self.title_label)
        line_title.addStretch()
        line_title.addWidget(self.hide_b)
        if self.WidgetWin == "main": line_title.addWidget(self.sizeButStack)
        line_title.addWidget(self.close_b)
        line_title.setContentsMargins(8, 0, 4, 0)
        self.setLayout(line_title)


    def style_titleBar(self, t):
        if t == "dark":
            bg = "#212529"
        else:
            bg = "#d4d4d4"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
            }}
            QWidget QPushButton {{
                background-color: transparent;
            }}
            QWidget QLabel {{
                background-color: transparent;
            }}
            QWidget QStackedWidget {{
                background-color: transparent;
            }}
        """)
    def moved(self):
        x = QCursor.pos().x() - self.x_offset
        y = QCursor.pos().y() - self.y_offset
        self.target.move(x, y)
            
    def mousePressEvent(self, event):
        if self.WidgetWin == "main" and self.sizeButStack.currentWidget() == self.min_size_b:
            self.x_offset_m = self.target.mapFromGlobal(QCursor.pos()).x()
            self.x_offset = int(self.x_offset_m/(win.width()/900))
            self.y_offset = self.target.mapFromGlobal(QCursor.pos()).y()
            win.showNormal()
            self.sizeButStack.setCurrentWidget(self.max_size_b)
        else:
            self.x_offset = QCursor.pos().x() - self.target.x()
            self.y_offset = QCursor.pos().y() - self.target.y()

        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_held = True
            self.timer.start()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_held = False
            self.timer.stop()

main_title_bar = TitleBar("main", win)

change_master_pwd = QPushButton()
icon_change_pass = QIcon(":/icons/MPassword.svg")
change_master_pwd.setIcon(icon_change_pass)
change_master_pwd.setFixedSize(30, 30)
change_master_pwd.setFocusPolicy(Qt.FocusPolicy.NoFocus)
change_master_pwd.setStyleSheet("""
    QPushButton {
        padding: 0px;
    }
""")
change_master_pwd.setIconSize(QSize(23, 23))
if language == "russian":
    change_master_pwd.setToolTip("Смена мастер-пароля")
else:
    change_master_pwd.setToolTip("Change master password")

def change_master_password():
    global salt, cipher, key, language, theme
    texts = {
        "russian": ("Введите прежний мастер пароль", "Введите новый мастер-пароль", "Подтвердите новый мастер-пароль", "Мастер-пароли не совпадают", "Неверный мастер-пароль", "Отмена"),
        "english": ("Enter old master password", "Enter new master password", "Confirm new master password", "Master passwords do not match", "Invalid master password", "Cancel"),
    }
    ask = QDialog()
    ask.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    ask.setWindowIcon(QIcon(":/icons/icon.ico"))
    ask.setWindowTitle(" ")
    ask.setFixedSize(300, 200)
    if theme == "dark":
        bg = "#262B30"
    else:
        bg = "#e0dddd"
    ask.setStyleSheet(f"""
        QDialog {{
            background-color: {bg};
            border: 0.5px solid #2979FF;
        }}
        QDialog QLabel {{
            color: #2979FF;
            background-color: transparent;
        }}
    """)

    ask_title_bar = TitleBar("dialog", ask)

    old_pwd_input = QLineEdit()
    old_pwd_input.setPlaceholderText(texts[language][0])

    new_pwd_input = QLineEdit()
    new_pwd_input.setPlaceholderText(texts[language][1])

    confirm_pwd_input = QLineEdit()
    confirm_pwd_input.setPlaceholderText(texts[language][2])

    buttons_ask = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons_ask.setFixedSize(100, 25)
    for btn in buttons_ask.buttons():
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    cancel_button = buttons_ask.button(QDialogButtonBox.StandardButton.Cancel)
    cancel_button.setText(texts[language][5])
    buttons_ask.setStyleSheet("""
        QPushButton {
            padding: 1px;
        font-size: 10px;
            }
        """)

    invalid_pwd = QLabel(texts[language][4])
    invalid_pwd.setStyleSheet("color: red;")
    invalid_pwd.hide()

    different_pwd = QLabel(texts[language][3])
    different_pwd.setStyleSheet("color: red;")
    different_pwd.hide()

    ask_line = QVBoxLayout()
    ask_line.setContentsMargins(9, 9, 9, 9)
    ask_line.addWidget(old_pwd_input)
    ask_line.addWidget(invalid_pwd)
    ask_line.addWidget(new_pwd_input)
    ask_line.addWidget(confirm_pwd_input)
    ask_line.addWidget(different_pwd)
    ask_line.addWidget(buttons_ask)
    
    main_line = QVBoxLayout()
    main_line.setContentsMargins(1, 1, 1, 1)
    main_line.addWidget(ask_title_bar)
    main_line.addLayout(ask_line)

    ask.setLayout(main_line)

    def on_accept():
        global key, cipher
        invalid_pwd.hide()
        different_pwd.hide()
        old_pwd = old_pwd_input.text().strip()
        new_pwd = new_pwd_input.text().strip()
        confirm_pwd = confirm_pwd_input.text().strip()
        
        if old_pwd and new_pwd and confirm_pwd:
            old_ok = derive_key(old_pwd.encode(), salt) == key
            match_ok = new_pwd == confirm_pwd
            if not old_ok:
                invalid_pwd.show()
            if not match_ok:
                different_pwd.show()
            if not (old_ok and match_ok):
                return
        
            key = derive_key(new_pwd.encode(), salt)
            cipher = Fernet(key)
            save_accounts()
            ask.accept()

    buttons_ask.accepted.connect(on_accept)
    buttons_ask.rejected.connect(lambda: ask.reject())

    ask.exec()

def clear_selection_global(event):
    account_list.clearSelection()
    QWidget.mousePressEvent(win, event)
    if language == "russian":
        login.setText('ЛОГИН')
    elif language == "english":
        login.setText('LOGIN')
    
win.mousePressEvent = clear_selection_global

account_list = QListWidget()
account_list.resize(600, 700)
for name in accounts.keys():
    account_list.addItem(name)

account_list.setStyleSheet("""
    QListWidget::item {
        color: #2979FF;
    }
    QListWidget::item:selected {
        background-color: #2979FF;
    }
""")

def clear_selection(event):
    item = account_list.itemAt(event.pos())
    if item is None:
        account_list.clearSelection()
        if language == "russian":
                login.setText('ЛОГИН')
        elif language == "english":
            login.setText('LOGIN')
    QListWidget.mousePressEvent(account_list, event)

account_list.mousePressEvent = clear_selection

account_search  = QLineEdit()
if language == "russian":
    account_search.setPlaceholderText("Поиск по названию аккаунта...")
elif language == "english":
    account_search.setPlaceholderText("Search by account name...")
account_search.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

def searching():
    search_text = account_search.text().lower()
    for i in range(account_list.count()):
        item = account_list.item(i)
        item.setHidden(search_text not in item.text().lower())

light_theme_button = QPushButton("☀")
light_theme_button.setFixedSize(40, 30)
light_theme_button.setStyleSheet("""
    QPushButton {
        padding: 0px;
    }
""")
light_theme_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

dark_theme_button = QPushButton("⏾")
dark_theme_button.setFixedSize(40, 30)
dark_theme_button.setStyleSheet("""
    QPushButton {
        padding: 0px;
    }
""")
dark_theme_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

stack_themes = QStackedWidget()
stack_themes.addWidget(light_theme_button)
stack_themes.addWidget(dark_theme_button)
stack_themes.setCurrentWidget(light_theme_button)

if theme == "light":
    apply_stylesheet(app, theme='light_blue.xml')
    stack_themes.setCurrentWidget(dark_theme_button)
elif theme == "dark":
    apply_stylesheet(app, theme='dark_blue.xml')
    stack_themes.setCurrentWidget(light_theme_button)

def change_themeLight():
    apply_stylesheet(app, theme='light_blue.xml')
    global theme
    theme = "light"
    settings.setValue("theme", theme)
    stack_themes.setCurrentWidget(dark_theme_button)
    main_title_bar.style_titleBar(theme)

def change_themeDark():
    apply_stylesheet(app, theme='dark_blue.xml')
    global theme
    theme = "dark"
    settings.setValue("theme", theme)
    stack_themes.setCurrentWidget(light_theme_button)
    main_title_bar.style_titleBar(theme)

en_language_but = QPushButton('EN')
en_language_but.setFixedSize(40, 30)
en_language_but.setStyleSheet("""
    QPushButton {
        padding: 0px;
    }
""")
en_language_but.setFocusPolicy(Qt.FocusPolicy.NoFocus)

ru_language_but = QPushButton('RU')
ru_language_but.setFixedSize(40, 30)
ru_language_but.setStyleSheet("""
    QPushButton {
        padding: 0px;
    }
""")
ru_language_but.setFocusPolicy(Qt.FocusPolicy.NoFocus)

def change_lang():
    if language == "russian":
        login.setText("ЛОГИН")
        password_copy.setText("СКОПИРОВАТЬ ПАРОЛЬ")
        add_account.setText("ДОБАВИТЬ АККАУНТ")
        delete_account.setText("УДАЛИТЬ АККАУНТ")
        account_search.setPlaceholderText("Поиск по названию аккаунта...")
        change_master_pwd.setToolTip("Смена мастер-пароля")
    elif language == "english":
        login.setText("LOGIN")
        password_copy.setText("COPY PASSWORD")
        add_account.setText("ADD ACCOUNT")
        delete_account.setText("DELETE ACCOUNT")
        account_search.setPlaceholderText("Search by account name...")
        change_master_pwd.setToolTip("Change master password")

def change_lang_ru():
    global language
    stack_lang.setCurrentWidget(en_language_but)
    language = "russian"
    settings.setValue("language", language)
    change_lang()

def change_lang_en():
    global language
    stack_lang.setCurrentWidget(ru_language_but)
    language = "english"
    settings.setValue("language", language)
    change_lang()

stack_lang = QStackedWidget()
stack_lang.addWidget(en_language_but)
stack_lang.addWidget(ru_language_but)
if language == "russian":
    stack_lang.setCurrentWidget(en_language_but)
elif language == "english":
    stack_lang.setCurrentWidget(ru_language_but)


login = QLabel('ЛОГИН')
login.setStyleSheet("""
    QLabel {
        border: 2px solid #2979FF;
        border-radius: 5px;
        background-color: transparent;
        color: #2979FF;
        padding: 10px;
        font-weight: bold;
    }
""") 

login.setAlignment(Qt.AlignmentFlag.AlignCenter)

def log_print():
    item1 = account_list.currentItem()
    if item1 != None:
        key2 = item1.text()
        if language == "russian":
            login.setText(f'ЛОГИН: {accounts[key2][0]}')
        elif language == "english":
            login.setText(f'LOGIN: {accounts[key2][0]}')


password_copy = QPushButton('СКОПИРОВАТЬ ПАРОЛЬ')
password_copy.setFocusPolicy(Qt.FocusPolicy.NoFocus)

def copy_pass():
    item2 = account_list.currentItem()
    if item2 != None:
        key1 = item2.text()
        copy_list = QApplication.clipboard()
        copy_list.setText(accounts[key1][1])
        account_list.clearSelection()
        if language == "russian":
            login.setText('ЛОГИН')
        elif language == "english":
            login.setText('LOGIN')


add_account = QPushButton('ДОБАВИТЬ АККАУНТ')
add_account.setFocusPolicy(Qt.FocusPolicy.NoFocus)

def add_account_dialog():
    texts = {
        "russian": ("Название:", "Логин:", "Пароль:", "СГЕНЕРИРОВАТЬ", "ОТМЕНА", "Аккаунт с таким названием уже существует!", "10pt"),
        "english": ("Name:", "Login:", "Password:", "GENERATE", "CANCEL", "An account with this name already exists!", "8pt")
    }
    dialog = QDialog()
    dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    dialog.setWindowIcon(QIcon(":/icons/icon.ico"))

    if theme == "dark":
        bg = "#262B30"
    else:
        bg = "#e0dddd"
    dialog.setStyleSheet(f"""
        QDialog {{
            background-color: {bg};
            border: 0.5px solid #2979FF;
        }}
        QDialog QPushButton {{
            background-color: transparent;
        }}
        QDialog QLabel {{
            color: #2979FF;
            background-color: transparent;
        }}
        QDialog QStackedWidget {{
            background-color: transparent;
        }}
    """)

    dialog.setWindowTitle(" ")
    dialog.setFixedSize(300, 200)
    dialog_line = QVBoxLayout()
    dialog_line.setContentsMargins(1, 1, 1, 1)

    form_line = QFormLayout()
    form_line.setContentsMargins(9, 9, 9, 9)
    password_line = QHBoxLayout()
    but_line = QHBoxLayout()

    dialog_title_bar = TitleBar("dialog", dialog)

    name_input = QLineEdit()
    name_input.setFixedSize(180, 30)

    same_name = QLabel(texts[language][5])
    same_name.setStyleSheet("color: red;")
    same_name.hide()
    def check_n():
        if name_input.text().strip() in accounts:
            same_name.show()
        else:
            same_name.hide()
    name_input.textChanged.connect(check_n)

    login_input = QLineEdit()
    login_input.setFixedSize(180, 30)

    password_input = QLineEdit()
    password_input.setFixedSize(180, 30)
    password_input.setEchoMode(QLineEdit.EchoMode.Password)

    generate_password_btn = QPushButton("")
    generate_password_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    generate_password_btn.setFixedSize(100, 25)
    generate_password_btn.setStyleSheet("""
        QPushButton {
        padding: 2px;
        font-size: 10px;
        }
    """)
    generate_password_btn.setText(texts[language][3])

    password_hide = QPushButton()
    password_hide.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    icon_ph = QIcon(":/icons/closeEye.svg")
    password_hide.setIcon(icon_ph)
    password_hide.setIconSize(QSize(20, 20))
    password_hide.setFixedSize(30, 30)
    password_hide.setStyleSheet("""
        QPushButton {
            padding: 0px;
            border: none;
        }
        QPushButton:pressed {
            background-color: transparent;
        }
        QPushButton:hover {
            background-color: transparent;
        }
    """)

    password_show = QPushButton()
    password_show.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    icon_ps = QIcon(":/icons/openEye.svg")
    password_show.setIcon(icon_ps)
    password_show.setIconSize(QSize(20, 20))
    password_show.setFixedSize(30, 30)
    password_show.setStyleSheet("""
        QPushButton {
            padding: 0px;
            border: none;
        }
        QPushButton:pressed {
        background-color: transparent;
        }
        QPushButton:hover {
            background-color: transparent;
        }
    """)

    buttons_dialog = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    cancel_button = buttons_dialog.button(QDialogButtonBox.StandardButton.Cancel)
    cancel_button.setText(texts[language][4])
    buttons_dialog.setFixedSize(100, 25)
    buttons_dialog.setStyleSheet("""
    QPushButton {
        padding: 1px;
    font-size: 10px;
        }
    """)

    stack_see = QStackedWidget()
    stack_see.addWidget(password_show)
    stack_see.addWidget(password_hide)
    stack_see.setCurrentWidget(password_show)
    stack_see.setFixedSize(30, 30)

    password_line.addWidget(password_input)
    password_line.addWidget(stack_see)
    
    but_line.addWidget(generate_password_btn)
    but_line.addStretch(1)
    but_line.addStretch(2)
    but_line.addWidget(buttons_dialog)

    form_line.addRow(texts[language][0], name_input)
    form_line.addRow(texts[language][1], login_input)
    form_line.addRow(texts[language][2], password_line)
    label_p = form_line.labelForField(password_line)
    label_p.setStyleSheet(f"font-size: {texts[language][6]};")
    form_line.addRow(same_name)
    form_line.addRow(but_line)

    dialog_line.addWidget(dialog_title_bar)
    dialog_line.addLayout(form_line)
    dialog.setLayout(dialog_line)

    def on_accept():
        name = name_input.text().strip()
        login_val = login_input.text().strip()
        password_val = password_input.text().strip()
        if name and login_val and password_val:
            if name not in accounts:
                accounts[name] = (login_val, password_val)
                account_list.addItem(name)
            elif name in accounts:
                return
        dialog.accept()
        account_list.clearSelection()
        save_accounts()

    def on_reject():
        dialog.reject()
        account_list.clearSelection()

    def show_password():
        password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        stack_see.setCurrentWidget(password_hide)

    def hide_password():
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        stack_see.setCurrentWidget(password_show)

    def generate_password(length=16):
        chars = (string.ascii_letters
                + string.digits
                + '?!._')
        return ''.join(
            secrets.choice(chars)
            for _ in range(length)
        )


    buttons_dialog.accepted.connect(on_accept)
    buttons_dialog.rejected.connect(on_reject)
    password_show.clicked.connect(show_password)
    password_hide.clicked.connect(hide_password)
    generate_password_btn.clicked.connect(lambda: password_input.setText(generate_password()))

    dialog.exec()

delete_account = QPushButton('УДАЛИТЬ АККАУНТ')
delete_account.setFocusPolicy(Qt.FocusPolicy.NoFocus)

def delete_ac():
    item3 = account_list.currentItem()
    if item3 != None:
        account_list.takeItem(account_list.currentRow())
        key3 = item3.text()
        del accounts[key3]
        save_accounts()
    if language == "english":
        login.setText("LOGIN")
    elif language == "russian":
        login.setText('ЛОГИН')

if language == "russian":
    login.setText("ЛОГИН")
    password_copy.setText("СКОПИРОВАТЬ ПАРОЛЬ")
    add_account.setText("ДОБАВИТЬ АККАУНТ")
    delete_account.setText("УДАЛИТЬ АККАУНТ")
elif language == "english":
    login.setText("LOGIN")
    password_copy.setText("COPY PASSWORD")
    add_account.setText("ADD ACCOUNT")
    delete_account.setText("DELETE ACCOUNT")


lineG  = QVBoxLayout()
line_list = QVBoxLayout()
line_b = QVBoxLayout()
lineH = QHBoxLayout()
line_del_add = QHBoxLayout()
line_prefs = QHBoxLayout()

line_del_add.addWidget(add_account)
line_del_add.addWidget(delete_account)

line_prefs.addWidget(change_master_pwd)
line_prefs.addStretch(1)
line_prefs.addWidget(stack_themes)
line_prefs.addWidget(stack_lang)
line_prefs.setSpacing(3)

line_b.addWidget(login)
line_b.addWidget(password_copy)
line_b.addLayout(line_del_add)
line_b.addStretch(1)
line_b.addLayout(line_prefs)
line_b.setSpacing(2)
line_b.setContentsMargins(20, 20, 20, 20)

line_list.addWidget(account_search)
line_list.addWidget(account_list)

lineH.addLayout(line_list, stretch=2)
lineH.addLayout(line_b, stretch=1)
lineH.setContentsMargins(9, 9, 9, 9)

lineG.addWidget(main_title_bar)
lineG.addLayout(lineH)
lineG.setContentsMargins(0, 0, 0, 0)
lineG.setSpacing(0)

win.setLayout(lineG)

add_account.clicked.connect(add_account_dialog)
password_copy.clicked.connect(copy_pass)
account_list.itemClicked.connect(log_print)
account_search.textChanged.connect(searching)
delete_account.clicked.connect(delete_ac)
light_theme_button.clicked.connect(change_themeLight)
dark_theme_button.clicked.connect(change_themeDark)
en_language_but.clicked.connect(change_lang_en)
ru_language_but.clicked.connect(change_lang_ru)
change_master_pwd.clicked.connect(change_master_password)

def closeEvent(event):
    save_accounts()
    event.accept()

win.closeEvent = closeEvent

MARGIN = 8

def edges_at(pos):
    edges = Qt.Edge(0)
    if pos.x() <= MARGIN:
        edges |= Qt.Edge.LeftEdge
    if pos.x() >= win.width() - MARGIN:
        edges |= Qt.Edge.RightEdge
    if pos.y() <= MARGIN:
        edges |= Qt.Edge.TopEdge
    if pos.y() >= win.height() - MARGIN:
        edges |= Qt.Edge.BottomEdge
    return edges

def cursor_for(e):
    E = Qt.Edge
    if e == (E.LeftEdge | E.TopEdge) or e == (E.RightEdge | E.BottomEdge):
        return Qt.CursorShape.SizeFDiagCursor
    if e == (E.RightEdge | E.TopEdge) or e == (E.LeftEdge | E.BottomEdge):
        return Qt.CursorShape.SizeBDiagCursor
    if e & (E.LeftEdge | E.RightEdge):
        return Qt.CursorShape.SizeHorCursor
    return Qt.CursorShape.SizeVerCursor

class ResizeFilter(QObject):
    cursor_active = False

    def eventFilter(self, obj, event):
        t = event.type()
        if t != QEvent.Type.MouseMove and t != QEvent.Type.MouseButtonPress:
            return False
        if not isinstance(obj, QWidget) or obj.window() is not win:
            return False
        if win.isMaximized() or win.isFullScreen():
            return False

        pos = win.mapFromGlobal(event.globalPosition().toPoint())
        edges = edges_at(pos)

        if t == QEvent.Type.MouseMove:
            if edges:
                shape = cursor_for(edges)
                if self.cursor_active:
                    QApplication.changeOverrideCursor(shape)
                else:
                    QApplication.setOverrideCursor(shape)
                    self.cursor_active = True
            elif self.cursor_active:
                QApplication.restoreOverrideCursor()
                self.cursor_active = False
            return False

        if edges and event.button() == Qt.MouseButton.LeftButton:
            win.windowHandle().startSystemResize(edges)
            return True
        return False

win.setWindowFlag(Qt.WindowType.FramelessWindowHint)
win.setMinimumSize(300, 200)
for w in [win] + win.findChildren(QWidget):
    w.setMouseTracking(True)

resize_filter = ResizeFilter()
QApplication.instance().installEventFilter(resize_filter)

win.show()
app.exec()