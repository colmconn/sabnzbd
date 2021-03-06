#!/usr/bin/python3 -OO
# Copyright 2007-2020 The SABnzbd-Team <team@sabnzbd.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""
tests.test_functional_downloads - Test the downloading flow
"""

from tests.testhelper import *


class TestDownloadFlow(SABnzbdBaseTest):
    def is_server_configured(self):
        """ Check if the wizard was already performed.
            If not: run the wizard!
        """
        with open(os.path.join(SAB_CACHE_DIR, "sabnzbd.ini"), "r") as config_file:
            if SAB_NEWSSERVER_HOST not in config_file.read():
                self.start_wizard()

    def start_wizard(self):
        # Language-selection
        self.open_page("http://%s:%s/sabnzbd/wizard/" % (SAB_HOST, SAB_PORT))
        self.selenium_wrapper(self.driver.find_element_by_id, "en").click()
        self.selenium_wrapper(self.driver.find_element_by_css_selector, ".btn.btn-default").click()

        # Fill server-info
        self.no_page_crash()
        host_inp = self.selenium_wrapper(self.driver.find_element_by_name, "host")
        host_inp.clear()
        host_inp.send_keys(SAB_NEWSSERVER_HOST)

        # This will fail if the translations failed to compile!
        self.selenium_wrapper(self.driver.find_element_by_partial_link_text, "Advanced Settings").click()

        # Change port
        port_inp = self.selenium_wrapper(self.driver.find_element_by_name, "port")
        port_inp.clear()
        port_inp.send_keys(SAB_NEWSSERVER_PORT)

        # Test server-check
        self.selenium_wrapper(self.driver.find_element_by_id, "serverTest").click()
        self.wait_for_ajax()
        assert "Connection Successful" in self.selenium_wrapper(self.driver.find_element_by_id, "serverResponse").text

        # Final page done
        self.selenium_wrapper(self.driver.find_element_by_id, "next-button").click()
        self.no_page_crash()
        check_result = self.selenium_wrapper(self.driver.find_element_by_class_name, "quoteBlock").text
        assert "http://%s:%s/sabnzbd" % (SAB_HOST, SAB_PORT) in check_result

        # Go to SAB!
        self.selenium_wrapper(self.driver.find_element_by_css_selector, ".btn.btn-success").click()
        self.no_page_crash()

    def add_test_nzb(self, nzb_dir, file_output):
        # Create NZB
        nzb_path = create_nzb(nzb_dir)

        # Add NZB
        test_job_name = "testfile_%s" % time.time()
        api_result = get_api_result("addlocalfile", extra_arguments={"name": nzb_path, "nzbname": test_job_name})
        assert api_result["status"]

        # Remove NZB-file
        os.remove(nzb_path)

        # See how it's doing
        self.open_page("http://%s:%s/sabnzbd/" % (SAB_HOST, SAB_PORT))

        # We wait for 60 seconds to let it complete
        for _ in range(60):
            try:
                # Locate status of our job
                status_text = self.driver.find_element_by_xpath(
                    '//div[@id="history-tab"]//tr[td/div/span[contains(text(), "%s")]]/td[contains(@class, "status")]'
                    % test_job_name
                ).text
                if status_text == "Completed":
                    break
                else:
                    time.sleep(1)
            except WebDriverException:
                time.sleep(1)
        else:
            self.fail("Download did not complete")

        # Check if the expected file exists on disk
        file_to_find = os.path.join(SAB_COMPLETE_DIR, test_job_name, file_output)
        assert os.path.exists(file_to_find)

    def test_download_basic_rar5(self):
        self.is_server_configured()
        self.add_test_nzb("basic_rar5", "testfile.bin")

    def test_download_zip(self):
        self.is_server_configured()
        self.add_test_nzb("test_zip", "testfile.bin")

    def test_download_7zip(self):
        self.is_server_configured()
        self.add_test_nzb("test_7zip", "testfile.bin")

    def test_download_passworded(self):
        self.is_server_configured()
        self.add_test_nzb("test_passworded{{secret}}", "testfile.bin")

    def test_download_unicode_made_on_windows(self):
        self.is_server_configured()
        self.add_test_nzb("test_win_unicode", "frènch_german_demö.bin")

    def test_download_fully_obfuscated(self):
        # This is also covered by a unit test but added to test full flow
        self.is_server_configured()
        self.add_test_nzb("obfuscated_single_rar_set", "100k.bin")

    @pytest.mark.xfail(reason="https://github.com/sabnzbd/sabnzbd/issues/1509")
    def test_download_unicode_rar(self):
        self.is_server_configured()
        self.add_test_nzb("unicode_rar", "我喜欢编程.bin")
