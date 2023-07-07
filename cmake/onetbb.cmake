# Build Core OneTBB components
include_directories(${CMAKE_SOURCE_DIR}/3rdparty/onetbb/include)

if (APPLE)
include(ExternalProject)
    ExternalProject_Add(ppc_onetbb
            SOURCE_DIR        "${CMAKE_SOURCE_DIR}/3rdparty/onetbb"
            PREFIX            ${CMAKE_CURRENT_BINARY_DIR}/ppc_onetbb
            BINARY_DIR        "${CMAKE_CURRENT_BINARY_DIR}/ppc_onetbb/build"
            INSTALL_DIR       "${CMAKE_CURRENT_BINARY_DIR}/ppc_onetbb/install"
            CONFIGURE_COMMAND "${CMAKE_COMMAND}" -S "${CMAKE_SOURCE_DIR}/3rdparty/onetbb/" -B "${CMAKE_CURRENT_BINARY_DIR}/ppc_onetbb/build/"
            -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER} -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER} -G${CMAKE_GENERATOR}
            -DTBB_TEST=OFF -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
            BUILD_COMMAND     "${CMAKE_COMMAND}" --build "${CMAKE_CURRENT_BINARY_DIR}/ppc_onetbb/build"
            INSTALL_COMMAND   "${CMAKE_COMMAND}" --install "${CMAKE_CURRENT_BINARY_DIR}/ppc_onetbb/build" --prefix "${CMAKE_CURRENT_BINARY_DIR}/ppc_onetbb/install"
            TEST_COMMAND      "")
elseif ()
    option(TBB_TEST "Enable testing" OFF)
    add_subdirectory(${CMAKE_SOURCE_DIR}/3rdparty/onetbb)
endif ()