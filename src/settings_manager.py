"""
Settings management for the Victoria 3 Map Editor.
"""
import os
import json


class SettingsManager:
    """Class to manage application settings."""
    
    def __init__(self, settings_file="editor_settings.json"):
        """
        Initialize the settings manager.
        
        Args:
            settings_file: Path to the settings file
        """
        self.settings_file = settings_file
        self.settings = self.load_settings()
    
    def load_settings(self):
        """
        Load settings from the settings file.
        
        Returns:
            Dictionary of settings
        """
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
        return self.get_default_settings()
    
    def get_default_settings(self):
        """
        Get default settings.
        
        Returns:
            Dictionary of default settings
        """
        return {
            "default_map_type": "climate",
            "enabled_maps": ["climate"],
            "game_directory": "",
            "locations_file": "",
            "state_regions_path": "",
            "icon_directory": os.path.join("res", "icons", "feather")
        }
    
    def save_settings(self):
        """
        Save settings to the settings file.
        """
        # Ensure climate is always enabled
        if "enabled_maps" in self.settings and "climate" not in self.settings["enabled_maps"]:
            self.settings["enabled_maps"].append("climate")
            
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)
    
    def get(self, key, default=None):
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if the key doesn't exist
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = value
        self.save_settings()
    
    def validate_paths(self):
        """
        Validate that required paths exist.
        
        Returns:
            Tuple of (is_valid, list of missing paths)
        """
        missing_paths = []
        
        locations_file = self.get("locations_file", "")
        if not locations_file or not os.path.exists(locations_file):
            missing_paths.append("Provinces map file")
        
        state_regions_path = self.get("state_regions_path", "")
        if not state_regions_path or not os.path.exists(state_regions_path):
            missing_paths.append("State regions directory")
        
        return (len(missing_paths) == 0, missing_paths)
    
    def validate_game_directory(self):
        """
        Validate the game directory structure.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        dir_path = self.get("game_directory", "")
        
        if not dir_path or not os.path.isdir(dir_path):
            return False, "Please select a valid directory"
        
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
            return False, "\n".join(errors)
        
        # Store the locations file and state regions paths
        self.set("locations_file", provinces_path)
        self.set("state_regions_path", state_regions_path)
        
        return True, "" 