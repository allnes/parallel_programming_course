include_directories(${CMAKE_SOURCE_DIR}/3rdparty/microprofile)

set(PPC_MICROPROFILE_PREFIX ${CMAKE_BINARY_DIR}/ppc_microprofile)

include(ExternalProject)
ExternalProject_Add(ppc_microprofile
        SOURCE_DIR        "${CMAKE_SOURCE_DIR}/3rdparty/microprofile"
        PREFIX            "${PPC_MICROPROFILE_PREFIX}"
        BINARY_DIR        "${PPC_MICROPROFILE_PREFIX}/build"
        INSTALL_DIR       "${PPC_MICROPROFILE_PREFIX}/install"
        CMAKE_ARGS
        -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}
        -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
        -DCMAKE_C_COMPILER_LAUNCHER=${CMAKE_C_COMPILER_LAUNCHER}
        -DCMAKE_CXX_COMPILER_LAUNCHER=${CMAKE_CXX_COMPILER_LAUNCHER}
        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
        -DCMAKE_INSTALL_PREFIX="${PPC_MICROPROFILE_PREFIX}/install"
        BUILD_COMMAND     "${CMAKE_COMMAND}" --build "${PPC_MICROPROFILE_PREFIX}/build" --config ${CMAKE_BUILD_TYPE} --parallel
        INSTALL_COMMAND   "${CMAKE_COMMAND}" --install "${PPC_MICROPROFILE_PREFIX}/build"
)
