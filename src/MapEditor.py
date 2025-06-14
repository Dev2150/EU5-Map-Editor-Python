# (arr_locations, modified_pixmap, dict_locations, location_to_v3TerrainType, location_to_koppen, koppen_details)
import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QPixmap, QImage, QIntValidator, QIcon
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QGraphicsScene, QLineEdit, QWidget, QPushButton, QApplication
from PyQt5.QtWidgets import QFileDialog, QDialog, QComboBox, QToolBar, QMainWindow, QAction, QStatusBar, QProgressDialog
from PyQt5.QtWidgets import QScrollArea, QFrame
from numpy import ndarray
from datetime import datetime
import os
import time
import json
import pickle
import sys
import subprocess
from PyQt5.QtWidgets import QSizePolicy

from CustomGraphicsView import CustomGraphicsView
from auxiliary import rgb_to_hex, hex_to_rgb, create_legend_item, convert_key_string_to_qt
from config import UNKNOWN_REGION, active_style, inactive_style

# Default map type is now managed by settings in editor_settings.json

MAP_TYPE_BUTTON_WIDTH = 100

class MapEditor(QMainWindow):
    def __init__(self, p_arr_locations: ndarray, p_feature_pixmaps: dict, p_locations: dict,
                 p_location_to_v3TerrainType: dict, p_feature_data: dict):
        super().__init__()
        
        # Set window icon - use absolute path for Windows
        icon_path = os.path.abspath(os.path.join("res", "icons", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Set the window title here
        self.setWindowTitle("Project Caesar Map Editor")
        
        self.picker_pixmap_RGB = None
        self.picker_map_type = None
        self.original_array = p_arr_locations
        self.feature_pixmaps = p_feature_pixmaps
        self.locations = p_locations
        self.location_to_v3TerrainType = p_location_to_v3TerrainType
        self.feature_data = p_feature_data

        # Try to load icon directory from settings
        self.icon_directory = os.path.join("res", "icons", "feather")
        try:
            if os.path.exists("editor_settings.json"):
                with open("editor_settings.json", "r") as f:
                    settings = json.load(f)
                    if "icon_directory" in settings:
                        custom_icon_dir = settings["icon_directory"]
                        if os.path.exists(custom_icon_dir):
                            self.icon_directory = custom_icon_dir
                            print(f"Using custom icon directory: {self.icon_directory}")
        except Exception as e:
            print(f"Error loading custom icon directory: {e}")

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Setup GUI
        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene, self)

        bottom_layout = self.create_bottom_GUI()

        # Create toolbar
        self.create_toolbar()

        self.create_legend_layout()

        qhb_picker = QHBoxLayout()
        self.picker_lbl_status = QLabel('Clipboard: ')
        # self.picker_lbl_status.setMaximumWidth(150)
        qhb_picker.addWidget(self.picker_lbl_status)
        self.picker_pixmap = QPixmap(20, 20)
        self.picker_lbl_pixmap = QLabel('')
        self.picker_lbl_pixmap.setMaximumWidth(30)
        qhb_picker.addWidget(self.picker_lbl_pixmap)
        self.picker_lbl_map_type_display = QLabel('')
        qhb_picker.addWidget(self.picker_lbl_map_type_display)
        self.picker_lbl_description = QLabel('Empty')
        # self.picker_lbl_description.setMaximumWidth(200)
        qhb_picker.addWidget(self.picker_lbl_description)
        
        # Add undo counter label
        qhb_picker.addSpacing(20)  # Add space before the counter
        self.undo_counter_label = QLabel("Changes: 0")
        self.undo_counter_label.setStyleSheet("font-weight: bold; color: #3366cc;")
        qhb_picker.addWidget(self.undo_counter_label)
        
        qhb_picker.addStretch()

        # Create main vertical layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.legend_container)
        main_layout.addLayout(qhb_picker)
        main_layout.addWidget(self.view)
        main_layout.addLayout(bottom_layout)
        central_widget.setLayout(main_layout)

        # Initialize button states and legend
        self.set_map_type('climate')  # Default to climate, but this will be overridden by main.py

        # Add picker-related attributes
        self.is_picker_active = False
        for featureID, feature in self.feature_data.items():
            feature['isEdited'] = False
            feature['copied_value'] = None

        # Add undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []
        # self.max_undo_steps = 1000000
        
        # Track last export state
        self.last_export_stack_size = 0
        
        # Initialize undo counter
        self.update_undo_counter()

    def create_toolbar(self):
        """Create the main toolbar with all map type buttons and actions"""
        # Create tools toolbar (top row)
        toolbar = QToolBar("Tools")
        toolbar.setWindowTitle("Tools")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        # Add a label at the start of the toolbar to identify it
        tools_label = QLabel("Tools: ")
        tools_label.setStyleSheet("font-weight: bold; margin-right: 10px;")
        toolbar.addWidget(tools_label)
        
        # Add tools toolbar at the top
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        
        # Add undo/redo actions
        
        undo_action = self.create_action("Undo", "undo", "Undo last change (Ctrl+Z)", self.undo_last_fill)
        toolbar.addAction(undo_action)
        
        redo_action = self.create_action("Redo", "redo", "Redo last change (Ctrl+Y)", self.redo_last_fill)
        toolbar.addAction(redo_action)
        
        toolbar.addSeparator()
        
        # Add feature selector action
        selector_action = self.create_action("Feature Selector", "feature-selector", 
                                           "Select a feature (Ctrl+B)", self.show_feature_selector)
        toolbar.addAction(selector_action)

        # Add search action
        search_action = self.create_action("Search", "search", "Search for province (F)", self.show_search)
        toolbar.addAction(search_action)

        # Add save, open, and help actions
        toolbar.addSeparator()
        
        save_action = self.create_action("Save", "save", "Save/Export changes (Ctrl+S)", self.export_changes)
        toolbar.addAction(save_action)
        
        restart_action = self.create_action("Home", "home", "Restart the application", self.restart_application)
        toolbar.addAction(restart_action)
        
        help_action = self.create_action("Help", "help", "Show help dialog (Ctrl+H)", self.show_help_dialog)
        toolbar.addAction(help_action)
        
        # Create map type toolbar (bottom row)
        map_type_toolbar = QToolBar("Map Types")
        map_type_toolbar.setWindowTitle("Map Types")
        map_type_toolbar.setMovable(False)
        map_type_toolbar.setFloatable(False)
        
        # Create a scrollable container for map type buttons
        map_type_container = QWidget()
        map_type_layout = QHBoxLayout(map_type_container)
        map_type_layout.setContentsMargins(0, 0, 0, 0)
        map_type_layout.setSpacing(2)
        
        # Add a label at the start of the layout to identify it
        map_type_label = QLabel("Map Types: ")
        map_type_label.setStyleSheet("font-weight: bold; margin-right: 10px;")
        map_type_layout.addWidget(map_type_label)
        
        # Create buttons for each map type
        for feature in self.feature_data:
            hotkeyVar = self.feature_data[feature]['hotkey']
            hotkey = hotkeyVar[0] if isinstance(hotkeyVar, list) else hotkeyVar
            
            button = QPushButton(f"{self.feature_data[feature]['display_name']} ({chr(hotkey)})")
            button.setCheckable(True)  # Make buttons checkable
            button.setProperty("feature", feature)  # Store feature name as property
            button.clicked.connect(lambda checked, f=feature: self.set_map_type(f))
            button.setStyleSheet(inactive_style)  # Set initial style
            button.setMinimumWidth(80)  # Ensure buttons have reasonable width
                        
            # Disable buttons for maps that aren't loaded
            if feature not in self.feature_pixmaps:
                button.setEnabled(False)
                button.setToolTip("This map was not loaded. Select it in the startup window to enable.")
                button.setStyleSheet("background-color: #f0f0f0; color: #a0a0a0; border: 1px solid #d0d0d0;")
            
            self.feature_data[feature]['button'] = button
            map_type_layout.addWidget(button)
        
        # Add stretch to push buttons to the left
        map_type_layout.addStretch()
        
        # Create scroll area and add the container to it
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)  # Remove the border
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(map_type_container)
        scroll_area.setMinimumWidth(300)  # Set a minimum width to ensure at least a few buttons are visible
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        scroll_area.setMaximumHeight(40)  # Limit the height to prevent it from taking too much vertical space
        
        # Add the scroll area to the toolbar
        action = map_type_toolbar.addWidget(scroll_area)
        # Make the widget take up all available width
        action.setVisible(True)
        
        # Add toolbar below the tools toolbar
        self.addToolBarBreak(Qt.TopToolBarArea)
        self.addToolBar(Qt.TopToolBarArea, map_type_toolbar)
        
        # Store map type toolbar for later access
        self.map_type_toolbar = map_type_toolbar

    def create_action(self, text, icon_name, tooltip, callback):
        """Helper method to create a QAction with icon (if exists) or text fallback"""
        # Always show text in toolbar buttons
        action = QAction(text, self)
        
        # Try to load the icon from several possible locations and formats
        icon_found = False
        
        # Check for SVG icon
        icon_path = os.path.join(self.icon_directory, icon_name)
        if os.path.exists(icon_path):
            action.setIcon(QIcon(icon_path))
            icon_found = True
        
        # Check for SVG with extension explicitly specified
        if not icon_found and not icon_name.lower().endswith('.svg'):
            icon_path = os.path.join(self.icon_directory, f"{icon_name}.svg")
            if os.path.exists(icon_path):
                action.setIcon(QIcon(icon_path))
                icon_found = True
        
        # Check for PNG icon
        if not icon_found:
            png_path = os.path.join(self.icon_directory, f"{icon_name.split('.')[0]}.png")
            if os.path.exists(png_path):
                action.setIcon(QIcon(png_path))
                icon_found = True
        
        # If no icon was found, don't worry, just use text
        if not icon_found:
            print(f"Icon not found: {icon_name}. Using text instead.")
        
        action.setToolTip(tooltip)
        action.triggered.connect(callback)
        
        return action

    def show_search(self):
        """Show the search box"""
        self.search_box.show()
        self.search_box.setFocus()

    def copy_feature(self):
        """Copy the current feature from the hovered province"""
        self.is_picker_active = True
        try:
            # Check if the feature type exists for this location
            if self.current_map_type not in self.locations[self.original_color_HEX]:
                self.picker_lbl_pixmap.clear()
                self.picker_lbl_map_type_display.clear()
                self.picker_lbl_description.setText(f'Feature {self.current_map_type} not available for this province')
                return
                
            feature_key = self.locations[self.original_color_HEX][self.current_map_type]
            
            # Check if the feature key exists in the feature data
            if feature_key not in self.feature_data[self.current_map_type]['labels']:
                self.picker_lbl_pixmap.clear()
                self.picker_lbl_map_type_display.clear()
                self.picker_lbl_description.setText(f'Feature key {feature_key} not found in {self.current_map_type} data')
                return
                
            feature_current = self.feature_data[self.current_map_type]['labels'][feature_key]
            color_HEX = feature_current['color']
            color_RGB = hex_to_rgb(color_HEX)
            self.picker_pixmap.fill(QColor(*color_RGB))
            self.picker_lbl_pixmap.setPixmap(self.picker_pixmap)
            desc_short = str(feature_current['desc_short'])
            self.picker_lbl_description.setText(desc_short)
            self.picker_map_type = self.current_map_type
            self.picker_pixmap_RGB = color_RGB
            self.picker_key = feature_key
            self.picker_lbl_map_type_display.setText(f"{self.feature_data[self.current_map_type]['display_name']} - ")
        except Exception as e:
            self.picker_lbl_pixmap.clear()
            self.picker_lbl_map_type_display.clear()
            self.picker_lbl_description.setText(f'Error: {str(e)}')

    def paste_feature(self):
        """Paste the copied feature to the province under the cursor"""
        start_time_block = time.perf_counter()
        
        prev_time = time.perf_counter()
        cursor_pos = self.view.mapFromGlobal(self.cursor().pos())
        current_time = time.perf_counter()
        print(f"Time for cursor_pos: {current_time - prev_time:.1f} s")
        prev_time = current_time

        scene_pos = self.view.mapToScene(cursor_pos)
        current_time = time.perf_counter()
        print(f"Time for scene_pos: {current_time - prev_time:.1f} s")
        prev_time = current_time

        color_HEX = self.fill_region(int(scene_pos.x()), int(scene_pos.y()))
        current_time = time.perf_counter()
        print(f"Time for fill_region: {current_time - prev_time:.1f} s")
        prev_time = current_time

        if color_HEX:
            self.locations[color_HEX][self.picker_map_type] = self.picker_key
            current_time = time.perf_counter()
            print(f"Time for updating locations: {current_time - prev_time:.1f} s")
        
        end_time_block = time.perf_counter()
        print(f"Total time for paste operation: {end_time_block - start_time_block:.1f} s\n")
        
    def create_legend_layout(self):
        # Create legend box with fixed height
        self.legend_layout = QHBoxLayout()
        self.legend_layout.setContentsMargins(5, 5, 5, 5)  # Add some padding
        # Cache for legend widgets
        self.legend_cache = {
            'climate': None,
            'topography': None,
            'vegetation': None
        }
        # Create a container widget with fixed height
        self.legend_container = QWidget()
        self.legend_container.setFixedHeight(40)  # Adjust this value as needed
        self.legend_container.setLayout(self.legend_layout)

    def create_bottom_GUI(self):
        # Initialize pixmap_item with default map
        self.pixmap_item = self.scene.addPixmap(self.feature_pixmaps['climate'])
        # Create feature display components
        # self.pixmap_item = self.scene.addPixmap(self.feature_pixmaps['climate'])
        self.feature_displays = {}
        self.createFeatureDisplayComponent('location')
        for feature_type in self.feature_data:
            self.createFeatureDisplayComponent(feature_type)
        self.current_map_type = ''
        # Add search box (hidden by default)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search for location...")
        self.search_box.hide()
        self.search_box.returnPressed.connect(self.on_search)
        self.search_box.setMaximumWidth(200)
        bottom_layout = QHBoxLayout()
        # Create horizontal layout for location information
        hbl_location_base = QHBoxLayout()
        feature_data_current = self.feature_displays['location']
        feature_data_current['lbl_pixmap'].setText('Hover over a location...')
        hbl_location_base.addWidget(feature_data_current['lbl_pixmap'])
        hbl_location_base.addWidget(feature_data_current['desc_short'])
        hbl_location_base.addStretch()
        vbl_location = QVBoxLayout()
        vbl_location.addLayout(hbl_location_base)
        self.lbl_province_name = QLabel('')
        vbl_location.addWidget(self.lbl_province_name)
        self.lbl_province_climate = QLabel('')
        vbl_location.addWidget(self.lbl_province_climate)
        vbl_location.addWidget(self.search_box)
        bottom_layout.addLayout(vbl_location, 1)
        # Add definition labels
        self.lbl_definition_koppen = QLabel('')
        self.lbl_definition_koppen.setWordWrap(True)  # Enable word wrapping for long definitions
        for feature_type, feature_data_current in self.feature_displays.items():
            if feature_type == 'location':
                continue
            hbl_feature = QHBoxLayout()
            hbl_feature.addWidget(feature_data_current['lbl_pixmap'])
            hbl_feature.addWidget(feature_data_current['desc_short'])
            hbl_feature.addStretch()

            vbl_feature = QVBoxLayout()  # Create new layout variable instead of assigning to string
            vbl_feature.addLayout(hbl_feature)
            vbl_feature.addWidget(feature_data_current['desc_long'])
            stretch = feature_data_current['bottom_layout_width_weight'] if 'bottom_layout_width_weight' in feature_data_current else 1
            bottom_layout.addLayout(vbl_feature, stretch)
        return bottom_layout

    def createFeatureDisplayComponent(self, feature_type):
        self.feature_displays[feature_type] = {
            'pixmap': QPixmap(20, 20),
            'lbl_pixmap': QLabel(),
            'desc_short': QLabel(''),
            'desc_long': QLabel('') # if feature_type == 'climate' else None
        }
        self.feature_displays[feature_type]['lbl_pixmap'].setFixedSize(20, 20)
        self.feature_displays[feature_type]['desc_long'].setWordWrap(True)  # Enable word wrapping for long definitions

    def update_bottom_layers(self, x, y):
        if not (0 <= y < self.original_array.shape[0] and 0 <= x < self.original_array.shape[1]):
            return

        self.original_color_RGB = tuple(self.original_array[y, x])
        self.original_color_HEX = rgb_to_hex(*self.original_color_RGB)

        # Update region color square
        loc = self.feature_displays['location']
        loc['pixmap'].fill(QColor(*self.original_color_RGB))
        loc['lbl_pixmap'].setPixmap(loc['pixmap'])

        # Update text labels
        loc['desc_short'].setText(f"{self.original_color_HEX}")
        region_name = self.locations.get(self.original_color_HEX, UNKNOWN_REGION)
        climate_V3 = ''
        if region_name != UNKNOWN_REGION:
            region_name = region_name['name']
            climate_V3 = self.location_to_v3TerrainType[self.original_color_HEX]

            climate_abbreviation = self.locations[self.original_color_HEX]['climate']
            if climate_abbreviation in ['', 'W']:
                for featureType, feature in self.feature_displays.items():
                    feature['lbl_pixmap'].clear()
                    feature['desc_short'].setText('')
                    feature['desc_long'].setText('')
            else:
                for feature_type, feature in self.feature_data.items():
                    feature_display_current = self.feature_displays[feature_type]
                    
                    # Skip if this feature type doesn't exist for this location or isn't loaded
                    if feature_type not in self.locations[self.original_color_HEX] or feature_type not in self.feature_pixmaps:
                        feature_display_current['lbl_pixmap'].clear()
                        feature_display_current['desc_short'].setText('')
                        feature_display_current['desc_long'].setText('')
                        continue
                        
                    feature_key = self.locations[self.original_color_HEX][feature_type]
                    
                    # Skip if the feature key doesn't exist in labels
                    if feature_key not in self.feature_data[feature_type]['labels']:
                        feature_display_current['lbl_pixmap'].clear()
                        feature_display_current['desc_short'].setText(f"{feature['display_name']} - Not available")
                        feature_display_current['desc_long'].setText('')
                        continue
                        
                    feature_current = self.feature_data[feature_type]['labels'][feature_key]
                    pixmap_current = feature_display_current['pixmap']
                    color_HEX = feature_current['color']
                    pixmap_current.fill(QColor(*hex_to_rgb(color_HEX)))
                    feature_display_current['lbl_pixmap'].setPixmap(pixmap_current)
                    desc_short = feature_current['desc_short']

                    text = f"{feature['display_name']} "
                    if feature_type == 'climate':
                        text += f"({feature_key}) "
                    text += f"- {desc_short} "
                    desc_long = feature_current['desc_long']
                    feature_display_current['desc_long'].setText(desc_long)
                    feature_display_current['desc_short'].setText(text)

        self.lbl_province_name.setText(f"State: {region_name}")
        self.lbl_province_climate.setText(f"Climate (Victoria 3): {climate_V3}")

    def set_map_type(self, active_map: str):
        """Set the active map layer and update the UI accordingly"""
        # Only proceed if the map is actually changing
        if self.current_map_type == active_map:
            return
            
        # Check if the map is available
        if active_map not in self.feature_pixmaps:
            print(f"Warning: Map type '{active_map}' not loaded")
            return

        # Update the map display
        self.pixmap_item.setPixmap(self.feature_pixmaps[active_map])

        # Update button states
        for feature_type, feature in self.feature_data.items():
            if 'button' in feature:
                # Skip updating styles for disabled buttons
                if feature_type not in self.feature_pixmaps:
                    continue
                
                is_active = feature_type == active_map
                feature['button'].setChecked(is_active)
                feature['button'].setStyleSheet(active_style if is_active else inactive_style)

        self.current_map_type = active_map
        self.update_legend(active_map)

    def update_legend(self, map_type: str):
        """Update the legend based on the current map type"""
        # Clear existing legend items
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Clear nested layout
                while item.layout().count():
                    nested_item = item.layout().takeAt(0)
                    if nested_item.widget():
                        nested_item.widget().deleteLater()
            del item

        # Create new legend items
        feature_data_current = self.feature_data[map_type]
        if not feature_data_current['isNumerical']:
            for label_name, label in feature_data_current['labels'].items():
                if map_type == 'climate' and label_name in ['W']:
                    continue
                
                # Create a proper closure for the callback
                def create_callback(map_type_arg, key_arg):
                    return lambda: self.select_feature_from_legend(map_type_arg, key_arg)
                
                callback = create_callback(map_type, label_name)
                
                item_layout = create_legend_item(
                    hex_to_rgb(label['color']),
                    f"{label_name}",
                    on_click=callback)
                self.legend_layout.addLayout(item_layout)

            self.legend_layout.addStretch()

    def select_feature_from_legend(self, map_type, feature_key):
        """Select a feature from the legend"""
        self.is_picker_active = True
        
        # Set picker values (similar to show_feature_selector)
        feature_current = self.feature_data[map_type]['labels'][feature_key]
        color_HEX = feature_current['color']
        color_RGB = hex_to_rgb(color_HEX)
        
        self.picker_pixmap.fill(QColor(*color_RGB))
        self.picker_lbl_pixmap.setPixmap(self.picker_pixmap)
        desc_short = str(feature_current['desc_short'])
        self.picker_lbl_description.setText(desc_short)
        self.picker_map_type = map_type
        self.picker_pixmap_RGB = color_RGB
        self.picker_key = feature_key
        self.picker_lbl_map_type_display.setText(f"{self.feature_data[map_type]['display_name']} - ")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F:
            self.show_search()
        elif event.key() == Qt.Key_Escape:
            self.search_box.hide()
            self.search_box.clear()
            self.view.setFocus()
        elif event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.export_changes()
            elif event.key() == Qt.Key_B:
                self.show_feature_selector()
            elif event.key() == Qt.Key_C:
                self.copy_feature()
                return
            elif event.key() == Qt.Key_V:
                self.paste_feature()
            elif event.key() == Qt.Key_Z:
                self.undo_last_fill()
            elif event.key() == Qt.Key_Y:
                self.redo_last_fill()
            elif event.key() == Qt.Key_H:
                self.show_help_dialog()
            elif event.key() == Qt.Key_Q:
                # Handle Ctrl+Q for quitting
                self.close()  # This will trigger closeEvent
        else:
            for feature_type, feature in self.feature_data.items():
                if 'hotkey' in feature and event.key() in feature['hotkey']:
                    # Skip maps that aren't loaded
                    if feature_type in self.feature_pixmaps:
                        self.set_map_type(feature_type)
                    break
        super().keyPressEvent(event)

    def on_search(self):
        search_text = self.search_box.text().lower()

        # Search through provinces
        for hex_color, province_data in self.locations.items():
            if province_data['name'].lower().startswith(search_text):
                # Find a pixel with this color
                color_rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
                mask = (self.original_array == color_rgb).all(axis=-1)
                if mask.any():
                    # Get center of the province
                    y_coords, x_coords = np.where(mask)
                    center_x = x_coords.mean()
                    center_y = y_coords.mean()

                    # Center view on the province
                    self.view.centerOn(center_x, center_y)

                    # Hide and clear search box
                    self.search_box.hide()
                    self.search_box.clear()
                    self.view.setFocus()
                    return

        # If no match found, could add some feedback here
        self.search_box.setStyleSheet("background-color: #FFE4E1;")  # Light red
        QTimer.singleShot(1000, lambda: self.search_box.setStyleSheet(""))

    def fill_region(self, x: int, y: int) -> str | None:
        start_time_fill_region = time.perf_counter()
        prev_time = start_time_fill_region

        # Instruction 1: Initial checks
        if not self.picker_map_type or not (0 <= y < self.original_array.shape[0] and 0 <= x < self.original_array.shape[1]):
            current_time = time.perf_counter()
            print(f"fill_region - Time for initial boundary/picker_map_type check: {current_time - prev_time:.1f} s")
            return
        current_time = time.perf_counter()
        print(f"fill_region - Time for initial boundary/picker_map_type check: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 2: Current map type check
        if self.current_map_type != self.picker_map_type:
            current_time = time.perf_counter()
            print(f"fill_region - Time for current_map_type check: {current_time - prev_time:.1f} s")
            return
        current_time = time.perf_counter()
        print(f"fill_region - Time for current_map_type check: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Color to be changed
        # Instruction 3: Get target_color_RGB
        target_color_RGB = tuple(self.original_array[y, x])
        current_time = time.perf_counter()
        print(f"fill_region - Time for target_color_RGB: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 4: Get target_color_HEX
        target_color_HEX = rgb_to_hex(*target_color_RGB)
        current_time = time.perf_counter()
        print(f"fill_region - Time for target_color_HEX: {current_time - prev_time:.1f} s")
        prev_time = current_time
        
        # Instruction 5: Check if target_color_HEX in locations
        if target_color_HEX not in self.locations:
            current_time = time.perf_counter()
            print(f"fill_region - Time for locations check: {current_time - prev_time:.1f} s")
            return
        current_time = time.perf_counter()
        print(f"fill_region - Time for locations check: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Get the target feature and color
        # Instruction 6: Get feature_key
        feature_key = self.locations[target_color_HEX][self.picker_map_type]
        current_time = time.perf_counter()
        print(f"fill_region - Time for feature_key retrieval: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 7: Check if feature_key in labels
        if feature_key not in self.feature_data[self.picker_map_type]['labels']:
            current_time = time.perf_counter()
            print(f"fill_region - Time for feature_key in labels check: {current_time - prev_time:.1f} s")
            return
        current_time = time.perf_counter()
        print(f"fill_region - Time for feature_key in labels check: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Store the change in undo stack before applying the new feature
        # Instruction 8: Append to undo_stack
        self.undo_stack.append({
            'map_type': self.picker_map_type,
            'location_HEX': target_color_HEX,
            'old_feature': feature_key,
            'new_feature': self.picker_key
        })
        current_time = time.perf_counter()
        print(f"fill_region - Time for undo_stack.append: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 9 & 10: Manage undo_stack size
        # if len(self.undo_stack) > self.max_undo_steps:
        #    self.undo_stack.pop(0)
        current_time = time.perf_counter()
        print(f"fill_region - Time for undo_stack size management: {current_time - prev_time:.1f} s")
        prev_time = current_time
        
        # Instruction 11: Clear redo_stack
        self.redo_stack.clear()
        current_time = time.perf_counter()
        print(f"fill_region - Time for redo_stack.clear: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Update the location's feature
        # Instruction 12: Update self.locations
        self.locations[target_color_HEX][self.picker_map_type] = self.picker_key
        current_time = time.perf_counter()
        print(f"fill_region - Time for updating self.locations: {current_time - prev_time:.1f} s")
        prev_time = current_time
        
        # Apply the visual change
        # Instruction 13: Call _apply_feature_change
        self._apply_feature_change(self.picker_map_type, target_color_RGB, self.picker_pixmap_RGB)
        current_time = time.perf_counter()
        print(f"fill_region - Time for _apply_feature_change: {current_time - prev_time:.1f} s")
        prev_time = current_time
        
        # Update the undo counter
        self.update_undo_counter()

        end_time_fill_region = time.perf_counter()
        print(f"fill_region - Total time: {end_time_fill_region - start_time_fill_region:.4f} s\n")
        return target_color_HEX

    def _apply_feature_change(self, map_type: str, target_color_RGB: tuple, new_color_RGB: tuple) -> None:
        """Helper method to apply visual changes to the pixmap"""
        start_time_block = time.perf_counter()
        prev_time = start_time_block
        print(f"\n--- _apply_feature_change ({map_type}) ---")

        # Instruction 1: Set map type
        self.set_map_type(map_type)
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for set_map_type: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 2: Get QImage from pixmap
        image_feature_pixmap = self.feature_pixmaps[map_type].toImage()
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for toImage(): {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 3: Get image dimensions
        width, height = image_feature_pixmap.width(), image_feature_pixmap.height()
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for width(), height(): {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Convert QImage to numpy array for faster processing
        # Instruction 4: Get image bits
        ptr = image_feature_pixmap.bits()
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for bits(): {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 5: Set size of pointer
        ptr.setsize(height * width * 4)  # 4 bytes per pixel (RGBA)
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for setsize(): {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 6: Create numpy array from buffer
        arr_new_image = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for np.frombuffer().reshape(): {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Find matching region in original array
        # Optimized mask creation using component-wise comparison
        mask = ((self.original_array[:,:,0] == target_color_RGB[0]) & 
                (self.original_array[:,:,1] == target_color_RGB[1]) & 
                (self.original_array[:,:,2] == target_color_RGB[2]))
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for mask creation: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Create color array once for faster assignment
        color_array = np.array([new_color_RGB[2], new_color_RGB[1], new_color_RGB[0], 255], dtype=np.uint8)
        
        # Use broadcasting for faster assignment
        arr_new_image[mask] = color_array
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for arr_new_image[mask] assignment: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Convert back to QPixmap
        # Instruction 9: Create QImage from numpy array
        new_pixmap_image = QImage(arr_new_image.data, width, height, QImage.Format_ARGB32)
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for QImage creation from data: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 10: Create QPixmap from QImage
        new_pixmap = QPixmap.fromImage(new_pixmap_image)
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for QPixmap.fromImage(): {current_time - prev_time:.1f} s")
        prev_time = current_time
        
        # Update the display
        # Instruction 11: Update feature_pixmaps dictionary
        self.feature_pixmaps[map_type] = new_pixmap
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for self.feature_pixmaps assignment: {current_time - prev_time:.1f} s")
        prev_time = current_time

        # Instruction 12: Set pixmap on item
        self.pixmap_item.setPixmap(new_pixmap)
        current_time = time.perf_counter()
        print(f"_apply_feature_change - Time for self.pixmap_item.setPixmap(): {current_time - prev_time:.1f} s")
        
        end_time_block = time.perf_counter()
        print(f"_apply_feature_change - Total time: {end_time_block - start_time_block:.4f} s\n")

    def update_undo_counter(self):
        """Update the undo counter in the status bar"""
        self.undo_counter_label.setText(f"Changes: {len(self.undo_stack)}")

    def undo_last_fill(self) -> None:
        if not self.undo_stack:
            QApplication.beep()  # Play error sound
            return
        change = self.undo_stack.pop()
        self.redo_stack.append(change)
        
        # Get the old feature's color
        map_type = change['map_type']
        old_feature = change['old_feature']
        old_color = hex_to_rgb(self.feature_data[map_type]['labels'][old_feature]['color'])
        
        # Update the location's feature back to the old one
        self.locations[change['location_HEX']][map_type] = old_feature
        
        # Apply the visual change
        target_color_RGB = hex_to_rgb(change['location_HEX'])
        self._apply_feature_change(map_type, target_color_RGB, old_color)
        
        # Update undo counter
        self.update_undo_counter()
        
        # If we've undone all changes, reset the last export stack size
        if not self.undo_stack and self.last_export_stack_size > 0:
            self.last_export_stack_size = 0

    def redo_last_fill(self) -> None:
        if not self.redo_stack:
            QApplication.beep()  # Play error sound
            return
        change = self.redo_stack.pop()
        self.undo_stack.append(change)
        
        # Get the new feature's color
        map_type = change['map_type']
        new_feature = change['new_feature']
        new_color = hex_to_rgb(self.feature_data[map_type]['labels'][new_feature]['color'])
        
        # Update the location's feature to the new one
        self.locations[change['location_HEX']][map_type] = new_feature
        
        # Apply the visual change
        target_color_RGB = hex_to_rgb(change['location_HEX'])
        self._apply_feature_change(map_type, target_color_RGB, new_color)
        
        # Update undo counter
        self.update_undo_counter()

    def export_changes(self):
        """Export modified locations to a timestamped folder"""

        # Create exports directory if it doesn't exist
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = os.path.join('exports', timestamp)
        os.makedirs(export_dir, exist_ok=True)

        # Get all columns except name, x, y
        excluded_columns = {'name', 'x', 'y'}
        columns_to_export = set()
        
        # Find all unique columns across all locations
        for location_data in self.locations.values():
            columns_to_export.update(key for key in location_data.keys() if key not in excluded_columns)

        # Export each column to a separate file
        for column in columns_to_export:
            export_path = os.path.join(export_dir, f'{column}.csv')
            with open(export_path, 'w', encoding='utf-8') as f:
                for hex_code, location_data in self.locations.items():
                    if column in location_data:
                        f.write(f"{hex_code},{location_data[column]}\n")
            print(f"Exported {column} data to {export_path}")
        
        # Save the undo stack and current map type to a file
        project_data = {
            'undo_stack': self.undo_stack,
            'current_map_type': self.current_map_type,
            'loaded_maps': list(self.feature_pixmaps.keys())
        }
        
        project_file = os.path.join(export_dir, 'project_state.json')
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2)
        
        print(f"Saved project state with {len(self.undo_stack)} changes to {project_file}")

        # Update last export state
        self.last_export_stack_size = len(self.undo_stack)

        # Show success message
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Successful")
        layout = QVBoxLayout()
        label = QLabel(f"Successfully exported data to {export_dir}")
        layout.addWidget(label)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)
        dialog.setLayout(layout)
        dialog.exec_()

    def show_feature_selector(self):
        """Shows a dialog with a dropdown of all features for the current map type"""
        if not self.current_map_type or self.current_map_type not in self.feature_data:
            return
            
        if self.current_map_type not in self.feature_pixmaps:
            # Show error message if the current map type isn't loaded
            QApplication.beep()
            dialog = QDialog(self)
            dialog.setWindowTitle("Map Not Loaded")
            layout = QVBoxLayout()
            message = QLabel(f"The {self.feature_data[self.current_map_type]['display_name']} map is not loaded.\n"
                            "Please restart the application and select this map in the startup window.")
            layout.addWidget(message)
            button = QPushButton("OK")
            button.clicked.connect(dialog.accept)
            layout.addWidget(button)
            dialog.setLayout(layout)
            dialog.exec_()
            return
            
        dialog = QDialog(self)
        feature_data_current = self.feature_data[self.current_map_type]
        dialog.setWindowTitle(f"Select {feature_data_current['display_name']} Feature")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # Handle gradient and non-gradient features differently
        if feature_data_current['isNumerical']:
            # For gradient features, show a text input for value 0-255
            label = QLabel(f"Enter {feature_data_current['display_name']} value (0-255):")
            layout.addWidget(label)
            
            # Create text input for gradient value
            text_input = QLineEdit()
            text_input.setValidator(QIntValidator(0, 255))  # Restrict input to 0-255
            text_input.setText("")  # Default middle value
            layout.addWidget(text_input)
            
            # Preview color
            preview_layout = QHBoxLayout()
            preview_label = QLabel("Preview:")
            preview_layout.addWidget(preview_label)
            
            preview_color = QLabel()
            preview_pixmap = QPixmap(20, 20)
            preview_pixmap.fill(QColor(0, 0, 0))
            preview_color.setPixmap(preview_pixmap)
            preview_layout.addWidget(preview_color)
            layout.addLayout(preview_layout)
            
            # Update preview when text changes
            def update_preview():
                try:
                    value = int(text_input.text())
                    preview_pixmap.fill(QColor(value, value, value))
                    preview_color.setPixmap(preview_pixmap)
                except ValueError:
                    pass
            
            text_input.textChanged.connect(update_preview)
        else:
            # For non-gradient features, show dropdown as before
            label = QLabel(f"Choose a {feature_data_current['display_name']} feature:")
            layout.addWidget(label)
            
            combo = QComboBox()
            feature_labels = feature_data_current['labels']
            
            # Add features to dropdown with both key and description
            for key, feature in feature_labels.items():
                if self.current_map_type == 'climate' and key in ['W']:
                    continue
                
                # Create a pixmap for the color swatch
                color_swatch = QPixmap(16, 16)
                color_rgb = hex_to_rgb(feature['color'])
                color_swatch.fill(QColor(*color_rgb))
                
                # Create an icon from the pixmap
                icon = QIcon(color_swatch)
                
                # Add item with icon, text, and data
                combo.addItem(icon, f"{key} - {feature['desc_short']}", key)
            
            # Set a reasonable row count to make scrolling nicer
            combo.setMaxVisibleItems(15)
            
            layout.addWidget(combo)
        
        # Create buttons
        button_layout = QHBoxLayout()
        select_button = QPushButton("Select")
        cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(select_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Connect buttons
        cancel_button.clicked.connect(dialog.reject)
        select_button.clicked.connect(dialog.accept)
        
        # Show dialog
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            self.is_picker_active = True
            
            if feature_data_current['isNumerical']:
                # Handle gradient feature selection
                try:
                    value = int(text_input.text())
                    if 0 <= value <= 255:
                        # Generate grayscale color
                        color_RGB = (value, value, value)
                        color_HEX = rgb_to_hex(*color_RGB)
                        
                        # Set picker values
                        self.picker_pixmap.fill(QColor(*color_RGB))
                        self.picker_lbl_pixmap.setPixmap(self.picker_pixmap)
                        desc_short = f"Value: {value}"
                        self.picker_lbl_description.setText(desc_short)
                        self.picker_map_type = self.current_map_type
                        self.picker_pixmap_RGB = color_RGB
                        self.picker_key = str(value)  # Store value as string key
                        self.picker_lbl_map_type_display.setText(f"{feature_data_current['display_name']} - ")
                except ValueError:
                    pass
            else:
                # Handle non-gradient feature selection as before
                selected_key = combo.currentData()
                
                # Set picker values (similar to Ctrl+C)
                feature_current = feature_data_current['labels'][selected_key]
                color_HEX = feature_current['color']
                color_RGB = hex_to_rgb(color_HEX)
                
                self.picker_pixmap.fill(QColor(*color_RGB))
                self.picker_lbl_pixmap.setPixmap(self.picker_pixmap)
                desc_short = str(feature_current['desc_short'])
                self.picker_lbl_description.setText(desc_short)
                self.picker_map_type = self.current_map_type
                self.picker_pixmap_RGB = color_RGB
                self.picker_key = selected_key
                self.picker_lbl_map_type_display.setText(f"{feature_data_current['display_name']} - ")

                combo.setFocus()

    def show_help_dialog(self):
        """Shows a dialog with hotkey information"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Hotkeys Help")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Create text with hotkey information
        help_text = """
        Hotkeys:
        
        General:
        - Ctrl+H: Show this help dialog
        - Ctrl+Q: Quit application
        - Ctrl+B: Open feature selector
        - Ctrl+C: Copy feature from current location
        - Ctrl+V: Paste feature at cursor location
        - Ctrl+Z: Undo last change
        - Ctrl+Y: Redo last change
        - F: Open search box
        - ESC: Close search/help box
        
        Map Type Selection:
        - Key in parenthesis: Switch to map (if loaded)
        
        Mouse:
        - Hover over location: View location info
        - Left click + drag: Pan view
        - Mouse wheel: Zoom in/out
        
        Project Files:
        - Save (Ctrl+S): Exports all changes and saves the project state with undo history
        - Restart: Restarts the application (prompts to save if unsaved changes exist)
        
        Note: Some maps may be disabled if they weren't selected in the startup window.
        To enable these maps, restart the application and select them in the startup window.
        """
        
        text_label = QLabel(help_text)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def closeEvent(self, event):
        """Handle window close event and prompt for unsaved changes"""
        if len(self.undo_stack) > self.last_export_stack_size:
            # There are unsaved changes
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                'You have unsaved changes. Do you want to export before quitting?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Export changes then close
                self.export_changes()
                event.accept()
            elif reply == QMessageBox.No:
                # Close without exporting
                event.accept()
            else:
                # Cancel closing
                event.ignore()
        else:
            # No unsaved changes, close normally
            event.accept()
            
    def restart_application(self):
        """Restart the application"""
        if len(self.undo_stack) > self.last_export_stack_size:
            # There are unsaved changes
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                'You have unsaved changes. Do you want to export before restarting?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Export changes then restart
                self.export_changes()
                self._perform_restart()
            elif reply == QMessageBox.No:
                # Restart without exporting
                self._perform_restart()
            # If Cancel, do nothing
        else:
            # No unsaved changes, restart normally
            self._perform_restart()
            
    def _perform_restart(self):
        """Perform the actual restart operation"""
        python = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        subprocess.Popen([python, script_path])
        # Exit the current process
        sys.exit(0)

    def _batch_apply_feature_change(self, map_type, target_color_RGB, new_color_RGB):
        """Optimized version of _apply_feature_change for batch processing"""
        # Get the image from pixmap (only once per batch)
        if not hasattr(self, '_batch_image') or self._batch_map_type != map_type:
            self._batch_map_type = map_type
            self._batch_image = self.feature_pixmaps[map_type].toImage()
            width, height = self._batch_image.width(), self._batch_image.height()
            ptr = self._batch_image.bits()
            ptr.setsize(height * width * 4)  # 4 bytes per pixel (RGBA)
            self._batch_array = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        
        # Find matching region in original array
        mask = ((self.original_array[:,:,0] == target_color_RGB[0]) & 
                (self.original_array[:,:,1] == target_color_RGB[1]) & 
                (self.original_array[:,:,2] == target_color_RGB[2]))
        
        # Create color array for assignment
        color_array = np.array([new_color_RGB[2], new_color_RGB[1], new_color_RGB[0], 255], dtype=np.uint8)
        
        # Update the array
        self._batch_array[mask] = color_array

    def _finalize_feature_changes(self, map_type):
        """Convert the batch-processed array back to a pixmap and update the display"""
        if hasattr(self, '_batch_array') and self._batch_map_type == map_type:
            width, height = self._batch_image.width(), self._batch_image.height()
            new_pixmap_image = QImage(self._batch_array.data, width, height, QImage.Format_ARGB32)
            new_pixmap = QPixmap.fromImage(new_pixmap_image)
            
            # Update the pixmap
            self.feature_pixmaps[map_type] = new_pixmap
            
            # Update display if this is the current map type
            if self.current_map_type == map_type:
                self.pixmap_item.setPixmap(new_pixmap)
            
            # Clear the batch processing variables
            del self._batch_array
            del self._batch_image
            del self._batch_map_type
