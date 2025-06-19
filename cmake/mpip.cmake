include(ExternalProject)

set(MPIP_SOURCE_DIR ${CMAKE_SOURCE_DIR}/3rdparty/mpip)
set(MPIP_BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR}/ppc_mpip)
set(MPIP_BUILD_DIR  ${MPIP_BINARY_DIR}/build)
set(MPIP_INSTALL_DIR ${MPIP_BINARY_DIR}/install)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
    set(MPIP_ARCH "__aarch64__")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|x64|amd64)$")
    set(MPIP_ARCH "__x86_64__")
else()
    message(FATAL_ERROR "Unsupported architecture: ${CMAKE_SYSTEM_PROCESSOR}")
endif()

if(APPLE)
    set(MPIP_PLATFORM_DEFINE "-DDarwin")
else()
    set(MPIP_PLATFORM_DEFINE "-DLinux")
endif()

set(MPIP_CFLAGS "-D${MPIP_ARCH} ${MPIP_PLATFORM_DEFINE} -I${MPIP_SOURCE_DIR}")

ExternalProject_Add(mpip
        SOURCE_DIR     ${MPIP_SOURCE_DIR}
        BINARY_DIR     ${MPIP_BUILD_DIR}

        PATCH_COMMAND
        ${CMAKE_COMMAND} -E echo "Patching mpiPi.h: <malloc.h> → <stdlib.h>" &&
        ${CMAKE_COMMAND} -E copy_if_different ${MPIP_SOURCE_DIR}/mpiPi.h ${MPIP_SOURCE_DIR}/mpiPi.h.bak &&
        ${CMAKE_COMMAND} -E copy ${MPIP_SOURCE_DIR}/mpiPi.h ${MPIP_SOURCE_DIR}/mpiPi.h.tmp &&
        ${CMAKE_COMMAND} -E remove -f ${MPIP_SOURCE_DIR}/mpiPi.h &&
        sed "s|#include <malloc.h>|#include <stdlib.h>|g" ${MPIP_SOURCE_DIR}/mpiPi.h.tmp > ${MPIP_SOURCE_DIR}/mpiPi.h &&
        ${CMAKE_COMMAND} -E remove -f ${MPIP_SOURCE_DIR}/mpiPi.h.tmp &&
        ${CMAKE_COMMAND} -E make_directory ${MPIP_SOURCE_DIR}/arch &&
        ${CMAKE_COMMAND} -E make_directory ${MPIP_BUILD_DIR}/arch &&
        ${CMAKE_COMMAND} -E copy_if_different ${CMAKE_SOURCE_DIR}/3rdparty/arch_arm64.h ${MPIP_SOURCE_DIR}/arch/arch_arm64.h &&
        ${CMAKE_COMMAND} -E copy_if_different ${CMAKE_SOURCE_DIR}/3rdparty/arch_arm64.h ${MPIP_BUILD_DIR}/arch/arch_arm64.h

        CONFIGURE_COMMAND
        /bin/sh -c "env F77=no F90=no FC=no CC=${MPI_C_COMPILER} ${MPIP_SOURCE_DIR}/configure --prefix=${MPIP_INSTALL_DIR} CFLAGS='${MPIP_CFLAGS}'"

        BUILD_COMMAND make libmpiP.a
        INSTALL_COMMAND ""  # Убираем make install
        BUILD_IN_SOURCE 0
        UPDATE_DISCONNECTED TRUE
)

add_library(mpip_lib STATIC IMPORTED GLOBAL)
add_dependencies(mpip_lib mpip)
set_target_properties(mpip_lib PROPERTIES
        IMPORTED_LOCATION ${MPIP_BUILD_DIR}/libmpiP.a
        INTERFACE_INCLUDE_DIRECTORIES ${MPIP_SOURCE_DIR}
)
