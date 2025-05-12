PC Feature Map Editor​

Goal:
Speed up the modding of PC’s map’s terrain features.
It also provides maps for *climate*, vegetation, topography, etc. to get started modding a more accurate world

Features:

    The application has a ready-to-export game data file (.txt) to immediately be used as a source of climate, topography & vegetation terrain types (and other features), whose structure will be finalized when the game is released.
    I expect the game to be provided already with a map editor, enabling terrain feature editing, however I am inspired to have a more diverse terrain, so I have prepared a way to instantly replace the vanilla terrain system with a new one.
    There are 27,518 unique locations in the game and if it takes 1-5 seconds to provide/update a location feature for each one, it would take 8-38h per map feature and I prepared 3 + 2 types -> climate, topography, vegetation + wheat (low) and tubers (low).

Map editor features:

    View terrain features of hovered location (besides the location name and HEX color)
    Switch between views
        (via button clicking or hotkeys)

image11.png

image2.png

image13.png

image4.png

image16.png

    Search for provinces

image5.png

    Feature picker
        copy from hovered location or
        open feature selection window or
        select feature by clicking the corresponding legend item

image9.png

    Paint on other locations

image1.png

image12.png

    Undo & Redo
    Export feature files

Methodology
Mock-up
image14.png

In the first iteration, I have used as mock-up data for the location file Victoria 3’s provinces.png image, so that the rest of the functionality can be prepared.
Base

    Imported the location file, where each province/location is represented by a contiguous region having a unique color hex
    Extracted the location names from ‘state_regions’ folder and associated each hex color with the corresponding name.
    The information the map editor uses is in the form of text files, as Pavia stated that PC will be using the same (for loading efficiency).
    For every map feature the editor has (e.g. Vic3 terrain type, Köppen climate, topography, vegetation, etc.), I have used/created a map having the same shape and projection as the location file, then created a Python script that finds the dominant feature in every location (colored patch; via pixel counting; taking ~1h for each type), all so that the mapping text file is created, representing a list of mappings in the format ‘#HEX=FeatureLabel’ (basically also outputting a recoloring of the locations file)

image15.png

    I expect the feature details to be either in separate text files or everything in one file and I will perform the necessary parsing once the game is released
    Maps were created in the software QGIS, where useful map operations can be made, such as changing the map projections, to match the one in the location file, called Miller. The projections must match to prevent distortion errors.
    When the application is started it loads the location file, then for every feature type it generates its corresponding recolored map based on the mapping text files.


Köppen (Climate)
The geotiff (map) is the earliest one available, the 1900s one, from link
image8.png

The editor displays the Koppen abbreviation, full name and definition (temperature and precipitation conditions)
This is the final and more discrete version of the map:
image11.png

Inspiration: Sulphurologist's approach to new climate terrain type system
Vanilla: Climate.png

Topography

DEM (Digital Elevation Model)
The geotiff (map) is ‘World_ELE_GISdata_GlobalSolarAtlas-v2_GEOTIFF’ from link
image17.png


TRI (Terrain Ruggedness Index)
image6.png

The geotiff (map) is from link.


I have taken inspiration from one of the posts from Sulphurologist from the Paradox Plaza forum, where they’ve proposed to combine DEM with TRI and have suggested a table of topography labels for different combinations of labels from the two maps.
image10.png

The two maps do not overlap, and since it is necessary, I have created an intersection of them and the result has missing information in areas like the extreme northern hemisphere (North of N America & Russia)

This is the final version of the map:
image2.png

Vanilla: Topography.png


Vegetation

image7.png

The geotiffs are from link, showing the following information:

    Evergreen/Deciduous Needleleaf Trees
    Evergreen Broadleaf Trees
    Deciduous Broadleaf Trees
    Mixed/Other Trees
    Shrubs
    Herbaceous Vegetation
    Cultivated and Managed Vegetation
    Regularly Flooded Vegetation
    Urban/Built-up
    Snow/Ice
    Barren
    Open Water


It is necessary to combine them into a single map, so that it shows a limited palette of colors, one for each vegetation type:

    Barren – no sandstorms & no snow
    Desert – barren with sandstorms
    Snow – barren with snow
    Sparse
    Grassland
    Woods
    Forest
    Jungle

The following logic is used to classify:
image3.png


The initial vegetation map does not reflect the vegetation in 1337, however with the help of historians and the map editor, the vegetation map can be made more accurate.

This is the final version of the map:
image13.png

Vanilla: Vegetation.png


Acknowledgements

    Tinto team (Paradox development studio) for working on gems like PC (and Victoria 3).
    Sulphurologist for their works and suggestions on the forum and for helping me find the required map information and the tool to process the maps.

 
