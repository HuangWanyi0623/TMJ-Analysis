# TMJ Analysis

A comprehensive 3D Slicer extension for Temporomandibular Joint (TMJ) analysis.

## Overview

TMJ Analysis is a 3D Slicer extension that provides tools for TMJ research and clinical analysis. It contains two main modules:

### TMJ Extension
A Python-based module for data processing and analysis, including:
- **Data Manager**: Import, manage, and export medical imaging data while preserving original HU/intensity values
- **Gold Standard Set**: Manual registration and gold standard setup
- **Coarse Registration**: Fiducial-based coarse registration
- **ROI Mask Set**: Generate ROI masks for the temporomandibular joint region

### TMJ Registration
A registration module that provides a user-friendly interface to perform image registration using mutual information algorithms. Features:
- Rigid and Affine transformation support
- Support for initial transforms (for multi-stage registration)
- Optional mask-based local registration
- ITK-based C++ backend for high-performance registration

## Installation

### From 3D Slicer Extension Manager
1. Open 3D Slicer
2. Go to View → Extension Manager
3. Search for "TMJ Analysis"
4. Click Install

### From Source
1. Clone this repository
2. Open 3D Slicer
3. Go to Developer Tools → Extension Wizard
4. Select the TMJ_Analysis folder

## Building the C++ Backend

The TMJ Registration module requires a compiled C++ backend. To build:

### Prerequisites
- CMake 3.16+
- C++17 compatible compiler
- ITK (can be installed via vcpkg)

### Build Steps (Windows)
```powershell
cd TMJRegistration/Backend
mkdir build
cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=[vcpkg-path]/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release
```

The executable `MIRegistration.exe` will be created in `build/bin/Release/`.

## Project Structure

```
TMJ_Analysis/
├── CMakeLists.txt              # Main CMake configuration
├── TMJ_Analysis.s4ext          # Slicer extension descriptor
├── TMJExtension/               # Data processing module
│   ├── CMakeLists.txt
│   ├── TMJExtension.py
│   ├── DataManager/
│   ├── GoldStandardSet/
│   ├── CoarseRegistration/
│   ├── ROIMaskSet/
│   └── Resources/
└── TMJRegistration/            # Registration module
    ├── CMakeLists.txt
    ├── TMJRegistration.py
    ├── Resources/
    └── Backend/                # C++ registration engine
        ├── CMakeLists.txt
        ├── src/
        ├── include/
        └── config/
```

## Usage

1. Load your medical images into 3D Slicer
2. Navigate to the TMJ category in the Modules menu
3. Select either "TMJ Extension" or "TMJ Registration"
4. Follow the module-specific instructions

## License

This project is developed for TMJ research purposes.

## Contributors

- Feng
