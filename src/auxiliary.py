import time

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QColor
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget


def hex_to_rgb(hex_color) -> tuple:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b) -> str:
    if not all(0 <= x <= 255 for x in [r, g, b]):
        return None  # Invalid input

    return "{:02X}{:02X}{:02X}".format(r, g, b)


def get_array_from_image(image_path: str) -> np.ndarray:
    # Keep QImage as instance variable or extend its lifetime
    original_image = QImage(image_path)  # Store as instance variable
    if original_image.isNull():
        raise ValueError(f"Failed to load image: {image_path}")

    oi_width: int = original_image.width()
    oi_height: int = original_image.height()

    # Create a copy of the data instead of using direct buffer
    original_image = original_image.convertToFormat(QImage.Format_RGBA8888)
    ptr = original_image.bits()
    ptr.setsize(oi_height * oi_width * 4)
    # Create a copy of the data
    arr: np.ndarray = np.array(ptr).reshape((oi_height, oi_width, 4))
    return arr[:, :, :3].copy()  # Return an explicit copy


def resetTimer(text):
    print(f"\n{text}")
    return time.time()


def create_legend_item(color_RGB, label_text, on_click=None):
    """Helper function to create a legend item"""
    item_layout = QHBoxLayout()

    # Create color square
    color_label = QLabel()
    color_pixmap = QPixmap(15, 15)
    color_pixmap.fill(QColor(*color_RGB))
    color_label.setPixmap(color_pixmap)

    # Create text label
    text_label = QLabel(label_text)
    text_label.setStyleSheet("font-size: 10px;")
    
    # Make clickable if on_click is provided
    if on_click:
        # Create a widget container to make the legend item clickable
        container = QWidget()
        container.setCursor(Qt.PointingHandCursor)  # Show hand cursor on hover
        container.setToolTip(f"Click to select {label_text}")
        
        # Add widgets to layout
        inner_layout = QHBoxLayout(container)
        inner_layout.setContentsMargins(2, 0, 2, 0)  # Small padding
        inner_layout.addWidget(color_label)
        inner_layout.addWidget(text_label)
        inner_layout.addStretch()
        
        # Connect mouse press event via mousePressEvent
        container.mousePressEvent = lambda event: on_click()
        
        # Add container widget to layout
        item_layout.addWidget(container)
    else:
        # Non-clickable layout
        item_layout.addWidget(color_label)
        item_layout.addWidget(text_label)
        item_layout.addStretch()

    return item_layout


def convert_key_string_to_qt(key_str: str) -> int:
    # Function key mapping
    if len(key_str) > 1 and key_str.startswith('F'):
        try:
            fkey_num = int(key_str[1:])
            return getattr(Qt, f'Key_F{fkey_num}')
        except (ValueError, AttributeError):
            return None

    if 'A' <= key_str <= 'Z':
        return ord(key_str)