import os
import subprocess
import platform
from pathlib import Path


def init_cmd_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--running-type",
        required=True,
        choices=["threads", "processes", "performance", "performance-list"],
        help="Specify the execution mode. Choose 'threads' for multithreading or 'processes' for multiprocessing."
    )
    parser.add_argument(
        "--additional-mpi-args",
        required=False,
        default="",
        help="Additional MPI arguments to pass to the mpirun command (optional)."
    )
    args = parser.parse_args()
    _args_dict = vars(args)
    return _args_dict


class PPCRunner:
    def __init__(self):
        self.work_dir = None
        self.valgrind_cmd = "valgrind --error-exitcode=1 --leak-check=full --show-leak-kinds=all"

        if platform.system() == "Windows":
            self.mpi_exec = "mpiexec"
        else:
            self.mpi_exec = "mpirun"

    @staticmethod
    def __get_project_path():
        script_path = Path(__file__).resolve()  # Absolute path of the script
        script_dir = script_path.parent  # Directory containing the script
        return script_dir.parent

    def setup_env(self):
        if (Path(self.__get_project_path()) / "install").exists():
            self.work_dir = Path(self.__get_project_path()) / "install" / "bin"
        else:
            self.work_dir = Path(self.__get_project_path()) / "build" / "bin"

    @staticmethod
    def __run_exec(command):
        result = subprocess.run(command, shell=True, env=os.environ)
        if result.returncode != 0:
            raise Exception(f"Subprocess return {result.returncode}.")

    @staticmethod
    def __get_gtest_settings(repeats_count):
        command = f"--gtest_repeat={repeats_count} "
        command += "--gtest_recreate_environments_when_repeating "
        command += "--gtest_color=0 "
        return command

    def run_threads(self):
        if platform.system() == "Linux" and not os.environ.get("PPC_ASAN_RUN"):
            self.__run_exec(f"{self.valgrind_cmd} {self.work_dir / 'seq_func_tests'} {self.__get_gtest_settings(1)}")
            self.__run_exec(f"{self.valgrind_cmd} {self.work_dir / 'stl_func_tests'} {self.__get_gtest_settings(1)}")

        self.__run_exec(f"{self.work_dir / 'seq_func_tests'} {self.__get_gtest_settings(3)}")
        self.__run_exec(f"{self.work_dir / 'stl_func_tests'} {self.__get_gtest_settings(3)}")
        self.__run_exec(f"{self.work_dir / 'tbb_func_tests'} {self.__get_gtest_settings(3)}")
        self.__run_exec(f"{self.work_dir / 'omp_func_tests'} {self.__get_gtest_settings(3)}")

    def run_core(self):
        if platform.system() == "Linux" and not os.environ.get("PPC_ASAN_RUN"):
            self.__run_exec(f"{self.valgrind_cmd} {self.work_dir / 'core_func_tests'} {self.__get_gtest_settings(1)}")

        self.__run_exec(f"{self.work_dir / 'core_func_tests'} {self.__get_gtest_settings(1)}")

    def run_processes(self, additional_mpi_args):
        PPC_NUM_PROC = os.environ.get("PPC_NUM_PROC")
        if PPC_NUM_PROC is None:
            raise EnvironmentError("Required environment variable 'PPC_NUM_PROC' is not set.")

        mpi_running = f"{self.mpi_exec} {additional_mpi_args} -np {PPC_NUM_PROC}"
        if not os.environ.get("PPC_ASAN_RUN"):
            self.__run_exec(f"{mpi_running} {self.work_dir / 'all_func_tests'} {self.__get_gtest_settings(10)}")
            self.__run_exec(f"{mpi_running} {self.work_dir / 'mpi_func_tests'} {self.__get_gtest_settings(10)}")

    def run_performance(self):
        if not os.environ.get("PPC_ASAN_RUN"):
            PPC_NUM_PROC = os.environ.get("PPC_NUM_PROC")
            if PPC_NUM_PROC is None:
                raise EnvironmentError("Required environment variable 'PPC_NUM_PROC' is not set.")
            mpi_running = f"{self.mpi_exec} -np {PPC_NUM_PROC}"
            self.__run_exec(f"{mpi_running} {self.work_dir / 'all_perf_tests'} {self.__get_gtest_settings(1)}")
            self.__run_exec(f"{mpi_running} {self.work_dir / 'mpi_perf_tests'} {self.__get_gtest_settings(1)}")

        self.__run_exec(f"{self.work_dir / 'omp_perf_tests'} {self.__get_gtest_settings(1)}")
        self.__run_exec(f"{self.work_dir / 'seq_perf_tests'} {self.__get_gtest_settings(1)}")
        self.__run_exec(f"{self.work_dir / 'stl_perf_tests'} {self.__get_gtest_settings(1)}")
        self.__run_exec(f"{self.work_dir / 'tbb_perf_tests'} {self.__get_gtest_settings(1)}")

    def run_performance_list(self):
        for task_type in ["all", "mpi", "omp", "seq", "stl", "tbb"]:
            self.__run_exec(f"{self.work_dir / f'{task_type}_perf_tests'} --gtest_list_tests")


if __name__ == "__main__":
    args_dict = init_cmd_args()

    ppc_runner = PPCRunner()
    ppc_runner.setup_env()

    if args_dict["running_type"] in ["threads", "processes"]:
        ppc_runner.run_core()

    if args_dict["running_type"] == "threads":
        ppc_runner.run_threads()
    elif args_dict["running_type"] == "processes":
        ppc_runner.run_processes(args_dict["additional_mpi_args"])
    elif args_dict["running_type"] == "performance":
        ppc_runner.run_performance()
    elif args_dict["running_type"] == "performance-list":
        ppc_runner.run_performance_list()
    else:
        raise Exception("running-type is wrong!")
