cmake_minimum_required(VERSION 3.16)
project(MIRegistration)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 查找ITK
# 当作为 Slicer 扩展构建时，ITK 应该已经可用
# 独立构建时，需要通过 vcpkg 或其他方式安装 ITK
find_package(ITK REQUIRED)
include(${ITK_USE_FILE})

# 包含头文件目录
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# 源文件
set(SOURCES
    src/MattesMutualInformation.cpp
    src/RegularStepGradientDescentOptimizer.cpp
    src/ImageRegistration.cpp
    src/ConfigManager.cpp
    src/main.cpp
)

# 头文件
set(HEADERS
    include/MattesMutualInformation.h
    include/RegularStepGradientDescentOptimizer.h
    include/ImageRegistration.h
    include/ConfigManager.h
)

# 创建可执行文件
add_executable(MIRegistration ${SOURCES} ${HEADERS})

# 针对 MSVC 明确指定源文件编码为 UTF-8
if(MSVC)
    target_compile_options(MIRegistration PRIVATE "/utf-8")
endif()

# 链接ITK库
target_link_libraries(MIRegistration ${ITK_LIBRARIES})

# 设置输出目录
set_target_properties(MIRegistration PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)

# 当作为 Slicer 扩展构建时，安装到 CLI 模块目录
if(DEFINED Slicer_INSTALL_CLIMODULES_BIN_DIR)
    install(TARGETS MIRegistration
        RUNTIME DESTINATION ${Slicer_INSTALL_CLIMODULES_BIN_DIR}
        COMPONENT RuntimeLibraries
    )
endif()

# 安装配置文件
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/config/
    DESTINATION ${CMAKE_BINARY_DIR}/bin/config
    FILES_MATCHING PATTERN "*.json"
)
