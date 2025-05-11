import re
import sys
import time
from ast import literal_eval
from os import listdir, path

import numpy as np
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QApplication
from numpy import ndarray

from MapEditor import MapEditor
from src.auxiliary import hex_to_rgb, resetTimer, get_array_from_image, rgb_to_hex, convert_key_string_to_qt

PATH_RES = 'res/'
FILE_IMAGE_LOCATIONS_INPUT = PATH_RES + 'provinces.png'

FILE_TXT_TERRAINS = f'{PATH_RES}mappings/province_terrains.txt'
PATH_LOCATION_MAPPINGS = f'{PATH_RES}mappings/location_'
PATH_FEATURE_DETAILS = f'{PATH_RES}feature_details/feature_details_'

# Define map feature types
feature_data = {
    'climate': {
        'display_name': 'Climate',
        'key': 'climate',
        'hotkey': ['Q', 'F1'],
        'needs_rgb_conversion': True,
        'isGradient': False,
        'bottom_layout_stretch': 4,
    },
    'topography': {
        'display_name': 'Topography',
        'key': 'topography',
        'hotkey': ['W', 'F2'],
        'needs_rgb_conversion': True,
        'isGradient': False,
        'bottom_layout_stretch': 1,
    },
    'vegetation': {
        'display_name': 'Vegetation',
        'key': 'vegetation',
        'hotkey': ['E', 'F3'],
        'needs_rgb_conversion': True,
        'isGradient': False,
        'bottom_layout_stretch': 1,
    },
    'low_wheat': {
        'display_name': 'Wheat (Low)',
        'hotkey': ['R', 'F5'],
        'needs_rgb_conversion': True,
        'isGradient': True,
        'bottom_layout_stretch': 1,
    },
    'low_tubers': {
        'display_name': 'Tubers (Low)',
        'hotkey': ['T', 'F6'],
        'needs_rgb_conversion': True,
        'isGradient': True,
        'bottom_layout_stretch': 1,
    }
}

labels_suitability = ['Unsuitable', 'Suboptimal', 'Favourable', 'Excellent', 'Exceptional']


def parse_states(file_path: str) -> dict:
    """
    Parses a file containing state definitions and creates a province-to-state dictionary.
    Args:
        file_path: The path to the file containing the state definitions.
    Returns:
        A dictionary where keys are province IDs and values are state names.
    """

    provinces_init: dict = {}
    # Compile regex patterns once
    state_pattern = re.compile(r'([A-Z_]+)\s*=\s*\{.*?provinces\s*=\s*\{([^}]*)\}.*?\n\}', re.DOTALL)
    province_pattern = re.compile(r'"(x[0-9A-F]+)"')

    # Use list comprehension for file reading
    files: list[str] = [path.join(file_path, f) for f in listdir(file_path)]

    for fileName in files:
        with open(fileName, 'r', encoding='utf-8') as file:
            content = file.read()

        # Use pre-compiled patterns
        state_blocks = state_pattern.findall(content)
        for state_name, provinces_str in state_blocks:
            # Process provinces in bulk
            province_dict = {
                province[1:]: {
                    'name': state_name[6:],
                    'x': 0, 'y': 0,
                    'climate': '',
                    'topography': '',
                    'vegetation': ''
                }
                for province in province_pattern.findall(provinces_str)
            }
            provinces_init.update(province_dict)

    return provinces_init


def load_province_V3_terrain_types(filepath: str) -> dict:
    """Loads the color-to-terrain mapping from a file."""
    mapping: dict = {}
    with open(filepath, 'r') as f:
        lines: list[str] = [line.strip() for line in f if '=' in line]
        for line in lines:
            color_hex, terrain = line.split('=')
            color_hex = color_hex.lstrip('x')
            terrain = literal_eval(terrain)  # .strip('\"')
            # color_rgb = tuple(int(color_hex[i:i + 2], 16) for i in (0, 2, 4))
            mapping[color_hex] = terrain
    return mapping


def load_location_mappings(filepath: str, featureName: str):
    global dict_locations
    with open(filepath, 'r', encoding='UTF-8-sig') as f:
        lines: list[str] = [line.strip() for line in f if ',' in line]
        for line in lines:
            color_hex, feature = line.split(',')
            if color_hex in dict_locations:
                dict_locations[color_hex][featureName] = feature
            # else:
            #     print(f'{color_hex} is not in provinces')


def load_province_features(filepath: str) -> dict:
    mapping: dict = {}
    with open(filepath, 'r', encoding='UTF-8-sig') as f:
        lines: list[str] = [line.strip() for line in f if ';' in line]
        for line in lines:
            key, colorHex, desc_short, desc_long = line.split(';')
            mapping[key] = {'color': colorHex, 'desc_short': desc_short, 'desc_long': desc_long}
    return mapping


