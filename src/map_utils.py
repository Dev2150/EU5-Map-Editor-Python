import numpy as np
from PyQt5.QtGui import QPixmap, QImage

from auxiliary import hex_to_rgb, rgb_to_hex


def construct_map_from_mapping(dict_locations: dict, arr_original: np.ndarray, feature_data: dict, isNumerical=False,
                               needsConversionToRGB=False, feature_type=None):
    """
    Creates a new map pixmap based on feature mapping
    
    Args:
        dict_locations: Dictionary of location data including feature values
        arr_original: Original map array
        feature_data: Feature type data including colors
        isNumerical: Whether the feature uses numerical values
        needsConversionToRGB: Whether colors need to be converted to RGB
        feature_type: The type of feature being mapped (climate, topography, etc.)
        
    Returns:
        QPixmap of the constructed map
    """
    modifiedArray: np.ndarray = np.copy(arr_original)
    
    # Create a new dictionary with only the specific feature
    if feature_type:
        mapping = {hex_code: location_data[feature_type]
                   for hex_code, location_data in dict_locations.items()
                   if feature_type in location_data}
    else:
        # No locations to map, return a blank map
        print("Warning: No feature type provided for mapping")
        return QPixmap(arr_original.shape[1], arr_original.shape[0])

    # Create original to new color mapping
    original_to_new = {}

    if feature_data:
        for orig_hex, label in mapping.items():
            if label not in feature_data:
                print(f"Warning: Label '{label}' not found in feature data for {feature_type}")
                continue
                
            color_original: tuple = hex_to_rgb(orig_hex)
            color_new: tuple = feature_data[label]['color']
            if needsConversionToRGB:
                color_new = hex_to_rgb(color_new)
            original_to_new[color_original] = color_new
    else:
        for orig_hex, label in mapping.items():
            try:
                label = int(label)
                color_original: tuple = hex_to_rgb(orig_hex)
                color_new: tuple = (label, label, label)
                original_to_new[color_original] = color_new
            except (ValueError, TypeError) as e:
                print(f"Warning: Could not convert label '{label}' to integer: {e}")
                continue

    if not original_to_new:
        print(f"Warning: No valid color mappings found for {feature_type}")
        return QPixmap(arr_original.shape[1], arr_original.shape[0])

    # Convert colors to numpy arrays for vectorized operations
    orig_colors: np.ndarray = np.array(list(original_to_new.keys()), dtype=np.uint8)
    new_colors: np.ndarray = np.array(list(original_to_new.values()), dtype=np.uint8)
    # Create a lookup table for all possible RGB values
    lookup = np.zeros((256, 256, 256, 3), dtype=np.uint8)
    for orig, new in zip(orig_colors, new_colors):
        lookup[int(orig[0]), int(orig[1]), int(orig[2])] = new
    # Apply the lookup table to the original array
    h, w = modifiedArray.shape[:2]
    result: np.ndarray = lookup[modifiedArray[:, :, 0],
    modifiedArray[:, :, 1],
    modifiedArray[:, :, 2]]
    # Update the original array with the transformed colors
    modifiedArray[:] = result
    # Convert the processed numpy array back to QImage
    height, width = modifiedArray.shape[:2]
    bytes_per_line = 3 * width
    # Ensure the array is contiguous and convert to bytes
    modified_image: QImage = QImage(modifiedArray.tobytes(),
                                    width, height,
                                    bytes_per_line,
                                    QImage.Format_RGB888)
    # Create pixmap from the modified image
    modified_pixmap = QPixmap.fromImage(modified_image)
    if modified_pixmap.isNull():
        raise ValueError("Failed to create pixmap from image")

    return modified_pixmap


def generate_numerical_feature_labels(labels_suitability):
    """Generate labels for numerical features based on suitability categories
    
    Args:
        labels_suitability: List of suitability labels
        
    Returns:
        Dictionary with numerical feature labels
    """
    labels = {}
    labels_suitability_len = len(labels_suitability)
    
    for i in range(256):
        desc_long = labels_suitability[min(labels_suitability_len - 1, int(i / (256 / labels_suitability_len)))]
        labels[str(i)] = {
            'color': rgb_to_hex(*(i, i, i)), 
            'desc_short': i,
            'desc_long': desc_long
        }
        
    return labels 