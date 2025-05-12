from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QCheckBox, QGroupBox, QLabel
from PyQt5.QtCore import Qt
import json
import os

class StartupWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Editor Settings")
        self.setMinimumWidth(400)
        self.settings_file = "editor_settings.json"
        self.settings = self.load_settings()
        self.feature_data = self.load_feature_data()
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Select Maps to Load")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Create checkboxes for each map type
        group = QGroupBox("Available Maps")
        group_layout = QVBoxLayout()
        
        # Group map types by category
        categories = {
            "Climate": ["climate"],
            "Terrain": ["topography"],
            "Vegetation": ["vegetation"],
            "Crop Suitability": ["low_wheat", "low_tubers"]
        }
        
        self.checkboxes = {}
        
        for category, map_types in categories.items():
            category_label = QLabel(category)
            category_label.setStyleSheet("font-weight: bold;")
            group_layout.addWidget(category_label)
            
            for map_type in map_types:
                if map_type in self.feature_data:
                    display_name = self.feature_data[map_type]["display_name"]
                    checkbox = QCheckBox(display_name)
                    self.checkboxes[map_type] = checkbox
                    
                    # Set checked state based on saved settings
                    enabled_maps = self.settings.get("enabled_maps", ["climate"])
                    checkbox.setChecked(map_type in enabled_maps)
                    
                    checkbox.toggled.connect(lambda checked, mt=map_type: self.on_checkbox_toggled(mt, checked))
                    group_layout.addWidget(checkbox)
            
            # Add a small space between categories
            spacer = QLabel("")
            spacer.setFixedHeight(10)
            group_layout.addWidget(spacer)
        
        # Default map selection
        # default_label = QLabel("Default Map (first map to show):")
        # default_label.setStyleSheet("font-weight: bold;")
        # group_layout.addWidget(default_label)
        
        self.default_map_checkboxes = {}
        for map_type, checkbox in self.checkboxes.items():
            if map_type in self.feature_data:
                display_name = self.feature_data[map_type]["display_name"]
                # radio = QCheckBox(f"Start with {display_name}")
                # self.default_map_checkboxes[map_type] = radio
                
                # Set checked state based on saved settings
                # default_map = self.settings.get("default_map_type", "climate")
                # radio.setChecked(map_type == default_map)
                
                # radio.toggled.connect(lambda checked, mt=map_type: self.on_default_toggled(mt, checked))
                # group_layout.addWidget(radio)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        # Start button
        start_button = QPushButton("Start Map Editor")
        start_button.clicked.connect(self.validate_and_accept)
        layout.addWidget(start_button)
        
        self.setLayout(layout)
    
    def validate_and_accept(self):
        # Ensure at least one map is selected
        enabled_maps = self.settings.get("enabled_maps", [])
        if not enabled_maps:
            # Auto-select climate if nothing is selected
            self.settings["enabled_maps"] = ["climate"]
            self.settings["default_map_type"] = "climate"
            if "climate" in self.checkboxes:
                self.checkboxes["climate"].setChecked(True)
            if "climate" in self.default_map_checkboxes:
                self.default_map_checkboxes["climate"].setChecked(True)
        
        # Ensure default map is among enabled maps
        default_map = self.settings.get("default_map_type", "climate")
        if default_map not in enabled_maps and enabled_maps:
            self.settings["default_map_type"] = enabled_maps[0]
        
        self.save_settings()
        self.accept()
        
    def on_checkbox_toggled(self, map_type, checked):
        enabled_maps = self.settings.get("enabled_maps", [])
        
        if checked and map_type not in enabled_maps:
            enabled_maps.append(map_type)
        elif not checked and map_type in enabled_maps:
            enabled_maps.remove(map_type)
            
            # If we unchecked the default map, update default as well
            if self.settings.get("default_map_type") == map_type:
                if enabled_maps:
                    self.settings["default_map_type"] = enabled_maps[0]
                    self.default_map_checkboxes[enabled_maps[0]].setChecked(True)
                else:
                    self.settings["default_map_type"] = ""
        
        self.settings["enabled_maps"] = enabled_maps
        self.save_settings()
    
    def on_default_toggled(self, map_type, checked):
        if checked:
            # Uncheck all other default options
            for mt, checkbox in self.default_map_checkboxes.items():
                if mt != map_type and checkbox.isChecked():
                    checkbox.blockSignals(True)
                    checkbox.setChecked(False)
                    checkbox.blockSignals(False)
            
            # Set this as default
            self.settings["default_map_type"] = map_type
            
            # Make sure the map is enabled
            if map_type not in self.settings.get("enabled_maps", []):
                self.settings.setdefault("enabled_maps", []).append(map_type)
                if map_type in self.checkboxes:
                    self.checkboxes[map_type].setChecked(True)
            
            self.save_settings()
            
    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "default_map_type": "climate",
            "enabled_maps": ["climate"]
        }
        
    def load_feature_data(self):
        try:
            with open('res/mappings/feature_data.json', 'r') as f:
                return json.load(f)
        except:
            # Fallback if file isn't available
            return {
                "climate": {"display_name": "Climate"},
                "topography": {"display_name": "Topography"},
                "vegetation": {"display_name": "Vegetation"},
                "low_wheat": {"display_name": "Wheat (Low)"},
                "low_tubers": {"display_name": "Tubers (Low)"}
            }
        
    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)
            
    def get_settings(self):
        return self.settings 