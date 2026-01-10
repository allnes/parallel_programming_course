#include <benchmark/benchmark.h>

#include "example_threads/all/include/ops_all.hpp"
#include "example_threads/common/include/common.hpp"
#include "example_threads/omp/include/ops_omp.hpp"
#include "example_threads/seq/include/ops_seq.hpp"
#include "example_threads/stl/include/ops_stl.hpp"
#include "example_threads/tbb/include/ops_tbb.hpp"
#include "util/include/perf_test_util.hpp"

namespace nesterov_a_test_task_threads {
namespace {

constexpr int kCount = 200;

InType MakeInput() {
  return kCount;
}

bool CheckOutput(const InType &input, const OutType &output) {
  return input == output;
}

struct BenchmarkRegistrar {
  BenchmarkRegistrar() {
    ppc::util::BenchmarkParams params{};
    params.iterations = 1;
    ppc::util::RegisterBenchmarksForTasks<InType, OutType, NesterovATestTaskALL, NesterovATestTaskOMP,
                                          NesterovATestTaskSEQ, NesterovATestTaskSTL, NesterovATestTaskTBB>(
        PPC_SETTINGS_example_threads, MakeInput, CheckOutput, params);
  }
};

const BenchmarkRegistrar kRegistrar{};

}  // namespace
}  // namespace nesterov_a_test_task_threads
