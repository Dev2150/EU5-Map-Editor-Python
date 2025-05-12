from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QCheckBox, QGroupBox, QLabel, QFileDialog, QHBoxLayout
from PyQt5.QtWidgets import QProgressDialog, QApplication, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import json
import os
import pickle

class StartupWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Editor Settings")
        self.setMinimumWidth(400)
        self.settings_file = "editor_settings.json"
        self.settings = self.load_settings()
        self.feature_data = self.load_feature_data()
        self.imported_project = None
        self.project_map_changes = {}  # Stores changes per map type in imported project
        
        # Set window icon - use absolute path for Windows
        icon_path = os.path.abspath(os.path.join("res", "icons", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
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
                    
                    # Add special handling for climate checkbox
                    if map_type == "climate":
                        checkbox.setToolTip("Climate map is required and cannot be deselected")
                        # Use a slightly different style to indicate it's always selected
                        checkbox.setStyleSheet("font-weight: bold;")
                    
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
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Open project button
        open_project_button = QPushButton("Open Existing Project")
        open_project_button.clicked.connect(self.import_project)
        buttons_layout.addWidget(open_project_button)
        
        # Start button
        start_button = QPushButton("Start Map Editor")
        start_button.clicked.connect(self.validate_and_accept)
        buttons_layout.addWidget(start_button)
        
        layout.addLayout(buttons_layout)
        
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
        # If a project was imported, we can skip validation
        if self.imported_project:
            # Check if any required map is unchecked
            for map_type in self.imported_project["project_data"].get("loaded_maps", []):
                if map_type in self.checkboxes and not self.checkboxes[map_type].isChecked():
                    # Filter the undo stack to remove changes for deselected maps
                    self.filter_undo_stack_for_deselected_maps()
                    break
            
            self.accept()
            return
            
        # Validate game directory
        if not self.validate_game_directory():
            return
            
        # Ensure climate map is always selected
        enabled_maps = self.settings.get("enabled_maps", [])
        if "climate" not in enabled_maps:
            enabled_maps.append("climate")
            self.settings["enabled_maps"] = enabled_maps
            
        # Ensure at least one map is selected
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
    
    def filter_undo_stack_for_deselected_maps(self):
        """Filter the undo stack to remove changes for deselected maps"""
        if not self.imported_project or "project_data" not in self.imported_project:
            return
            
        project_data = self.imported_project["project_data"]
        undo_stack = project_data.get("undo_stack", [])
        if not undo_stack:
            return
            
        # Get currently enabled maps
        enabled_maps = []
        for map_type, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                enabled_maps.append(map_type)
        
        # Filter the undo stack
        new_undo_stack = [change for change in undo_stack if change["map_type"] in enabled_maps]
        
        # Update the project data
        if len(new_undo_stack) != len(undo_stack):
            project_data["undo_stack"] = new_undo_stack
            # Also update loaded_maps to match enabled maps
            project_data["loaded_maps"] = enabled_maps
        
    def on_checkbox_toggled(self, map_type, checked):
        enabled_maps = self.settings.get("enabled_maps", [])
        
        # Prevent climate from being unchecked
        if map_type == "climate" and not checked:
            # Block signals to prevent infinite recursion
            if map_type in self.checkboxes:
                self.checkboxes[map_type].blockSignals(True)
                self.checkboxes[map_type].setChecked(True)
                self.checkboxes[map_type].blockSignals(False)
            return
        
        # Handle deselecting a map that is in the imported project
        if not checked and self.imported_project and map_type in self.checkboxes:
            imported_maps = self.imported_project["project_data"].get("loaded_maps", [])
            if map_type in imported_maps:
                # Count changes that would be lost
                changes_to_remove = self.count_changes_for_map_type(map_type)
                
                if changes_to_remove > 0:
                    # Show warning
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("Warning: Changes Will Be Lost")
                    msg.setText(f"Deselecting this map will remove {changes_to_remove} changes from the imported project.")
                    msg.setInformativeText("Do you want to continue?")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg.setDefaultButton(QMessageBox.No)
                    
                    if msg.exec_() == QMessageBox.No:
                        # User canceled, recheck the checkbox
                        self.checkboxes[map_type].blockSignals(True)
                        self.checkboxes[map_type].setChecked(True)
                        self.checkboxes[map_type].blockSignals(False)
                        return
        
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
    
    def count_changes_for_map_type(self, map_type):
        """Count how many changes in the undo stack belong to a specific map type"""
        if not self.imported_project or "project_data" not in self.imported_project:
            return 0
            
        undo_stack = self.imported_project["project_data"].get("undo_stack", [])
        return sum(1 for change in undo_stack if change["map_type"] == map_type)
    
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
    
    def import_project(self):
        """Import a previously saved project and set it for the MapEditor"""
        # Open file dialog to select the project file
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Project File", "exports", "Project Files (project_state.json)"
        )
        
        if not file_path:
            return
        
        try:
            # Load the project data
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # Extract the project directory (parent of the file)
            project_dir = os.path.dirname(file_path)
            
            # Count changes per map type
            changes_by_map = {}
            undo_stack = project_data.get("undo_stack", [])
            for change in undo_stack:
                map_type = change["map_type"]
                if map_type not in changes_by_map:
                    changes_by_map[map_type] = 0
                changes_by_map[map_type] += 1
            
            # Store the changes by map type
            self.project_map_changes = changes_by_map
            
            # Store the loaded project
            self.imported_project = {
                'project_data': project_data,
                'project_dir': project_dir
            }
            
            # Ensure required maps are enabled in settings
            required_maps = set(project_data.get('loaded_maps', ['climate']))
            enabled_maps = set(self.settings.get("enabled_maps", ["climate"]))
            
            # Update enabled maps to include all required by the project
            self.settings["enabled_maps"] = list(enabled_maps.union(required_maps))
            
            # If climate not in enabled maps, add it
            if "climate" not in self.settings["enabled_maps"]:
                self.settings["enabled_maps"].append("climate")
            
            # Reset all checkbox styles first
            for map_type, checkbox in self.checkboxes.items():
                if map_type == 'climate':
                    checkbox.setStyleSheet("font-weight: bold;")  # Keep climate always bold
                else:
                    checkbox.setStyleSheet("")
            
            # Update checkboxes to reflect required maps and highlight them
            for map_type in required_maps:
                if map_type in self.checkboxes:
                    self.checkboxes[map_type].setChecked(True)
                    
                    # Special style for maps included in the project
                    if map_type != 'climate':  # Climate already has its own style
                        change_count = changes_by_map.get(map_type, 0)
                        
                        # Style with changes count
                        self.checkboxes[map_type].setStyleSheet(
                            "background-color: #e6f7ff; color: #0066cc; font-weight: bold; border: 1px solid #99ccff; padding: 2px;"
                        )
                        
                        # Set tooltip to indicate this map is required by the project
                        changes_text = f"{change_count} change" if change_count == 1 else f"{change_count} changes"
                        self.checkboxes[map_type].setToolTip(
                            f"This map is required by the loaded project ({changes_text})"
                        )
            
            # Save settings
            self.save_settings()
            
            # Show success message
            project_name = os.path.basename(project_dir)
            map_count = len(required_maps)
            change_count = len(undo_stack)
            map_text = "map" if map_count == 1 else "maps"
            change_text = "change" if change_count == 1 else "changes"
            self.dir_validation_label.setText(
                f"Project '{project_name}' loaded with {map_count} {map_text} and {change_count} {change_text}."
            )
            self.dir_validation_label.setStyleSheet("color: green; font-weight: bold;")
            
        except Exception as e:
            # Show error message
            self.dir_validation_label.setText(f"Error importing project: {str(e)}")
            self.dir_validation_label.setStyleSheet("color: red;")

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
        # Ensure climate is always enabled
        if "enabled_maps" in self.settings and "climate" not in self.settings["enabled_maps"]:
            self.settings["enabled_maps"].append("climate")
            
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)
            
    def get_settings(self):
        return self.settings
        
    def get_imported_project(self):
        return self.imported_project 