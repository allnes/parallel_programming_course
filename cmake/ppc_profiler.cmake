if(PPC_ENABLE_PROFILING)
  add_library(ppc_microprofile STATIC
    3rdparty/microprofile/microprofile.cpp
  )
  target_include_directories(ppc_microprofile PUBLIC
    ${CMAKE_SOURCE_DIR}/3rdparty/microprofile
    ${CMAKE_SOURCE_DIR}/modules/common/include
  )
  target_compile_definitions(ppc_microprofile PUBLIC
    MICROPROFILE_ENABLED=1
    MICROPROFILE_USE_CONFIG=1
  )
else()
  add_library(ppc_microprofile INTERFACE)
  target_compile_definitions(ppc_microprofile INTERFACE MICROPROFILE_ENABLED=0)
endif()

