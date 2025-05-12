"""
Utility functions specifically for the map editor.
"""
import os
import time
import numpy as np
from datetime import datetime
import json
from PyQt5.QtGui import QColor, QPixmap, QImage
from PyQt5.QtWidgets import QApplication

from auxiliary import hex_to_rgb


def create_pixmap_from_array(arr, width, height):
    """
    Create a QPixmap from a numpy array.
    
    Args:
        arr: Numpy array with image data
        width: Image width
        height: Image height
        
    Returns:
        QPixmap created from the array
    """
    bytes_per_line = 3 * width
    # Ensure the array is contiguous and convert to bytes
    modified_image = QImage(arr.tobytes(),
                            width, height,
                            bytes_per_line,
                            QImage.Format_RGB888)
    # Create pixmap from the modified image
    modified_pixmap = QPixmap.fromImage(modified_image)
    if modified_pixmap.isNull():
        raise ValueError("Failed to create pixmap from image")
    
    return modified_pixmap


def apply_feature_change(original_array, feature_array, target_color_RGB, new_color_RGB):
    """
    Apply a feature change to the feature array.
    
    Args:
        original_array: Original map array
        feature_array: Feature map array to modify
        target_color_RGB: RGB color to replace
        new_color_RGB: New RGB color
        
    Returns:
        Modified feature array
    """
    # Make a copy to avoid modifying the original
    arr_new_image = np.copy(feature_array)
    
    # Create mask of pixels matching target color
    mask = ((original_array[:,:,0] == target_color_RGB[0]) &
            (original_array[:,:,1] == target_color_RGB[1]) &
            (original_array[:,:,2] == target_color_RGB[2]))
    
    # Create color array for faster assignment
    color_array = np.array([new_color_RGB[2], new_color_RGB[1], new_color_RGB[0], 255], dtype=np.uint8)
    
    # Update pixel colors in the feature array
    arr_new_image[mask] = color_array
    
    return arr_new_image


def export_map_data(locations, undo_stack, current_map_type, feature_pixmaps):
    """
    Export modified locations and project state to a timestamped folder.
    
    Args:
        locations: Dictionary of location data
        undo_stack: Undo stack with changes
        current_map_type: Current active map type
        feature_pixmaps: Dictionary of feature pixmaps
        
    Returns:
        Export directory path
    """
    # Create exports directory if it doesn't exist
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_dir = os.path.join('exports', timestamp)
    os.makedirs(export_dir, exist_ok=True)

    # Get all columns except name, x, y
    excluded_columns = {'name', 'x', 'y'}
    columns_to_export = set()
    
    # Find all unique columns across all locations
    for location_data in locations.values():
        columns_to_export.update(key for key in location_data.keys() if key not in excluded_columns)

    # Export each column to a separate file
    for column in columns_to_export:
        export_path = os.path.join(export_dir, f'{column}.csv')
        with open(export_path, 'w', encoding='utf-8') as f:
            for hex_code, location_data in locations.items():
                if column in location_data:
                    f.write(f"{hex_code},{location_data[column]}\n")
    
    # Save the undo stack and current map type to a file
    project_data = {
        'undo_stack': undo_stack,
        'current_map_type': current_map_type,
        'loaded_maps': list(feature_pixmaps.keys())
    }
    
    project_file = os.path.join(export_dir, 'project_state.json')
    with open(project_file, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=2)
    
    return export_dir


def batch_apply_changes(map_editor, map_type, target_color_RGB, new_color_RGB):
    """
    Optimized function to apply changes to a map for batch processing.
    
    Args:
        map_editor: MapEditor instance
        map_type: Map type to modify
        target_color_RGB: Target RGB color
        new_color_RGB: New RGB color
    """
    # Get the image from pixmap (only once per batch)
    if not hasattr(map_editor, '_batch_image') or map_editor._batch_map_type != map_type:
        map_editor._batch_map_type = map_type
        map_editor._batch_image = map_editor.feature_pixmaps[map_type].toImage()
        width, height = map_editor._batch_image.width(), map_editor._batch_image.height()
        ptr = map_editor._batch_image.bits()
        ptr.setsize(height * width * 4)  # 4 bytes per pixel (RGBA)
        map_editor._batch_array = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    
    # Find matching region in original array
    mask = ((map_editor.original_array[:,:,0] == target_color_RGB[0]) & 
            (map_editor.original_array[:,:,1] == target_color_RGB[1]) & 
            (map_editor.original_array[:,:,2] == target_color_RGB[2]))
    
    # Create color array for assignment
    color_array = np.array([new_color_RGB[2], new_color_RGB[1], new_color_RGB[0], 255], dtype=np.uint8)
    
    # Update the array
    map_editor._batch_array[mask] = color_array


def finalize_batch_changes(map_editor, map_type):
    """
    Finalize batch changes by converting the processed array back to a pixmap.
    
    Args:
        map_editor: MapEditor instance
        map_type: Map type that was modified
    """
    if hasattr(map_editor, '_batch_array') and map_editor._batch_map_type == map_type:
        width, height = map_editor._batch_image.width(), map_editor._batch_image.height()
        new_pixmap_image = QImage(map_editor._batch_array.data, width, height, QImage.Format_ARGB32)
        new_pixmap = QPixmap.fromImage(new_pixmap_image)
        
        # Update the pixmap
        map_editor.feature_pixmaps[map_type] = new_pixmap
        
        # Update display if this is the current map type
        if map_editor.current_map_type == map_type:
            map_editor.pixmap_item.setPixmap(new_pixmap)
        
        # Clear the batch processing variables
        del map_editor._batch_array
        del map_editor._batch_image
        del map_editor._batch_map_type 