#!/usr/bin/env python3

import os
import sys
import json
import subprocess

from typing import *

NEST = 0
MAKE = ""

class LogNest:
	def __enter__(self):
		global NEST
		NEST += 1

	def __exit__(self, exc_type, exc_value, exc_tb):
		global NEST
		NEST -= 1


def get_make() -> str:
	try:
		if subprocess.run(["gmake", "-v"]).returncode == 0:
			return "gmake"
	except:
		pass
	return "make"

def touch(f: str) -> None:
	with open(f, "w") as f:
		f.write("1")

def log(msg: str, end: str = '\n') -> None:
	global NEST
	print(f"{NEST * 2 * ' '}\x1b[94;1m[log]\x1b[0m \x1b[1m{msg}\x1b[0m", file=sys.stderr, end=end, flush=True)

def warn(msg: str, end: str = '\n') -> None:
	global NEST
	print(f"{NEST * 2 * ' '}\x1b[93;1m[wrn]\x1b[0m \x1b[1m{msg}\x1b[0m", file=sys.stderr, end=end, flush=True)

def error(msg: str, end: str = '\n') -> None:
	global NEST
	print(f"{NEST * 2 * ' '}\x1b[91;1m[err]\x1b[0m \x1b[1m{msg}\x1b[0m", file=sys.stderr, end=end, flush=True)

def build_tests(results: list[dict[str, str]]) -> list[dict[str, str]]:
	if not os.path.exists(".configured"):
		log(f"Configuring")

		cflags = "-DVERBOSE=10"
		ldflags = ""
		if sys.platform == "darwin":
			# sadgely, force an "librt.a" file to appear here
			with open("asdf.c", "w") as asdf:
				asdf.write("void _____________() { }")
			subprocess.run(["cc", "-o", "asdf.o", "-c", "asdf.c"], check=True)
			subprocess.run(["ar", "rcs", "librt.a", "asdf.o"], check=True)
			os.remove("asdf.o")
			os.remove("asdf.c")

			ldflags = f"LDFLAGS='-L{os.getcwd()}'"

			# sigrtmin doesn't exist on macos; use sigusr2
			cflags += " -DSIGRTMIN=SIGUSR2 -Wno-deprecated-declarations"


		subprocess.run([f"./configure CFLAGS='{cflags}' {ldflags}"], shell=True, check=True)
		touch(".configured")

	log(f"Building tests")
	with LogNest():
		output = subprocess.run([MAKE, "-j1", "--no-print-directory"], check=True, capture_output=True).stdout

		i: int = 0
		cur_out: str = ""
		lines = output.decode().splitlines()

		while i < len(lines):
			if "compile FAILED; SKIPPING" in lines[i]:
				parts = lines[i].split()
				error(f"failed: {parts[0]}")
				results.append({
					"name": parts[0],
					"result": "NO_COMPILE",
					"output": cur_out
				})
				cur_out = ""
			elif "compile PASSED" in lines[i]:
				cur_out = ""
			else:
				cur_out += lines[i] + "\n"
			i += 1

	return results


def parse_logfile(path: str, results: list[dict[str, str]]) -> None:
	with open(path, "r") as f:
		lines = list(filter(lambda x: len(x) > 0, map(lambda x: x.strip(), f.read().splitlines())))
		i: int = 0
		while i < len(lines):
			if "execution: " in lines[i]:
				parts = lines[i].split(": ")
				test_name = parts[0].strip()
				test_result = parts[2].strip()
				test_output: str = ""

				i += 1
				while i < len(lines):
					if "execution: " in lines[i]:
						break
					test_output += f"{lines[i]}\n"
					i += 1

				results.append({
					"name": test_name,
					"result": test_result,
					"output": test_output,
				})

			else:
				i += 1

