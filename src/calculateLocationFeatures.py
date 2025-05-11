"""Used when having prepared maps so that this script can find the dominant feature in each location(covers most pixels)"""
import time

import numpy as np
from PIL import Image
from numpy import ndarray
from tqdm import tqdm  # Add this import at the top of the file

from main import resetTimer, get_array_from_image, FILE_IMAGE_LOCATIONS_INPUT
from src.auxiliary import rgb_to_hex

FEATURE_FILES = {
    'koppen': {
        'input': 'koppen_v3_16.png',
    },
    'topography': {
        'input': 'location_topography_16.png',
    },
    'vegetation': {
        'input': 'location_vegetation_8.png',
    },
    'low_wheat': {
        'input': 'location_low_wheat_input.png',
    },
    'low_tubers': {
        'input': 'location_low_tubers_input.png',
    }
}


def calculate_location_features(p_arr_locations: ndarray, arr_features: ndarray, path_output: str,
                                output_file_txt: str, is_gradient: bool = False,
                                color_to_skip: tuple[int, int, int] = None):
    # Verify image dimensions match
    if p_arr_locations.shape != arr_features.shape:
        raise ValueError("Region and feature images must have the same dimensions.")

    # Create output mapping file
    mapping_file_path = "province_koppen_colors.txt"

    # Reshape arrays to 2D for faster processing
    original_2d = p_arr_locations.reshape(-1, 3)
    koppen_2d = arr_features.reshape(-1, 3)

    # Get unique regions and their indices more efficiently
    unique_regions, inverse_indices = np.unique(original_2d, axis=0, return_inverse=True)

    # Create a mapping array for the final result
    result_colors = np.zeros_like(unique_regions)

    # Dictionary to store region to climate mappings
    climate_mappings = {}

    # Convert the color to skip into the same integer format
    if color_to_skip:
        color_to_skip = (color_to_skip[0] * 256 * 256 + color_to_skip[1] * 256 + color_to_skip[2])

    # Process each unique region
    lenUniqueColors = len(unique_regions)
    step = max(lenUniqueColors // 100, 1)

    with tqdm(total=lenUniqueColors, desc="Processing regions", unit="region") as pbar:
        for i, color in enumerate(unique_regions):
            # Find all pixels belonging to this region
            region_mask = (inverse_indices == i)

            # Get feature values for this region
            region_features = koppen_2d[region_mask]

            if len(region_features) > 0:
                if is_gradient:
                    # Calculate average values for each RGB channel
                    dominant_feature = np.mean(region_features, axis=0).astype(np.int32)

                    # Store mapping using hex for region and numerical value for gradient
                    region_hex = f"{rgb_to_hex(*color)}"
                    # Calculate single gradient value (assuming grayscale where R=G=B)
                    gradient_value = int(np.mean(dominant_feature))
                    climate_mappings[region_hex] = gradient_value
                else:
                    # Original logic for categorical features
                    feature_ints = (region_features[:, 0].astype(np.int32) * 256 * 256 +
                                    region_features[:, 1].astype(np.int32) * 256 +
                                    region_features[:, 2])
                    unique_features, counts = np.unique(feature_ints, return_counts=True)

                    if color_to_skip:
                        # Find the index of the most common color that isn't the one to skip
                        if len(counts) > 1:  # Make sure we have at least 2 colors
                            sorted_indices = np.argsort(counts)[::-1]  # Sort indices by count (descending)
                            for idx in sorted_indices:
                                if unique_features[idx] != color_to_skip:
                                    dominant_feature_int = unique_features[idx]
                                    break
                        else:
                            dominant_feature_int = unique_features[0]  # If only one color exists, use it
                    else:
                        dominant_feature_int = unique_features[np.argmax(counts)]

                    # Convert back to RGB
                    dominant_feature = [
                        dominant_feature_int // (256 * 256),
                        (dominant_feature_int // 256) % 256,
                        dominant_feature_int % 256
                    ]

                    # Store mapping using hex colors for both
                    region_hex = f"{rgb_to_hex(*color)}"
                    feature_hex = f"{rgb_to_hex(*dominant_feature)}"
                    climate_mappings[region_hex] = feature_hex

                result_colors[i] = dominant_feature

            if i % step == step - 1:
                pbar.update(step)

                # Write mappings to file
                with open(output_file_txt, 'w+') as f:
                    for region, value in sorted(climate_mappings.items()):
                        f.write(f"{region}={value}\n")
                output_arr = result_colors[inverse_indices].reshape(arr_features.shape)
                Image.fromarray(output_arr.astype(np.uint8)).save(path_output)
                pass

    with open(output_file_txt, 'w+') as f:
        for region, value in sorted(climate_mappings.items()):
            f.write(f"{region}={value}\n")
    # Apply the results using broadcasting
    output_arr = result_colors[inverse_indices].reshape(arr_features.shape)

    # Save the result image
    Image.fromarray(output_arr.astype(np.uint8)).save(path_output)

    # return output_arr


def generateLocationMapAndTextFromInputMap(feature, is_gradient=False):
    global time_task
    time_task = resetTimer(f'Creating map for {feature}...')
    arr_feature = get_array_from_image(FEATURE_FILES[feature]['input'])
    calculate_location_features(
        arr_locations,
        arr_feature,
        f'res/location_{feature}.png',
        f'res/location_{feature}.csv',
        is_gradient
    )
    print(f'Map for {feature} created in {time.time() - time_task:.2f} seconds')


if __name__ == "__main__":
    time_task = resetTimer('Getting array from images...')
    arr_locations: ndarray = get_array_from_image(FILE_IMAGE_LOCATIONS_INPUT)
    print(f"Arrays from images retrieved in {time.time() - time_task:.2f} seconds")

    # time_task = resetTimer('Creating Victoria 3 climate map...')
    # modified_pixmap: QPixmap = construct_map_from_mapping(location_to_v3TerrainType, terrain_colors)
    # print(f"V3 climate map created in {time.time() - time_task:.2f} seconds")

    # generateLocationMapAndTextFromInputMap('koppen')
    # generateLocationMapAndTextFromInputMap('topography')
    # generateLocationMapAndTextFromInputMap('vegetation')
    # generateLocationMapAndTextFromInputMap('low_wheat', True)
    # generateLocationMapAndTextFromInputMap('low_tubers', True)

# 'output_image': 'location_koppen.png',
# 'output_data': 'province_koppen_colors.txt'
