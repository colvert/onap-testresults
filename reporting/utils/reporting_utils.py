#!/usr/bin/python
#
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import logging
import json
import os
import requests
import pdfkit
import yaml


# ----------------------------------------------------------
#
#               YAML UTILS
#
# -----------------------------------------------------------
def get_parameter_from_yaml(parameter, config_file):
    """
    Returns the value of a given parameter in file.yaml
    parameter must be given in string format with dots
    Example: general.openstack.image_name
    """
    with open(config_file) as my_file:
        file_yaml = yaml.safe_load(my_file)
    my_file.close()
    value = file_yaml
    for element in parameter.split("."):
        value = value.get(element)
        if value is None:
            raise ValueError("The parameter %s is not defined in"
                             " reporting.yaml" % parameter)
    return value


def get_config(parameter):
    """
    Get configuration parameter from yaml configuration file
    """
    yaml_ = os.environ["CONFIG_REPORTING_YAML"]
    return get_parameter_from_yaml(parameter, yaml_)


# ----------------------------------------------------------
#
#               LOGGER UTILS
#
# -----------------------------------------------------------
def getLogger(module):
    """
    Get Logger
    """
    log_formatter = logging.Formatter("%(asctime)s [" +
                                      module +
                                      "] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger()
    log_file = get_config('general.log.log_file')
    log_level = get_config('general.log.log_level')

    file_handler = logging.FileHandler("{0}/{1}".format('.', log_file))
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
    logger.setLevel(log_level)
    return logger


# ----------------------------------------------------------
#
#               REPORTING UTILS
#
# -----------------------------------------------------------
def getApiResults(case, installer, version, criteria):
    """
    Get Results by calling the API

    criteria is to consider N last results for the case success criteria
    """
    results = json.dumps([])
    # to remove proxy (to be removed at the end for local test only)
    # proxy_handler = urllib2.ProxyHandler({})
    # opener = urllib2.build_opener(proxy_handler)
    # urllib2.install_opener(opener)
    # url = "http://127.0.0.1:8000/results?case=" + case + \
    #       "&period=30&installer=" + installer
    period = get_config('general.period')
    url_base = get_config('testapi.url')
    nb_tests = get_config('general.nb_iteration_tests_success_criteria')

    url = (url_base + "?case=" + case +
           "&period=" + str(period) + "&installer=" + installer +
           "&version=" + version)
    if criteria:
        url += "&last=" + str(nb_tests)
    proxy = get_config('general.proxy')
    response = requests.get(url, proxies=proxy)

    try:
        results = json.loads(response.content)
    except Exception:  # pylint: disable=broad-except
        print "Error when retrieving results form API"

    return results


def getNbtestOk(results):
    """
    based on default value (PASS) count the number of test OK
    """
    nb_test_ok = 0
    for my_result in results:
        for res_k, res_v in my_result.iteritems():
            try:
                if "PASS" in res_v:
                    nb_test_ok += 1
            except TypeError:
                # print "Cannot retrieve test status"
                pass
    return nb_test_ok


def getCaseScore(testCase, installer, version):
    """
    Get Result  for a given Functest Testcase
    """
    # retrieve raw results
    results = getApiResults(testCase, installer, version, True)
    # let's concentrate on test results only
    test_results = results['results']

    # if results found, analyze them
    if test_results is not None:
        test_results.reverse()

        scenario_results = []

        # print " ---------------- "
        # print test_results
        # print " ---------------- "
        # print "nb of results:" + str(len(test_results))

        for res_r in test_results:
            scenario_results.append({res_r["start_date"]: res_r["criteria"]})
        # sort results
        scenario_results.sort()
        # 4 levels for the results
        # 3: 4+ consecutive runs passing the success criteria
        # 2: <4 successful consecutive runs but passing the criteria
        # 1: close to pass the success criteria
        # 0: 0% success, not passing
        # -1: no run available
        test_result_indicator = 0
        nb_test_ok = getNbtestOk(scenario_results)

        # print "Nb test OK (last 10 days):"+ str(nb_test_ok)
        # check that we have at least 4 runs
        if len(scenario_results) < 1:
            # No results available
            test_result_indicator = 0
        elif nb_test_ok < 1:
            test_result_indicator = 0
        elif nb_test_ok < 2:
            test_result_indicator = 1
        else:
            # Test the last 4 run
            if len(scenario_results) > 3:
                last_4_run_results = scenario_results[-4:]
                nb_test_ok_last_4 = getNbtestOk(last_4_run_results)
                # print "Nb test OK (last 4 run):"+ str(nb_test_ok_last_4)
                if nb_test_ok_last_4 > 3:
                    test_result_indicator = 3
                else:
                    test_result_indicator = 2
            else:
                test_result_indicator = 2
    return test_result_indicator


def getScenarioPercent(scenario_score, scenario_criteria):
    """
    Get success rate of the scenario (in %)
    """
    try:
        score = float(scenario_score) / float(scenario_criteria) * 100
    except ZeroDivisionError:
        score = 0
    return score
# ----------------------------------------------------------
#
#               Export
#
# -----------------------------------------------------------


def export_csv(scenario_file_name, installer, version):
    """
    Generate sub files based on scenario_history.txt
    """
    scenario_installer_file_name = ("./display/" + version +
                                    "/functest/scenario_history_" +
                                    installer + ".csv")
    scenario_installer_file = open(scenario_installer_file_name, "a")
    with open(scenario_file_name, "r") as scenario_file:
        scenario_installer_file.write("date,scenario,installer,detail,score\n")
        for line in scenario_file:
            if installer in line:
                scenario_installer_file.write(line)


def generate_csv(scenario_file):
    """
    Generate sub files based on scenario_history.txt
    """
    import shutil
    csv_file = scenario_file.replace('txt', 'csv')
    shutil.copy2(scenario_file, csv_file)


def export_pdf(pdf_path, pdf_doc_name):
    """
    Export results to pdf
    """
    try:
        pdfkit.from_file(pdf_path, pdf_doc_name)
    except IOError:
        print "Error but pdf generated anyway..."
    except Exception:  # pylint: disable=broad-except
        print "impossible to generate PDF"
