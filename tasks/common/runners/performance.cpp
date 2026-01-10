#include <benchmark/benchmark.h>
#include <mpi.h>

#include <format>
#include <iostream>
#include <vector>

#include "oneapi/tbb/global_control.h"
#include "util/include/util.hpp"

namespace {
class NullReporter : public benchmark::BenchmarkReporter {
 public:
  bool ReportContext(const Context & /*context*/) override {
    return true;
  }

  void ReportRuns(const std::vector<Run> & /*runs*/) override {}
};
}  // namespace

int main(int argc, char **argv) {
  const int init_res = MPI_Init(&argc, &argv);
  if (init_res != MPI_SUCCESS) {
    std::cerr << std::format("[  ERROR  ] MPI_Init failed with code {}\n", init_res);
    return init_res;
  }

  tbb::global_control control(tbb::global_control::max_allowed_parallelism, ppc::util::GetNumThreads());

  int rank = 0;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);

  // Storage for filtered argv to keep lifetime until program end
  static std::vector<std::string> arg_storage;
  static std::vector<char *> argv_storage;

  // Strip file-output flags on non-root ranks to avoid concurrent writes
  if (rank != 0) {
    arg_storage.clear();
    argv_storage.clear();
    arg_storage.reserve(static_cast<std::size_t>(argc));
    argv_storage.reserve(static_cast<std::size_t>(argc) + 1);
    arg_storage.emplace_back(argv[0]);
    for (int i = 1; i < argc; ++i) {
      std::string_view arg = argv[i] ? argv[i] : "";
      if (arg.starts_with("--benchmark_out") || arg.starts_with("--benchmark_out_format")) {
        continue;
      }
      arg_storage.emplace_back(argv[i]);
    }
    for (auto &s : arg_storage) {
      argv_storage.push_back(s.data());
    }
    argv_storage.push_back(nullptr);
    argc = static_cast<int>(argv_storage.size()) - 1;
    argv = argv_storage.data();
  }

  ::benchmark::Initialize(&argc, argv);
  if (::benchmark::ReportUnrecognizedArguments(argc, argv)) {
    MPI_Finalize();
    return 1;
  }

  if (rank == 0) {
    (void)::benchmark::RunSpecifiedBenchmarks();
  } else {
    NullReporter null_reporter;
    (void)::benchmark::RunSpecifiedBenchmarks(&null_reporter);
  }
  ::benchmark::Shutdown();

  const int finalize_res = MPI_Finalize();
  if (finalize_res != MPI_SUCCESS) {
    std::cerr << std::format("[  ERROR  ] MPI_Finalize failed with code {}\n", finalize_res);
    return finalize_res;
  }

  return 0;
}
