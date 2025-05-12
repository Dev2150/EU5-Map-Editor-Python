"""
UI utility functions for the Victoria 3 Map Editor.
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt


def create_simple_dialog(parent, title, message, button_text="OK"):
    """
    Create a simple dialog with a message and an OK button.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message
        button_text: Text for the button (default: "OK")
        
    Returns:
        QDialog instance
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout()
    label = QLabel(message)
    label.setWordWrap(True)
    layout.addWidget(label)
    ok_button = QPushButton(button_text)
    ok_button.clicked.connect(dialog.accept)
    layout.addWidget(ok_button)
    dialog.setLayout(layout)
    return dialog


def create_progress_dialog(parent, title, message, modal=True):
    """
    Create a progress dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message
        modal: Whether the dialog should be modal (default: True)
        
    Returns:
        QDialog instance and QLabel for updating the message
    """
    progress = QDialog(parent)
    progress.setWindowTitle(title)
    if modal:
        progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumWidth(400)
    
    progress_layout = QVBoxLayout()
    progress_message = QLabel(message)
    progress_layout.addWidget(progress_message)
    progress.setLayout(progress_layout)
    
    return progress, progress_message


def show_warning_dialog(parent, title, message, info_text=None):
    """
    Show a warning dialog with Yes/No buttons.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message
        info_text: Optional additional information
        
    Returns:
        True if Yes was clicked, False otherwise
    """
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    if info_text:
        msg.setInformativeText(info_text)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.No)
    
    return msg.exec_() == QMessageBox.Yes


def show_error_dialog(parent, title, message, details=None):
    """
    Show an error dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message
        details: Optional error details
        
    Returns:
        None
    """
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    if details:
        msg.setDetailedText(details)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()


def show_save_changes_dialog(parent, title="Unsaved Changes"):
    """
    Show a dialog asking to save unsaved changes.
    
    Args:
        parent: Parent widget
        title: Dialog title
        
    Returns:
        QMessageBox.Yes, QMessageBox.No, or QMessageBox.Cancel
    """
    return QMessageBox.question(
        parent, title,
        'You have unsaved changes. Do you want to export before quitting?',
        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        QMessageBox.Yes
    ) 