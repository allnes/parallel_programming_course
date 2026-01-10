include_guard()

include(ExternalProject)

ExternalProject_Add(
  ppc_benchmark
  SOURCE_DIR "${CMAKE_SOURCE_DIR}/3rdparty/benchmark"
  PREFIX "${CMAKE_CURRENT_BINARY_DIR}/ppc_benchmark"
  BINARY_DIR "${CMAKE_CURRENT_BINARY_DIR}/ppc_benchmark/build"
  INSTALL_DIR "${CMAKE_CURRENT_BINARY_DIR}/ppc_benchmark/install"
  CMAKE_ARGS -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}
             -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
             -DCMAKE_C_COMPILER_LAUNCHER=${CMAKE_C_COMPILER_LAUNCHER}
             -DCMAKE_CXX_COMPILER_LAUNCHER=${CMAKE_CXX_COMPILER_LAUNCHER}
             -DCMAKE_CXX_STANDARD=${CMAKE_CXX_STANDARD}
             -DCMAKE_CXX_STANDARD_REQUIRED=${CMAKE_CXX_STANDARD_REQUIRED}
             -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
             -DBENCHMARK_ENABLE_TESTING=OFF
             -DBENCHMARK_ENABLE_GTEST_TESTS=OFF
             -DBENCHMARK_ENABLE_INSTALL=ON
             -DBENCHMARK_ENABLE_LIBPFM=OFF
  BUILD_COMMAND
    "${CMAKE_COMMAND}" --build "${CMAKE_CURRENT_BINARY_DIR}/ppc_benchmark/build"
    --config $<CONFIG> --parallel
  INSTALL_COMMAND
    "${CMAKE_COMMAND}" --install
    "${CMAKE_CURRENT_BINARY_DIR}/ppc_benchmark/build" --config $<CONFIG>
    --prefix "${CMAKE_CURRENT_BINARY_DIR}/ppc_benchmark/install")

function(ppc_link_benchmark target)
  target_include_directories(
    ${target} PUBLIC ${CMAKE_SOURCE_DIR}/3rdparty/benchmark/include)
  add_dependencies(${target} ppc_benchmark)
  target_link_directories(${target} PUBLIC
                          "${CMAKE_BINARY_DIR}/ppc_benchmark/install/lib")
  target_link_libraries(${target} PUBLIC benchmark)
endfunction()
