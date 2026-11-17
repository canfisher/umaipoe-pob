import re
from pathlib import Path
import sys

root = Path(sys.argv[1])
original = (root / 'CMakeLists.txt').read_text(encoding='utf-8')
host = original.split('add_executable(pob-zh WIN32', 1)[1].split('\n    )', 1)[0]
host = '\n'.join(line for line in host.splitlines() if not line.strip().startswith('#'))
host = host.replace('${IMGUI_SOURCES}', '''dep/imgui/imgui.cpp dep/imgui/imgui_draw.cpp
dep/imgui/imgui_tables.cpp dep/imgui/imgui_widgets.cpp
dep/imgui/misc/cpp/imgui_stdlib.cpp dep/imgui/backends/imgui_impl_glfw.cpp
dep/imgui/backends/imgui_impl_opengl3.cpp''')
cmake = '''cmake_minimum_required(VERSION 3.20)
project(UmaipoeHost LANGUAGES C CXX RC)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_executable(pob-zh WIN32
''' + host + ''')
target_compile_definitions(pob-zh PRIVATE UNICODE _UNICODE IMGUI_IMPL_OPENGL_ES2 _CRT_SECURE_NO_WARNINGS)
target_compile_options(pob-zh PRIVATE /utf-8 /O2 /EHsc /bigobj)
set_property(TARGET pob-zh PROPERTY MSVC_RUNTIME_LIBRARY MultiThreaded)
target_include_directories(pob-zh PRIVATE dep/imgui dep/imgui/backends dep/imgui/misc/cpp dep/stb dep/miniz deps/nlohmann vendor/include)
target_link_directories(pob-zh PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/vendor/lib")
target_link_libraries(pob-zh PRIVATE glfw3 libGLESv2 WebView2Loader libwebpdecoder delayimp)
target_link_options(pob-zh PRIVATE /DELAYLOAD:glfw3.dll /DELAYLOAD:libGLESv2.dll /DELAYLOAD:WebView2Loader.dll /DELAYLOAD:libwebpdecoder.dll)
add_executable(farming-test host/farming_test.cpp host/atlas_persist.cpp engine/common/base64.c)
target_include_directories(farming-test PRIVATE host deps/nlohmann)
target_compile_options(farming-test PRIVATE /utf-8 /O2 /EHsc)
set_property(TARGET farming-test PROPERTY MSVC_RUNTIME_LIBRARY MultiThreaded)
add_executable(branding-test host/branding_test.cpp)
target_include_directories(branding-test PRIVATE host)
target_compile_options(branding-test PRIVATE /utf-8 /O2 /EHsc)
set_property(TARGET branding-test PROPERTY MSVC_RUNTIME_LIBRARY MultiThreaded)
add_executable(navigation-test host/navigation_test.cpp)
target_include_directories(navigation-test PRIVATE host)
target_compile_definitions(navigation-test PRIVATE UNICODE _UNICODE)
target_compile_options(navigation-test PRIVATE /utf-8 /O2 /EHsc)
target_link_libraries(navigation-test PRIVATE user32)
set_property(TARGET navigation-test PROPERTY MSVC_RUNTIME_LIBRARY MultiThreaded)
'''
(root / 'CMakeLists.txt').write_text(cmake, encoding='utf-8')
