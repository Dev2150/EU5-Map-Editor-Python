import re
from ast import literal_eval
from os import listdir, path

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
            mapping[color_hex] = terrain
    return mapping


def load_location_mappings(filepath: str, featureName: str, dict_locations: dict):
    """Loads mappings from a CSV file and adds them to dict_locations.
    
    Args:
        filepath: Path to the CSV file with color,feature mappings
        featureName: The feature type to add to locations dictionary
        dict_locations: Dictionary to update with feature data
    """
    with open(filepath, 'r', encoding='UTF-8-sig') as f:
        lines: list[str] = [line.strip() for line in f if ',' in line]
        for line in lines:
            color_hex, feature = line.split(',')
            if color_hex in dict_locations:
                dict_locations[color_hex][featureName] = feature


def load_province_features(filepath: str) -> dict:
    """Loads feature details from a CSV file.
    
    Args:
        filepath: Path to the CSV file with feature details
        
    Returns:
        Dictionary mapping feature keys to their details
    """
    mapping: dict = {}
    with open(filepath, 'r', encoding='UTF-8-sig') as f:
        lines: list[str] = [line.strip() for line in f if ';' in line]
        for line in lines:
            key, colorHex, desc_short, desc_long = line.split(';')
            mapping[key] = {'color': colorHex, 'desc_short': desc_short, 'desc_long': desc_long}
    return mapping


def load_feature_data(filepath: str) -> dict:
    """Load feature configuration data from JSON file."""
    import json
    with open(filepath, 'r') as f:
        return json.load(f) 