def run_test_set(name: str, results: list[dict[str, str]], skip: list[str]) -> None:
	log(f"Running {name} tests")
	with LogNest():
		# find the actual folder containing the test executables
		for r, ds, fs in os.walk(f"{name}"):
			have_tests = False
			for f in fs:
				if f.endswith(".run-test"):
					have_tests = True
					break

			if not have_tests:
				continue

			rname = '/'.join(os.path.relpath(r, ".").split('/')[1:])
			if any(s in skip for s in r.split('/')):
				warn(f"skipping {rname}")
				continue

			log(f"{rname}")
			subprocess.run([MAKE, "--no-print-directory", "-C", f"{r}", "test"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
			if os.path.exists(f"{r}/logfile"):
				parse_logfile(f"{r}/logfile", results)
			else:
				with LogNest():
					warn(f"{rname}: no logfile")


def run_tests(results: list[dict[str, str]]) -> list[dict[str, str]]:
	log("Deleting existing log files")
	for r, ds, fs in os.walk("."):
		for f in fs:
			if f == "logfile" and os.path.isfile(f"{r}/{f}"):
				os.remove(f"{r}/{f}")

	run_test_set("functional", results, [])
	run_test_set("conformance", results, [] if sys.platform != "darwin" else [
		"mmap"
	])

	return results



def print_schema_v2(obj: dict[str, Any], only: Optional[str] = None) -> None:
	test_objs = obj["tests"]

	total_tests = len(test_objs)
	passed_tests = sum(map(lambda x: 1, filter(lambda x: x["result"] == "PASS", test_objs)))
	failed_tests = total_tests - passed_tests

	print(f"Total:  {total_tests}")
	print(f"Passed: {passed_tests}")
	print(f"Failed: {failed_tests}")
	print(f"")

	def filter_results(tests: list[dict[str, Any]], result: str) -> list[dict[str, Any]]:
		return list(filter(lambda x: x["result"] == result, tests))

	def print_test_list(tests: list[dict[str, Any]], category: str) -> None:
		if only is not None and category != only:
			return

		print(f"{category} ({len(tests)}):")
		for t in tests:
			print(f"  {t['name']}")
			if "output" in t and len(t["output"]) > 0:
				for l in t["output"].splitlines():
					print(f"    {l}")
				print("")

	print_test_list(filter_results(test_objs, "NO_COMPILE"), "NO_COMPILE")
	print_test_list(filter_results(test_objs, "UNRESOLVED"), "UNRESOLVED")
	print_test_list(filter_results(test_objs, "FAILED"), "FAILED")
	print_test_list(filter_results(test_objs, "UNTESTED"), "UNTESTED")
	print_test_list(filter_results(test_objs, "UNSUPPORTED"), "UNSUPPORTED")
	print_test_list(filter_results(test_objs, "SIGNALED"), "SIGNALED")
	print_test_list(filter_results(test_objs, "HUNG"), "HUNG")



def print_schema_v1(obj: dict[str, Any], only: Optional[str] = None) -> None:
	total_tests = len(obj.keys())
	passed_tests = sum(map(lambda x: 1, filter(lambda x: x[1]["result"] == "PASS", obj.items())))
	failed_tests = total_tests - passed_tests

	print(f"Total:  {total_tests}")
	print(f"Passed: {passed_tests}")
	print(f"Failed: {failed_tests}")
	print(f"")

	def filter_results(tests: dict[str, Any], result: str) -> list[tuple[str, dict[str, Any]]]:
		return list(filter(lambda x: x[1]["result"] == result, tests.items()))

	def print_test_list(tests: list[tuple[str, dict[str, Any]]], category: str) -> None:
		if only is not None and category != only:
			return

		print(f"{category} ({len(tests)}):")
		for t, r in tests:
			print(f"  {t}")
			if "output" in r and len(r["output"]) > 0:
				for l in r["output"].splitlines():
					print(f"    {l}")
				print("")

	print_test_list(filter_results(obj, "NO_COMPILE"), "NO_COMPILE")
	print_test_list(filter_results(obj, "UNRESOLVED"), "UNRESOLVED")
	print_test_list(filter_results(obj, "FAILED"), "FAILED")
	print_test_list(filter_results(obj, "UNTESTED"), "UNTESTED")
	print_test_list(filter_results(obj, "UNSUPPORTED"), "UNSUPPORTED")
	print_test_list(filter_results(obj, "SIGNALED"), "SIGNALED")
	print_test_list(filter_results(obj, "HUNG"), "HUNG")



def cmd_report(json_file: str, only: Optional[str] = None) -> None:
	with open(json_file, "r") as f:
		obj = json.load(f)

		if obj.get("schema", 1) == 1:
			print_schema_v1(obj, only)
		elif obj["schema"] == 2:
			print_schema_v2(obj)
		else:
			error(f"Unsupported schema version '{obj['schema']}'")


def cmd_patch(test_dir: str) -> None:
	# patch things if necessary
	if os.path.exists("fixes.patch") and not os.path.exists(".patched"):
		log(f"Patching files")
		subprocess.run(["patch", "-Nsp0", "-d", test_dir], input=open("fixes.patch", "rb").read(), check=True)
		touch(".patched")

def cmd_build(test_dir: str) -> list[dict[str, Any]]:
	old_dir = os.getcwd()
	os.chdir(test_dir)

	results = build_tests([])

	os.chdir(old_dir)
	return results

def cmd_test(test_dir: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
	old_dir = os.getcwd()
	os.chdir(test_dir)

	results = run_tests(results)

	os.chdir(old_dir)
	return results


def cmd_save(report_file: str, results: list[dict[str, Any]]) -> None:
	log("Saving results")
	with open(report_file, "w") as f:
		f.write(json.dumps({"schema": 2, "tests": results}, indent=2))





if __name__ == "__main__":
	if len(sys.argv) < 3:
		print(f"usage: ./run.py <test|report> <report_file>")
		sys.exit(0)

	MAKE = get_make()
	TESTSUITE_DIR = "testcases/open_posix_testsuite"

	cmd = sys.argv[1]
	report_file = sys.argv[2]

	if cmd == "test":
		cmd_patch(TESTSUITE_DIR)
		r = cmd_build(TESTSUITE_DIR)
		r = cmd_test(TESTSUITE_DIR, r)
		cmd_save(report_file, r)
		cmd_report(report_file)

	elif cmd == "report":
		cmd_report(report_file)

	elif cmd == "build":
		cmd_patch(TESTSUITE_DIR)
		r = cmd_build(TESTSUITE_DIR)
		cmd_save(report_file, r)
		cmd_report(report_file)

	else:
		print(f"Invalid command '{cmd}'")
		sys.exit(1)
