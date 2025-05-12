import sys
import time
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
import numpy as np

from constants import (
    PATH_RES, FILE_TXT_TERRAINS, PATH_LOCATION_MAPPINGS, 
    PATH_FEATURE_DETAILS, FILE_FEATURE_DATA, LABELS_SUITABILITY
)
from file_parsers import (
    parse_states, load_province_V3_terrain_types, 
    load_location_mappings, load_province_features, load_feature_data
)
from map_utils import construct_map_from_mapping, generate_numerical_feature_labels
from project_manager import apply_imported_changes
from settings_manager import SettingsManager
from ui_utils import show_error_dialog
from auxiliary import get_array_from_image, resetTimer, convert_key_string_to_qt
from MapEditor import MapEditor
from StartupWindow import StartupWindow


def convert_hotkey_strings_to_qt(feature_data):
    """Convert string hotkey representations to Qt key codes."""
    for _, feature in feature_data.items():
        feature['hotkey'] = [convert_key_string_to_qt(hotkey) for hotkey in feature['hotkey']]


def main():
    """Main entry point of the application."""
    app = QApplication(sys.argv)
    
    # Set application icon - use absolute path for Windows
    icon_path = os.path.abspath(os.path.join("res", "icons", "icon.png"))
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
        
        # For Windows, we need to set the app ID to show the custom icon in taskbar
        if sys.platform == 'win32':
            import ctypes
            myappid = 'eu5.mapeditor.v1.0'  # Arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    try:
        # Initialize settings manager
        settings_manager = SettingsManager()
        
        # Show startup window first
        startup_window = StartupWindow()
        if startup_window.exec_() != StartupWindow.Accepted:
            sys.exit(0)  # Exit if user cancels
    
        # Get settings from startup window
        settings = startup_window.get_settings()
        default_map_type = settings.get("default_map_type", "climate")
        enabled_maps = settings.get("enabled_maps", ["climate"])
        locations_file = settings.get("locations_file", "")
        state_regions_path = settings.get("state_regions_path", "")
        
        # Check if a project was imported
        imported_project = startup_window.get_imported_project()
        
        # If no project was imported, validate paths
        if not imported_project:
            # Validate the required paths exist before proceeding
            is_valid, missing_paths = settings_manager.validate_paths()
            if not is_valid:
                show_error_dialog(
                    None, 
                    "Error", 
                    f"The following required paths were not found:\n- {'\n- '.join(missing_paths)}\n\nPlease restart and select a valid game directory."
                )
                sys.exit(1)
    
        start_time = time.time()
    
        # Pre-load all required data
        time_task = resetTimer('Starting state parsing...')
        dict_locations = parse_states(state_regions_path)
        print(f"State parsing completed in {time.time() - time_task:.2f} seconds")
    
        time_task = resetTimer('Loading V3 province terrains...')
        location_to_v3TerrainType = load_province_V3_terrain_types(FILE_TXT_TERRAINS)
        print(f"V3 province terrains loaded in {time.time() - time_task:.2f} seconds")
    
        # Load feature data from JSON
        feature_data = load_feature_data(FILE_FEATURE_DATA)
    
        time_task = resetTimer('Loading feature details and data...')
        for feature_type, config in feature_data.items():
            # Only load feature mappings for enabled maps
            if feature_type in enabled_maps:
                isNumerical = config['isNumerical']
                filePath = config['file_details'] if 'file_details' in config else f'{PATH_LOCATION_MAPPINGS}{feature_type}.csv'
                load_location_mappings(filePath, feature_type, dict_locations)
    
                if not isNumerical:
                    filePath = config['file_data'] if 'file_data' in config else f'{PATH_FEATURE_DETAILS}{feature_type}.csv'
                    feature_data[feature_type]['labels'] = load_province_features(filePath)
                else:
                    feature_data[feature_type]['labels'] = generate_numerical_feature_labels(LABELS_SUITABILITY)
            else:
                # For disabled maps, initialize empty labels to avoid errors
                feature_data[feature_type]['labels'] = {}
                print(f"Skipping feature data loading for {feature_type} (not enabled)")
    
        print(f"Feature details and data loaded in {time.time() - time_task:.2f} seconds")
    
        time_task = resetTimer('Getting array from locations image...')
        arr_original = get_array_from_image(locations_file)
    
        # Create feature maps
        feature_pixmaps = {}
        for feature_type, config in feature_data.items():
            # Only load enabled maps
            if feature_type in enabled_maps:
                time_task = resetTimer(f'Creating {feature_type} map...')
                
                # Create feature labels map
                feature_labels = None
                if not config['isNumerical']:
                    feature_labels = feature_data[feature_type]['labels']
                
                # Construct the map with explicit feature_type parameter
                feature_pixmaps[feature_type] = construct_map_from_mapping(
                    dict_locations,
                    arr_original,
                    feature_labels,
                    config['isNumerical'],
                    config['needs_rgb_conversion'],
                    feature_type  # Pass the feature_type explicitly
                )
                print(f"{feature_type} map created in {time.time() - time_task:.2f} seconds")
            else:
                print(f"Skipping {feature_type} map (not enabled)")
    
        print(f"Arrays from images retrieved in {time.time() - time_task:.2f} seconds")
    
        convert_hotkey_strings_to_qt(feature_data)
    
        # Initialize MapEditor with consolidated data
        map_editor = MapEditor(
            arr_original,
            feature_pixmaps,
            dict_locations,
            location_to_v3TerrainType,
            feature_data
        )
        map_editor.resize(1200, 800)
        
        # Apply imported project changes if a project was imported
        if imported_project:
            project_data = imported_project['project_data']
            
            # Set the initial map type from the project
            initial_map_type = project_data.get('current_map_type', 'climate')
            if initial_map_type and initial_map_type in feature_pixmaps:
                map_editor.set_map_type(initial_map_type)
                
            # Apply all changes from the project
            changes = project_data.get('undo_stack', [])
            if changes:
                try:
                    apply_imported_changes(map_editor, changes)
                    print(f"Applied {len(changes)} changes from imported project")
                    
                    # Set last_export_stack_size to match current undo stack size
                    # This prevents the "unsaved changes" prompt when quitting without making new changes
                    map_editor.last_export_stack_size = len(map_editor.undo_stack)
                except Exception as e:
                    show_error_dialog(
                        map_editor,
                        "Error Applying Changes",
                        f"Failed to apply some project changes: {str(e)}",
                        details=f"Error details: {repr(e)}"
                    )
        
        # Set the default map type if one was selected and no project was imported
        elif default_map_type and default_map_type in feature_data and default_map_type in feature_pixmaps:
            map_editor.set_map_type(default_map_type)
        elif feature_pixmaps:  # If default map not available, use the first available map
            map_editor.set_map_type(list(feature_pixmaps.keys())[0])
            
        map_editor.show()
        print(f"Map editor ready! It took a total of {time.time() - start_time:.2f} seconds")
        sys.exit(app.exec_())
        
    except Exception as e:
        show_error_dialog(
            None,
            "Unexpected Error",
            f"An unexpected error occurred: {str(e)}",
            details=f"Error details: {repr(e)}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
