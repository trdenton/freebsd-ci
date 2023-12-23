#!/usr/bin/env python3

'''
Basic script for converting json output to JUnit format
'''

# requires pip install junit-xml
# or, pkg inst py32-junit-xml
import junit_xml
import json
import argparse

def get_class_name_from_path(path:str) -> str:
    return "/".join((path.split('/')[0:2]))

def process_format(json_input_file:str, junit_output_file:str):
    data = {}
    test_results=[]
    with open(json_input_file) as jsonf:
            data = json.load(jsonf)
    for i in data['tests']:
        classname = get_class_name_from_path(i['name'])
        tc = junit_xml.TestCase(name=i['name'], classname=classname, stdout=i['output'])

        result = i['result']
        if result == "PASS":
            pass
        elif result == "FAILED":
            tc.add_fail_info(result)
        elif result in ["UNTESTED", "UNSUPPORTED"]:
            tc.add_skipped_info(result)
        else:
            tc.add_error_info(result)

        test_results.append(tc)

    ts = junit_xml.TestSuite("My test suite", test_results);
    with open(junit_output_file,'w') as junitf:
        junitf.write(junit_xml.TestSuite.to_xml_string([ts]))

if __name__=="__main__":
    parser = argparse.ArgumentParser(prog='format_junit')
    parser.add_argument('json_input_file')
    parser.add_argument('junit_output_file')
    args = parser.parse_args()
    process_format(args.json_input_file, args.junit_output_file)

