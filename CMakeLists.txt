cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(TMJ_Analysis)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/YourUsername/TMJ_Analysis")
set(EXTENSION_CATEGORY "TMJ")
set(EXTENSION_CONTRIBUTORS "Feng (Your Organization)")
set(EXTENSION_DESCRIPTION "TMJ Analysis - A comprehensive 3D Slicer extension for Temporomandibular Joint analysis, including data processing and image registration.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/YourUsername/TMJ_Analysis/main/TMJExtension/Resources/Icons/TMJExtension.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/YourUsername/TMJ_Analysis/main/Screenshots/Screenshot1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules

# TMJ Extension - Python module for data processing
add_subdirectory(TMJExtension)

# TMJ Registration - Python wrapper + C++ CLI backend
add_subdirectory(TMJRegistration)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
