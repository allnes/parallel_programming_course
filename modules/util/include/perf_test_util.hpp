#pragma once

#include <benchmark/benchmark.h>
#include <mpi.h>

#include <chrono>
#include <fstream>
#include <functional>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>

#include "performance/include/performance.hpp"
#include "task/include/task.hpp"
#include "util/include/perf_time_util.hpp"
#include "util/include/util.hpp"

namespace ppc::util {

struct BenchmarkParams {
  int iterations = 1;
  double max_time_sec = GetPerfMaxTime();
};

inline std::string ReadTasksType(const std::string &settings_path) {
  try {
    std::ifstream f(settings_path);
    if (!f.is_open()) {
      return {};
    }
    nlohmann::json j;
    f >> j;
    if (j.contains("tasks_type") && j["tasks_type"].is_string()) {
      return j["tasks_type"].get<std::string>();
    }
  } catch (...) {
  }
  return {};
}

template <typename InType, typename OutType>
using OutputChecker = std::function<bool(const InType &, const OutType &)>;

namespace detail {
inline bool ShouldSkipByName(const std::string &name) {
  return name.find("unknown") != std::string::npos || name.find("disabled") != std::string::npos;
}

inline void SetCommonCounters(benchmark::State &state) {
  state.counters["Threads"] = static_cast<double>(ppc::util::GetNumThreads());
  state.counters["Proc"] = static_cast<double>(ppc::util::GetNumProc());
}
}  // namespace detail

template <typename TaskType, typename InType, typename OutType, typename InputProvider>
void RegisterPipelineBenchmark(const std::string &benchmark_name, InputProvider input_provider,
                               const BenchmarkParams &params, const OutputChecker<InType, OutType> &checker) {
  if (detail::ShouldSkipByName(benchmark_name)) {
    return;
  }

  benchmark::RegisterBenchmark(benchmark_name.c_str(),
                               [input_provider, checker, params](benchmark::State &state) {
    int initialized = 0;
    MPI_Initialized(&initialized);
    const bool is_mpi = initialized != 0;
    if constexpr (TaskType::GetStaticTypeOfTask() == ppc::task::TypeOfTask::kMPI) {
      if (!is_mpi) {
        state.SkipWithError("MPI benchmarks skipped: MPI not initialized");
        return;
      }
    }
    for (auto _ : state) {
      auto task = ppc::task::TaskGetter<TaskType, InType>(input_provider());
      task->GetStateOfTesting() = ppc::task::StateOfTesting::kPerf;

      if (is_mpi) {
        MPI_Barrier(MPI_COMM_WORLD);
      }

      const auto t0 = std::chrono::steady_clock::now();
      task->Validation();
      task->PreProcessing();
      task->Run();
      task->PostProcessing();
      const auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

      if (is_mpi) {
        MPI_Barrier(MPI_COMM_WORLD);
      }

      state.SetIterationTime(elapsed);
      benchmark::DoNotOptimize(task->GetOutput());

      if (checker && !checker(task->GetInput(), task->GetOutput())) {
        state.SkipWithError("Output validation failed");
        break;
      }
      if (elapsed > params.max_time_sec) {
        state.SkipWithError("Exceeded PPC_PERF_MAX_TIME");
        break;
      }
    }
    detail::SetCommonCounters(state);
  })
      ->UseManualTime()
      ->Iterations(params.iterations)
      ->Unit(benchmark::kMillisecond);
}

template <typename TaskType, typename InType, typename OutType, typename InputProvider>
void RegisterCoreBenchmark(const std::string &benchmark_name, InputProvider input_provider,
                           const BenchmarkParams &params, const OutputChecker<InType, OutType> &checker) {
  if (detail::ShouldSkipByName(benchmark_name)) {
    return;
  }

  benchmark::RegisterBenchmark(benchmark_name.c_str(),
                               [input_provider, checker, params](benchmark::State &state) {
    int initialized = 0;
    MPI_Initialized(&initialized);
    const bool is_mpi = initialized != 0;
    if constexpr (TaskType::GetStaticTypeOfTask() == ppc::task::TypeOfTask::kMPI) {
      if (!is_mpi) {
        state.SkipWithError("MPI benchmarks skipped: MPI not initialized");
        return;
      }
    }
    auto task = ppc::task::TaskGetter<TaskType, InType>(input_provider());
    task->GetStateOfTesting() = ppc::task::StateOfTesting::kPerf;
    task->Validation();
    task->PreProcessing();

    for (auto _ : state) {
      if (is_mpi) {
        MPI_Barrier(MPI_COMM_WORLD);
      }
      const auto t0 = std::chrono::steady_clock::now();
      task->Run();
      const auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
      if (is_mpi) {
        MPI_Barrier(MPI_COMM_WORLD);
      }
      state.SetIterationTime(elapsed);
      benchmark::DoNotOptimize(task->GetOutput());

      if (elapsed > params.max_time_sec) {
        state.SkipWithError("Exceeded PPC_PERF_MAX_TIME");
        break;
      }
    }

    task->PostProcessing();
    if (checker && !checker(task->GetInput(), task->GetOutput())) {
      state.SkipWithError("Output validation failed");
    }
    detail::SetCommonCounters(state);
  })
      ->UseManualTime()
      ->Iterations(params.iterations)
      ->Unit(benchmark::kMillisecond);
}

template <typename InType, typename OutType, typename... TaskTypes, typename InputProvider, typename Checker>
void RegisterBenchmarksForTasks(const std::string &settings_path, InputProvider input_provider, Checker checker,
                                const BenchmarkParams &params = {}) {
  const auto task_dir =
      std::filesystem::path(settings_path).parent_path().filename().string();  // use directory name as task id
  const auto tasks_type = ReadTasksType(settings_path);

  const auto register_one = [&](auto type_tag) {
    using TaskT = typename decltype(type_tag)::type;
    if constexpr (TaskT::GetStaticTypeOfTask() == ppc::task::TypeOfTask::kMPI) {
      if (!ppc::util::IsUnderMpirun()) {
        return;
      }
      if (tasks_type == "threads") {
        return;  // skip MPI benchmarks for thread-only tasks
      }
    } else {
      if (tasks_type == "processes") {
        // leave seq for processes; skip pure thread impls on process-only tasks?
        if constexpr (TaskT::GetStaticTypeOfTask() != ppc::task::TypeOfTask::kSEQ) {
          return;
        }
      }
    }
    const auto type_prefix = tasks_type.empty() ? "unknown" : tasks_type;
    const auto task_name =
        type_prefix + ":" + task_dir + ":" + ppc::task::GetStringTaskType(TaskT::GetStaticTypeOfTask(), settings_path);

    const auto task_run_name = std::string(ppc::performance::kTaskRunName) + "_" + task_name;
    RegisterCoreBenchmark<TaskT, InType, OutType>(task_run_name, input_provider, params, checker);
  };

  (register_one(std::type_identity<TaskTypes>{}), ...);
}

}  // namespace ppc::util
