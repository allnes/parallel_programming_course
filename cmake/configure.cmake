if(MSVC)
    option(gtest_force_shared_crt "" TRUE)
endif(MSVC)

if (APPLE)
    set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG TRUE)
endif(APPLE)

set( CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/arch" )
set( CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/lib" )
set( CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/bin" )

set( CMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/arch" )
set( CMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/lib" )
set( CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin" )

set( CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/arch" )
set( CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib" )
set( CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin" )

set( CMAKE_CXX_STANDARD 20 )

string(FIND "${CMAKE_CXX_COMPILER_ID}" "Clang" CLANG_SUBSTR)
if( UNIX OR (CLANG_SUBSTR GREATER -1) )
    set(CMAKE_C_FLAGS  "${CMAKE_C_FLAGS}     \
        -Wall -Wextra                        \
        -Wno-unused-parameter                \
        -Wno-cast-function-type              \
        -Wno-unused-command-line-argument    \
        -Wsign-compare  -Werror")
    set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} \
        -Wall -Wextra                        \
        -Wno-unused-parameter                \
        -Wno-cast-function-type              \
        -Wno-unused-command-line-argument    \
        -Wsign-compare -Werror")
    if (USE_COVERAGE)
        set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} --coverage")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} --coverage")
    endif(USE_COVERAGE)
endif( UNIX OR (CLANG_SUBSTR GREATER -1) )

if( MSVC )
    set(CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS}")
    set(CMAKE_C_FLAGS_RELEASE   "${CMAKE_C_FLAGS_RELEASE} /W4 /wd4267 /wd4244 /wd4100 /WX" )
    set(CMAKE_C_FLAGS_DEBUG     "${CMAKE_C_FLAGS_DEBUG} /W4 /wd4267 /wd4244 /wd4100 /WX")
    set(CMAKE_C_FLAGS           "${CMAKE_C_FLAGS} /W4 /wd4267 /wd4244 /wd4100 /WX" )
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /W4 /wd4267 /wd4244 /wd4100 /WX" )
    set(CMAKE_CXX_FLAGS_DEBUG   "${CMAKE_CXX_FLAGS_DEBUG} /W4 /wd4267 /wd4244 /wd4100 /WX")
    set(CMAKE_CXX_FLAGS         "${CMAKE_CXX_FLAGS} /W4 /wd4267 /wd4244 /wd4100 /WX" )
endif( MSVC )

add_compile_definitions(PPC_PATH_TO_PROJECT="${CMAKE_CURRENT_SOURCE_DIR}")

MACRO(SUBDIRLIST result curdir)
  FILE(GLOB children RELATIVE ${curdir} ${curdir}/*)
  SET(dirlist "")
  FOREACH(child ${children})
    IF(IS_DIRECTORY ${curdir}/${child})
      LIST(APPEND dirlist ${child})
    ENDIF()
  ENDFOREACH()
  SET(${result} ${dirlist})
ENDMACRO()