def construct_map_from_mapping(p_dict_locations: dict, p_arr_original: ndarray, p_feature_data: dict, isGradient=False,
                               needsConversionToRGB=False):
    # Create a new dictionary with only the specific feature
    mapping = {hex_code: location_data[feature_type]
               for hex_code, location_data in p_dict_locations.items()
               if feature_type in location_data}

    modifiedArray: np.ndarray = np.copy(p_arr_original)
    # Create original to new color mapping
    original_to_new = {}

    if p_feature_data:
        for orig_hex, label in mapping.items():
            color_original: tuple = hex_to_rgb(orig_hex)
            color_new: tuple = p_feature_data[label]['color']
            if needsConversionToRGB:
                color_new = hex_to_rgb(color_new)
            original_to_new[color_original] = color_new
    else:
        for orig_hex, label in mapping.items():
            label = int(label)
            color_original: tuple = hex_to_rgb(orig_hex)
            color_new: tuple = (label, label, label)
            original_to_new[color_original] = color_new

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


def convert_hotkey_strings_to_qt():
    for _, feature in feature_data.items():
        feature['hotkey'] = [convert_key_string_to_qt(hotkey) for hotkey in feature['hotkey']]


if __name__ == "__main__":
    # try:
    app: QApplication = QApplication(sys.argv)

    start_time = time.time()

    # Pre-load all required data
    time_task = resetTimer('Starting state parsing...')
    dict_locations: dict = parse_states('state_regions')
    print(f"State parsing completed in {time.time() - time_task:.2f} seconds")

    # time_task = resetTimer('Loading feature details...')
    # details_koppen: dict = load_details_feature(FILE_TXT_DETAILS_KOPPEN)
    # details_topography: dict = load_details_topography(FILE_TXT_DETAILS_TOPOGRAPHY)
    # details_vegetation: dict = load_details_vegetation(FILE_TXT_DETAILS_VEGETATION)
    # print(f"Feature details loaded in {time.time() - time_task:.2f} seconds")

    time_task = resetTimer('Loading V3 province terrains...')
    location_to_v3TerrainType: dict = load_province_V3_terrain_types(FILE_TXT_TERRAINS)
    print(f"V3 province terrains loaded in {time.time() - time_task:.2f} seconds")

    time_task = resetTimer('Loading feature details and data...')
    for feature_type, config in feature_data.items():

        isGradient = config['isGradient']
        filePath = config['file_details'] if 'file_details' in config else f'{PATH_LOCATION_MAPPINGS}{feature_type}.csv'
        load_location_mappings(filePath, feature_type)

        if not isGradient:
            filePath = config['file_data'] if 'file_data' in config else f'{PATH_FEATURE_DETAILS}{feature_type}.csv'
            feature_data[feature_type]['labels'] = load_province_features(filePath)
            # details = load_feature_details(dict_locations, config['key'])
        else:
            feature_data[feature_type]['labels'] = {}
            labels_suitability_len = len(labels_suitability)
            for i in range(256):
                desc_long = labels_suitability[min(labels_suitability_len - 1, int(i / (256 / labels_suitability_len)))]
                feature_data[feature_type]['labels'][str(i)] = {'color': rgb_to_hex(*(i, i, i)), 'desc_short': i,
                                                                'desc_long': desc_long}

    print(f"Feature details and data loaded in {time.time() - time_task:.2f} seconds")

    time_task = resetTimer('Getting array from locations image...')
    arr_original: ndarray = get_array_from_image(FILE_IMAGE_LOCATIONS_INPUT)

    # Create feature maps
    feature_pixmaps = {}
    for feature_type, config in feature_data.items():
        time_task = resetTimer(f'Creating {feature_type} map...')
        feature_pixmaps[feature_type] = construct_map_from_mapping(
            dict_locations,
            arr_original,
            None if config['isGradient'] else feature_data[feature_type]['labels'],
            config['isGradient'],
            config['needs_rgb_conversion']
        )
        print(f"{feature_type} map created in {time.time() - time_task:.2f} seconds")

    print(f"Arrays from images retrieved in {time.time() - time_task:.2f} seconds")

    convert_hotkey_strings_to_qt()

    # Initialize MapEditor with consolidated data
    map_editor = MapEditor(
        arr_original,
        feature_pixmaps,
        dict_locations,
        location_to_v3TerrainType,
        feature_data
    )
    map_editor.resize(1200, 800)
    map_editor.show()
    print(f"Map editor ready! It took a total of {time.time() - start_time:.2f} seconds")
    sys.exit(app.exec_())
    # except Exception as e:
    #     print(f"Error: {e}")
    #     sys.exit(1)
