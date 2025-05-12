"""
Project management functionality for the Victoria 3 Map Editor.
"""
import os
import json
from PyQt5.QtWidgets import QFileDialog, QApplication
from PyQt5.QtCore import QTimer, Qt

from ui_utils import show_warning_dialog, create_progress_dialog
from auxiliary import hex_to_rgb
from map_editor_utils import batch_apply_changes, finalize_batch_changes


class ProjectManager:
    """Class to manage project import/export functionality."""
    
    def __init__(self, parent=None):
        """
        Initialize the project manager.
        
        Args:
            parent: Parent widget
        """
        self.parent = parent
        self.imported_project = None
        self.project_map_changes = {}
    
    def import_project(self, settings_manager):
        """
        Import a previously saved project.
        
        Args:
            settings_manager: SettingsManager instance
            
        Returns:
            Dictionary with imported project data or None
        """
        # Open file dialog to select the project file
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent, "Select Project File", "exports", "Project Files (project_state.json)"
        )
        
        if not file_path:
            return None
        
        try:
            # Reset previous project data
            self.imported_project = None
            self.project_map_changes = {}
            
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
            
            # Update the settings to include ONLY the maps required by the project (and climate)
            settings_manager.set("enabled_maps", list(required_maps))
            
            # If climate not in enabled maps, add it
            enabled_maps = settings_manager.get("enabled_maps", [])
            if "climate" not in enabled_maps:
                enabled_maps.append("climate")
                settings_manager.set("enabled_maps", enabled_maps)
            
            # Set default map type to climate or first available
            if "climate" in required_maps:
                settings_manager.set("default_map_type", "climate")
            else:
                settings_manager.set("default_map_type", list(required_maps)[0])
            
            return self.imported_project
        
        except Exception as e:
            return None
    
    def count_changes_for_map_type(self, map_type):
        """
        Count how many changes in the undo stack belong to a specific map type.
        
        Args:
            map_type: Map type to count changes for
            
        Returns:
            Number of changes
        """
        if not self.imported_project or "project_data" not in self.imported_project:
            return 0
            
        undo_stack = self.imported_project["project_data"].get("undo_stack", [])
        return sum(1 for change in undo_stack if change["map_type"] == map_type)
    
    def filter_undo_stack_for_deselected_maps(self, enabled_maps):
        """
        Filter the undo stack to remove changes for deselected maps.
        
        Args:
            enabled_maps: List of enabled map types
            
        Returns:
            None
        """
        if not self.imported_project or "project_data" not in self.imported_project:
            return
            
        project_data = self.imported_project["project_data"]
        undo_stack = project_data.get("undo_stack", [])
        if not undo_stack:
            return
        
        # Filter the undo stack
        new_undo_stack = [change for change in undo_stack if change["map_type"] in enabled_maps]
        
        # Update the project data
        if len(new_undo_stack) != len(undo_stack):
            project_data["undo_stack"] = new_undo_stack
            # Also update loaded_maps to match enabled maps
            project_data["loaded_maps"] = enabled_maps


def apply_imported_changes(map_editor, changes):
    """
    Apply a series of changes from the imported undo stack efficiently.
    
    Args:
        map_editor: MapEditor instance
        changes: List of changes from imported project
    """
    if not changes:
        return
    
    # Create progress dialog
    progress, progress_message = create_progress_dialog(
        map_editor, "Importing Project", "Applying changes..."
    )
    
    progress.show()
    QApplication.processEvents()
    
    try:
        # Group changes by map type and target color to optimize processing
        change_groups = {}
        for i, change in enumerate(changes):
            map_type = change['map_type']
            location_HEX = change['location_HEX']
            new_feature = change['new_feature']
            
            # Store only the final state for each location+map_type
            key = (map_type, location_HEX)
            change_groups[key] = (i, new_feature)
            
            # Update progress message periodically
            if i % 50 == 0:
                progress_message.setText(f"Processing changes... ({i}/{len(changes)})")
                QApplication.processEvents()
        
        # Process the grouped changes by map type
        map_changes = {}
        for (map_type, location_HEX), (i, new_feature) in change_groups.items():
            if map_type not in map_changes:
                map_changes[map_type] = []
            
            # Append the change details
            map_changes[map_type].append({
                'location_HEX': location_HEX,
                'new_feature': new_feature,
                'original_index': i
            })
        
        # Process each map type
        completed = 0
        for map_type, changes_list in map_changes.items():
            # Switch to the current map type once
            map_editor.set_map_type(map_type)
            progress_message.setText(f"Applying changes for {map_type}... ({completed}/{len(changes)})")
            QApplication.processEvents()
            
            # Apply all changes for this map type
            for change_info in changes_list:
                location_HEX = change_info['location_HEX']
                new_feature = change_info['new_feature']
                
                # Get the original feature
                original_feature = map_editor.locations[location_HEX][map_type]
                
                # Update the location data
                map_editor.locations[location_HEX][map_type] = new_feature
                
                # Add to the undo stack
                map_editor.undo_stack.append({
                    'map_type': map_type,
                    'location_HEX': location_HEX,
                    'old_feature': original_feature,
                    'new_feature': new_feature
                })
                
                # Get colors for visual update
                target_color_RGB = hex_to_rgb(location_HEX)
                new_color_RGB = hex_to_rgb(map_editor.feature_data[map_type]['labels'][new_feature]['color'])
                
                # Apply the visual change using the map_editor_utils function
                batch_apply_changes(map_editor, map_type, target_color_RGB, new_color_RGB)
                
                completed += 1
                if completed % 50 == 0:
                    progress_message.setText(f"Applying changes... ({completed}/{len(changes)})")
                    QApplication.processEvents()
            
            # Final visual update for this map type using the map_editor_utils function
            finalize_batch_changes(map_editor, map_type)
        
        # Update the counter
        map_editor.update_undo_counter()
        
        # Update the display with the current map type
        map_editor.set_map_type(map_editor.current_map_type)
        
    finally:
        # Close progress dialog
        progress.accept() 