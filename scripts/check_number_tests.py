import sys
import subprocess

tests_executable_file = sys.argv[1]
list_of_args = [tests_executable_file, "--gtest_list_tests", "--gtest_color=no"]
proc = subprocess.Popen(list_of_args, stdout=subprocess.PIPE)

lines = []
index_lines = []
i = 0
while True:
    line = proc.stdout.readline()
    if not line:
        break
    lines.append(line.decode("utf-8").rstrip())
    index_lines.append(i)
    i += 1

list_of_number_tests = []
tmp_index = len(lines)
tmp_name_test = ""
for line, index in zip(lines, index_lines):
    if line[len(line) - 1] == ".":
        list_of_number_tests.append([tmp_name_test, abs(index - tmp_index) - 1])
        tmp_index = index
        tmp_name_test = line
list_of_number_tests.append([tmp_name_test, abs(len(lines) - tmp_index) - 1])

for res in list_of_number_tests:
    if res[1] < 5:
        print("ERROR:", res[0], "has", res[1], "tests")
        print("Project need to has more than or equal 5 tests")
        sys.exit(1)
    else:
        if res[0] != "":
            print("Project", res[0], "has", res[1], "tests: SUCCESS")