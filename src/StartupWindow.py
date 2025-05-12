from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QCheckBox, QGroupBox, QLabel, QFileDialog, QHBoxLayout
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
        
        # File selector for game directory
        file_group = QGroupBox("Victoria 3 Game Directory")
        file_layout = QVBoxLayout()
        
        # # Add information label
        # info_label = QLabel("Select the root folder containing the game directory with this structure:\n"
        #                    "folder/game/map_data/provinces.png\n"
        #                    "folder/game/map_data/state_regions/")
        # info_label.setWordWrap(True)
        # file_layout.addWidget(info_label)
        
        file_layout_row = QHBoxLayout()
        self.dir_path_label = QLabel(self.settings.get("game_directory", "Not selected"))
        file_layout_row.addWidget(self.dir_path_label)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.select_game_directory)
        file_layout_row.addWidget(browse_button)
        
        file_layout.addLayout(file_layout_row)
        
        # Add directory validation warning label
        self.dir_validation_label = QLabel("")
        self.dir_validation_label.setStyleSheet("color: red;")
        file_layout.addWidget(self.dir_validation_label)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
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
        self.default_map_checkboxes = {}
        for map_type, checkbox in self.checkboxes.items():
            if map_type in self.feature_data:
                display_name = self.feature_data[map_type]["display_name"]
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        # Start button
        start_button = QPushButton("Start Map Editor")
        start_button.clicked.connect(self.validate_and_accept)
        layout.addWidget(start_button)
        
        self.setLayout(layout)
        
        # Validate the directory on startup
        self.validate_game_directory()
    
    def select_game_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Victoria 3 Game Directory", 
            self.settings.get("game_directory", "")
        )
        
        if dir_path:
            self.settings["game_directory"] = dir_path
            self.dir_path_label.setText(dir_path)
            self.save_settings()
            self.validate_game_directory()
    
    def validate_game_directory(self):
        """Validate that the directory has the required structure."""
        dir_path = self.settings.get("game_directory", "")
        
        if not dir_path or not os.path.isdir(dir_path):
            self.dir_validation_label.setText("Please select a valid directory")
            return False
        
        # Check for required structure
        provinces_path = os.path.join(dir_path, "game", "map_data", "provinces.png")
        state_regions_path = os.path.join(dir_path, "game", "map_data", "state_regions")
        
        errors = []
        if not os.path.isfile(provinces_path):
            errors.append("Missing provinces.png file")
        
        if not os.path.isdir(state_regions_path):
            errors.append("Missing state_regions directory")
        elif not any(os.path.isfile(os.path.join(state_regions_path, f)) for f in os.listdir(state_regions_path)):
            errors.append("state_regions directory is empty")
            
        if errors:
            self.dir_validation_label.setText("\n".join(errors))
            return False
        else:
            # Store the locations file and state regions paths for later use
            self.settings["locations_file"] = provinces_path
            self.settings["state_regions_path"] = state_regions_path
            self.dir_validation_label.setText("")
            return True
    
    def validate_and_accept(self):
        # Validate game directory
        if not self.validate_game_directory():
            return
            
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
        
        # Try to load from template if the main settings file doesn't exist
        template_file = f"{self.settings_file}.template"
        if os.path.exists(template_file):
            try:
                with open(template_file, 'r') as f:
                    settings = json.load(f)
                    # Save the template as the main settings file
                    with open(self.settings_file, 'w') as out_f:
                        json.dump(settings, out_f, indent=4)
                    return settings
            except:
                pass
        
        # Default settings if neither file exists or can be loaded
        return {
            "default_map_type": "climate",
            "enabled_maps": ["climate"],
            "game_directory": "",
            "locations_file": "",
            "state_regions_path": ""
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