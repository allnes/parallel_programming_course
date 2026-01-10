#include <benchmark/benchmark.h>

#include "example_processes_2/common/include/common.hpp"
#include "example_processes_2/mpi/include/ops_mpi.hpp"
#include "example_processes_2/seq/include/ops_seq.hpp"
#include "util/include/perf_test_util.hpp"

namespace nesterov_a_test_task_processes_2 {
namespace {

constexpr int kCount = 100;

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
    ppc::util::RegisterBenchmarksForTasks<InType, OutType, NesterovATestTaskMPI, NesterovATestTaskSEQ>(
        PPC_SETTINGS_example_processes_2, MakeInput, CheckOutput, params);
  }
};

const BenchmarkRegistrar kRegistrar{};

}  // namespace
}  // namespace nesterov_a_test_task_processes_2
