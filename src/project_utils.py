from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication
from PyQt5.QtCore import Qt
from auxiliary import hex_to_rgb


def apply_imported_changes(map_editor, changes):
    """Apply a series of changes from the imported undo stack efficiently
    
    Args:
        map_editor: MapEditor instance to apply changes to
        changes: List of change dictionaries from imported project
    """
    if not changes:
        return
    
    # Create progress dialog
    progress = QDialog(map_editor)
    progress.setWindowTitle("Importing Project")
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumWidth(400)
    
    progress_layout = QVBoxLayout()
    progress_message = QLabel("Applying changes...")
    progress_layout.addWidget(progress_message)
    progress.setLayout(progress_layout)
    
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
                
                # Apply the visual change but without the expensive map_type switching
                map_editor._batch_apply_feature_change(map_type, target_color_RGB, new_color_RGB)
                
                completed += 1
                if completed % 50 == 0:
                    progress_message.setText(f"Applying changes... ({completed}/{len(changes)})")
                    QApplication.processEvents()
            
            # Final visual update for this map type
            map_editor._finalize_feature_changes(map_type)
        
        # Update the counter
        map_editor.update_undo_counter()
        
        # Update the display with the current map type
        map_editor.set_map_type(map_editor.current_map_type)
        
    finally:
        # Close progress dialog
        progress.accept() 