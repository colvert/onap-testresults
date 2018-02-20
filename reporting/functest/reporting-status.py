#!/usr/bin/python
#
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import datetime
import os
import jinja2

import reporting.functest.testCase as tc
import reporting.utils.reporting_utils as rp_utils

"""
  Functest reporting status
"""

# Logger
LOGGER = rp_utils.getLogger("ONAP-Functest-Status")

# Initialization
REPORTING_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# init just connection_check to get the list of scenarios
# as all the scenarios run connection_check
HEALTHCHECK_CASE = tc.TestCase("robot_healthcheck", "functest", -1)

# Retrieve the Functest configuration to detect which tests are relevant
# according to the installer, scenario
PERIOD = rp_utils.get_config('general.period')
VERSIONS = rp_utils.get_config('general.versions')
INSTALLERS = rp_utils.get_config('general.installers')
LOG_LEVEL = rp_utils.get_config('general.log.log_level')

TESTCASES = rp_utils.get_config('functest.test_list')

LOGGER.info("*******************************************")
LOGGER.info("*                                         *")
LOGGER.info("*   Generating reporting scenario status  *")
LOGGER.info("*   Data retention: %s days               *", PERIOD)
LOGGER.info("*   Log level: %s                         *", LOG_LEVEL)
LOGGER.info("*   Version: %s                           *", VERSIONS)
LOGGER.info("*   Installers! %s                        *", INSTALLERS)
LOGGER.info("*******************************************")

LOGGER.debug("Functest reporting start")

testcase_results = {}

# For all the versions
for version in VERSIONS:
    # For all the installers
    LOGGER.info("Search for version %s...............", version)
    scenario_directory = "./display/" + version + "/functest/"
    scenario_file_name = scenario_directory + "testcases_history.txt"
    # check that the directory exists, if not create it
    # (first run on new version)
    if not os.path.exists(scenario_directory):
        os.makedirs(scenario_directory)

    # # initiate scenario file if it does not exist
    if not os.path.isfile(scenario_file_name):
        with open(scenario_file_name, "a") as my_file:
            LOGGER.debug("Create scenario file: %s", scenario_file_name)
            my_file.write("date,testcase,installer,detail,score\n")

    for installer in INSTALLERS:
        LOGGER.info("Search for installer %s...............", installer)

        for testcase in TESTCASES:
            LOGGER.info("Search for results for %s", testcase)
            # get the score on the last 10 days
            functest_results = rp_utils.getApiResults(testcase,
                                                      installer,
                                                      version,
                                                      False)
            try:
                nb_tests_period_run = len(functest_results['results'])
                nb_tests_period_ok = rp_utils.getNbtestOk(
                    functest_results['results'])
                # Get the score cosidering the last 4 CI runs
                functest_score = rp_utils.getCaseScore(testcase,
                                                       installer,
                                                       version)
                LOGGER.info("Case score: %s", functest_score)
            except TypeError:
                nb_tests_period_run = 0
                nb_tests_period_ok = 0
                functest_score = 0

            LOGGER.info("Nb tests run over the test window period:%s",
                        nb_tests_period_run)
            LOGGER.info("Nb tests OK over the test window period:%s",
                        nb_tests_period_ok)

            testcase_result = {}
            testcase_result['result_4'] = str(functest_score) + "/3"
            testcase_result['result_period'] = (str(nb_tests_period_ok) +
                                                "/" +
                                                str(nb_tests_period_run))
            testcase_result['result_percent'] = rp_utils.getScenarioPercent(
                nb_tests_period_ok,
                nb_tests_period_run)
            testcase_results[testcase] = testcase_result

            # Save daily results in a file
            with open(scenario_file_name, "a") as f:
                info = (REPORTING_DATE + "," + testcase + "," +
                        installer + "," + testcase_result['result_4'] + "," +
                        str(testcase_result['result_percent']) + "\n")
                f.write(info)

        templateLoader = jinja2.FileSystemLoader(".")
        templateEnv = jinja2.Environment(
            loader=templateLoader, autoescape=True)
        TEMPLATE_FILE = ("./reporting/functest/template"
                         "/index-status-tmpl.html")
        template = templateEnv.get_template(TEMPLATE_FILE)
        outputText = template.render(
            testcase_results=testcase_results,
            installer=installer,
            period=PERIOD,
            version=version,
            date=REPORTING_DATE)
        with open("./display/" + version +
                  "/functest/status-" +
                  installer + ".html", "wb") as fh:
            fh.write(outputText)
            #
            # LOGGER.info("Manage export CSV & PDF")
            # rp_utils.export_csv(scenario_file_name, installer, version)
            # LOGGER.error("CSV generated...")
            #
            # # Generate outputs for export
            # # pdf
            # url_pdf = rp_utils.get_config('general.url')
            # pdf_path = ("./display/" + version +
            #             "/functest/status-" + installer + ".html")
            # pdf_doc_name = ("./display/" + version +
            #                 "/functest/status-" + installer + ".pdf")
            # rp_utils.export_pdf(pdf_path, pdf_doc_name)
            # LOGGER.info("PDF generated...")
