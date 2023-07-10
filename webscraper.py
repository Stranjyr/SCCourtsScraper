from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import logging
from datetime import datetime, date, timedelta
from multiprocessing.pool import ThreadPool
import mongo_db_connect

login_url = "https://apps.sccourts.org/logon/LogonPoint/tmindex.html"
firefox_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
username = ""
password = ""


class DatabaseAgent():

    def __init__(self, database_name, collection_name, thread_count):
        self.db = mongo_db_connect.get_database(database_name)
        self.collect = mongo_db_connect.add_collection(self.db,
                                                       collection_name)
        self.max_threads = thread_count
        self.pool = ThreadPool(processes=thread_count)

        logging.basicConfig(filename="logs/" + datetime.now()+".log", level=logging.DEBUG)
        logging.info("Started Database Agent")
    
    ## Helper Functions for threads
    def setup_webdriver(self, headless: bool = False):
        options = Options()
        options.binary_location = firefox_location
        options.headless = headless
        return webdriver.Firefox(options=options)

    def search_caselist_thead(self, name: str, case_list: list, bucket_size: int, headless: bool = False):
        logging.info("Started thread: " + name)
        driver = self.setup_webdriver(headless)
        scraper = IndexScraper(driver, name)
        scraper.login()
        num_iterations = int(len(case_list)/bucket_size)+1
        for iteration in range(num_iterations):
            logging.info("Thread {}: {}/{}".format(name, iteration+1, num_iterations))
            bucket_start = iteration*bucket_size
            bucket_end = min((iteration+1)*bucket_size, len(case_list))
            try:
                orig_handle = scraper.openCaseList(case_list=case_list[bucket_start:bucket_end], searchFirst=True)
                case_info = scraper.readAllOpenPages(orig_handle)
                mongo_db_connect.add_list(self.collect, case_info)
            except WebDriverException as e:
                logging.error("Error in Thread" + name +
                              ": case number in: " + case_list[bucket_start:bucket_end] +
                              "Error : " + str(e))
                #get back to a known state
                scraper.driver.quit()
                scraper.login()
        logging.info("Thread {} finished".format(name))

    def search_daterange_thread(self, name:str, start_date: date, end_date: date, court: str, headless: bool = True):
        logging.info("Started thread: " + name)
        driver = self.setup_webdriver(headless)
        scraper = IndexScraper(driver, name)
        scraper.login()
        curr_date = start_date
        while curr_date <= end_date:
            date_string = curr_date.strftime("%m/%d/%Y")
            logging.info("Thread {}: {}/{}".format(name, date_string, end_date.strftime("%m/%d/%Y")))
            try:
                case_list = scraper.searchAllCasesInDateRange(date_string, date_string, court)
                orig_window = scraper.openCaseList(case_list, searchFirst=False)
                case_info = scraper.readAllOpenPages(orig_window)
                mongo_db_connect.add_list(self.collect, case_info)
            except WebDriverException as e:
                logging.error("Error in Thread" + name +
                              ": date: " + date_string +
                              "Error : " + str(e))
                #get back to a known state
                scraper.driver.quit()
                scraper.login()
            curr_date += timedelta(days=1)
        logging.info("Thread {} finished".format(name))

    def caselist_thread_controller(self, case_list: list, bucket_size: int, headless: bool = False):
        logging.info("Starting Caselist Controller")
        case_per_thread = int(len(case_list)/self.max_threads)
        logging.info("{} cases per thead".foramt(case_per_thread))
        logging.info("{} cases total".foramt(len(case_list)))
        case_overflow = len(case_list)%self.max_threads
        last_start_index = 0
        thread_args_list = []
        for thread_index in self.max_threads:
            end_index = last_start_index + case_per_thread
            if case_overflow > thread_index:
                end_index += 1
                thread_args_list.append(("Thread {}".format(thread_index),
                                         case_list[last_start_index:end_index],
                                         bucket_size,
                                         headless))
        result = self.pool.map_async(self.search_caselist_thead, thread_args_list)
        result.wait()

    def daterange_thread_controller(self, thread_breakup: timedelta,
                                    start_date: date, end_date: date,
                                    courts: list, headless: bool):
        logging.info("Starting Date Controller")
        curr_date = start_date
        thread_args_list = []
        while curr_date <= end_date:
            next_date = max(curr_date + thread_breakup, end_date)
            for court in courts:
                thread_args_list.append(("Thread {}_{}_{}".format(curr_date.strftime('%m/%d/%Y'),
                                                                  court),
                                         curr_date,
                                         next_date,
                                         court,
                                         headless))
            curr_date += thread_breakup
        result = self.pool.map_async(self.search_daterange_thread, thread_args_list)
        result.wait()


class IndexScraper():
    def __init__(self, driver: webdriver.Firefox, run_name: str, timeout: int = 10000):
        self.driver = driver
        self.run_name = run_name
        self.timeout = timeout

    def login(self):
        self.driver.get(login_url)
        # self.driver.implicitly_wait(0.5)
        with open("logininfo.txt", 'r') as log_info:
            username = log_info.readline().strip()
            password = log_info.readline().strip()
        WebDriverWait(self.driver, self.timeout).until(EC.presence_of_element_located((By.NAME, "login")))
        name_field = self.driver.find_element(by=By.NAME, value="login")
        password_field = self.driver.find_element(by=By.NAME, value="passwd")
        login_btn = self.driver.find_element(by=By.ID, value="nsg-x1-logon-button")
        name_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()
        WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#allAppsBtn'))).click()
        WebDriverWait(self.driver, self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.storeapp:nth-child(3) > a:nth-child(2) > div:nth-child(4) > p:nth-child(1)")))

        crim_justice = self.driver.find_element(by=By.CSS_SELECTOR, value="li.storeapp:nth-child(3) > a:nth-child(2) > div:nth-child(4) > p:nth-child(1)")
        crim_justice.click()

        WebDriverWait(self.driver, self.timeout).until(EC.number_of_windows_to_be(2))

        self.switch_to_other_window(self.driver.current_window_handle, True)
        WebDriverWait(self.driver, self.timeout).until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$TextBoxCaseNumber")))
        new_base_url = self.driver.current_url
        return new_base_url

    def searchForCaseByNumber(self, casenum: str):
        WebDriverWait(self.driver, self.timeout).until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$TextBoxCaseNumber")))
        text_box = self.driver.find_element(by=By.NAME, value="ctl00$ContentPlaceHolder1$TextBoxCaseNumber")

        text_box.clear()
        text_box.send_keys(casenum)
        WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable((By.NAME, "ctl00$ContentPlaceHolder1$ButtonSearch"))).click()
        return casenum

    def searchAllCasesInDateRange(self, start_date: str, end_date: str, court_type: str = "Columbia Municipal Court"):
        WebDriverWait(self.driver, self.timeout).until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_DropDownListAgencies")))
        court_select = Select(self.driver.find_element(by=By.ID, value = "ctl00_ContentPlaceHolder1_DropDownListAgencies"))
        court_select.select_by_visible_text(court_type)
        WebDriverWait(self.driver, self.timeout).until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_DropDownListDateFilter")))
        court_select = Select(self.driver.find_element(by=By.ID, value = "ctl00_ContentPlaceHolder1_DropDownListDateFilter"))
        court_select.select_by_visible_text("Case Filed")

        WebDriverWait(self.driver, self.timeout).until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_TextBoxDateFrom")))
        from_box = self.driver.find_element(by=By.ID, value="ctl00_ContentPlaceHolder1_TextBoxDateFrom")
        from_box.clear()
        from_box.send_keys(start_date)

        WebDriverWait(self.driver, self.timeout).until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_TextBoxDateTo")))
        to_box = self.driver.find_element(by=By.ID, value="ctl00_ContentPlaceHolder1_TextBoxDateTo")
        to_box.clear()
        to_box.send_keys(end_date)

        WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable((By.NAME, "ctl00$ContentPlaceHolder1$ButtonSearch"))).click()

        case_names = []
        sentencing_table = self.driver.find_elements(by=By.XPATH, 
                                        value="/html/body/form/div[3]/div/div[2]/div[5]/div/table/tbody/tr")
        row_count = len(sentencing_table)
        for i in range(2, row_count+1):
            row_value = "/html/body/form/div[3]/div/div[2]/div[5]/div/table/tbody/tr[{}]/".format(i)
            case_names.append(self.driver.find_element(by=By.XPATH, value=row_value+"td[3]/a").text)
        return case_names

    def openCase(self, casenum: str):
        orig_window = self.driver.current_window_handle
        WebDriverWait(self.self.driver, self.timeout).until(EC.element_to_be_clickable((By.LINK_TEXT, casenum))).click()
        return orig_window

    def readAllOpenPages(self, original_handle: str):
        case_info_list = []
        while len(self.driver.window_handles) > 1:
            self.switch_to_other_window(self.driver, original_handle)
            case_info_list.append(self.get_all_info(self.driver))
            self.driver.close()
        self.driver.switch_to.window(original_handle)
        return case_info_list

    def openCaseList(self, case_list: list, searchFirst: bool):
        for casenum in case_list:
            if searchFirst:
                self.searchForCaseByNumber(casenum)
            orig_window = self.openCase(casenum)
            self.driver.switch_to.window(orig_window)
        return orig_window

    # Helper Methods
    def get_case_parties_info(self, section_count):
        parties = {}
        parties['all_parties'] = []
        name_table = self.driver.find_elements(by=By.XPATH,
                                               value="/html/body/form/div[3]/" +
                                                     "div/div[2]/div[4]/div/" +
                                                     "div[{}]/span[2]/table/tbody/tr".format(section_count))
        row_count = len(name_table)
        for i in range(2, row_count+1):  
            curr_party = {}
            row_value = ("/html/body/form/div[3]/" +
                         "div/div[2]/div[4]/div/" +
                         "div[{}]/span[2]/table/tbody/tr[{}]/").format(section_count, i)
            curr_party['name'] = self.driver.find_element(by=By.XPATH,
                                                     value=row_value+"td[1]").text
            curr_party['address'] = self.driver.find_element(by=By.XPATH,
                                                        value=row_value+"td[2]").text
            curr_party['race'] = self.driver.find_element(by=By.XPATH,
                                                     value=row_value+"td[3]").text
            curr_party['sex'] = self.driver.find_element(by=By.XPATH,
                                                    value=row_value+"td[4]").text
            curr_party['birth_date'] = self.driver.find_element(by=By.XPATH,
                                                           value=row_value+"td[5]").text
            curr_party['party_type'] = self.driver.find_element(by=By.XPATH,
                                                           value=row_value+"td[6]").text
            curr_party['party_status'] = self.driver.find_element(by=By.XPATH,
                                                             value=row_value+"td[7]").text
            curr_party['last_updated'] = self.driver.find_element(by=By.XPATH,
                                                             value=row_value+"td[8]").text
            if curr_party['party_type'].lower() == 'defendant':
                parties['Defendant'] = curr_party
            elif curr_party['party_type'].lower() == 'officer':
                parties['Officer'] = curr_party
            parties['all_parties'].append(curr_party)
        return parties

    def get_charge_info(self, section_count):
        charge_data = []
        charge_table = self.driver.find_elements(by=By.XPATH, 
                                        value="/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table/tbody/tr".format(section_count))
        row_count = len(charge_table)
        for i in range(2, row_count+1):  
            curr_charge = {}
            row_value = "/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table/tbody/tr[{}]/".format(section_count, i)
            curr_charge['name'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[1]").text
            curr_charge['charge_code'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[2]").text
            curr_charge['original_charge_code'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[3]").text
            curr_charge['disposition_date'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[4]").text
            charge_data.append(curr_charge)
        return charge_data

    def get_bonds_info(self, section_count):
        bonds = {}
        bonds['bond_information'] = []
        bonds['post_information'] = []

        bond_info_table = self.driver.find_elements(by=By.XPATH, 
                                        value="/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table[1]/tbody/tr".format(section_count))
        row_count = len(bond_info_table)
        for i in range(3, row_count+1):  
            curr_bond = {}
            row_value = "/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table[1]/tbody/tr[{}]/".format(section_count, i)
            curr_bond['bond_id'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[1]").text
            curr_bond['set_date'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[2]").text
            curr_bond['ammend_date'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[3]").text
            curr_bond['set_by'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[4]").text
            curr_bond['type_1'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[5]").text
            curr_bond['amount_1'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[6]").text
            curr_bond['type_2'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[7]").text
            curr_bond['amount_2'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[8]").text
            curr_bond['condition'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[9]").text
            bonds['bond_information'].append(curr_bond)

        post_info_table = self.driver.find_elements(by=By.XPATH, 
                                            value="/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table[2]/tbody/tr".format(section_count))
        row_count = len(post_info_table)
        for i in range(3, row_count+1):  
            curr_post = {}
            row_value = "/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table[2]/tbody/tr[{}]/".format(section_count, i)
            curr_post['bond_id'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[1]").text
            curr_post['bond_type'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[2]").text
            curr_post['amount'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[3]").text
            curr_post['date_posted'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[4]").text
            curr_post['posted_by'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[5]").text
            bonds['post_information'].append(curr_post)
        return bonds

    def get_sentencing_info(self, section_count):
        sent_info = []
        sentencing_table = self.driver.find_elements(by=By.XPATH, 
                                        value="/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table/tbody/tr".format(section_count))
        row_count = len(sentencing_table)
        for i in range(2, row_count+1):  
            curr_sentence = {}
            row_value = "/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table/tbody/tr[{}]/".format(section_count, i)
            curr_sentence['and_or'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[1]").text
            curr_sentence['description'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[2]").text
            curr_sentence['amount'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[2]").text
            curr_sentence['units'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[4]").text
            curr_sentence['begin_date'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[5]").text
            curr_sentence['end_date'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[6]").text
            curr_sentence['completion_date'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[7]").text
            curr_sentence['consecutive_or_concurrent'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[8]").text
            sent_info.append(curr_sentence)
        return sent_info

    def get_action_info(self, section_count):
        action_info = []
        action_table = self.driver.find_elements(by=By.XPATH, 
                                        value="/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table/tbody/tr".format(section_count))
        row_count = len(action_table)
        for i in range(2, row_count+1):  
            curr_action = {}
            row_value = "/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table/tbody/tr[{}]/".format(section_count, i)
            curr_action['name'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[1]").text
            curr_action['description'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[2]").text
            curr_action['type'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[3]").text
            curr_action['motion_roster'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[4]").text
            curr_action['begin_date'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[5]").text
            curr_action['completion_date'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[6]").text
            curr_action['documents'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[7]").text
            action_info.append(curr_action)
        return action_info

    def get_financial_info(self, section_count):
        financials = {}
        body_base = '/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table[1]/tbody/tr[2]/'.format(section_count)
        financials['fine_costs'] = self.driver.find_element(by=By.XPATH, value=body_base + 'td[2]').text
        financials['total_paid'] = self.driver.find_element(by=By.XPATH, value=body_base + 'td[4]').text
        financials['balance_due'] = self.driver.find_element(by=By.XPATH, value=body_base + 'td[6]').text

        financials['cost_summery'] = []
        costs_table = self.driver.find_elements(by=By.XPATH, 
                                        value="/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table[2]/tbody/tr".format(section_count))
        row_count = len(costs_table)
        for i in range(3, row_count+1):  
            curr_cost = {}
            row_value = "/html/body/form/div[3]/div/div[2]/div[4]/div/div[{}]/span[2]/table[2]/tbody/tr[{}]/".format(section_count, i)
            curr_cost['description'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[1]").text
            curr_cost['cost_code'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[2]").text
            curr_cost['amount'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[3]").text
            curr_cost['charge_action'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[4]").text
            curr_cost['disbursed_amount'] = self.driver.find_element(by=By.XPATH, value=row_value+"td[5]").text
            financials['cost_summery'].append(curr_cost)
        return financials


    def get_all_info(self):
        #click switch view button
        WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ButtonHTML"]'))).click()
        case_info = {}
        case_info["general_info"] = {}
        case_info["general_info"]["case_number"] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[3]/td[2]').text
        case_info["general_info"]['court_agency'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[3]/td[4]').text
        case_info["general_info"]['filed_date'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[3]/td[6]').text
        case_info["general_info"]['case_type'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[4]/td[2]').text
        case_info["general_info"]['case_sub_type'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[4]/td[4]').text
        case_info["general_info"]['status'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[5]/td[2]').text
        case_info["general_info"]['assigned_judge'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[5]/td[4]').text
        case_info["general_info"]['disposition_judge'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[5]/td[6]').text
        case_info["general_info"]['disposition'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[6]/td[2]').text
        case_info["general_info"]['disposition_date'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[7]/td[2]').text
        case_info["general_info"]['date_received'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[7]/td[4]').text
        case_info["general_info"]['arrest_date'] = self.driver.find_element(by=By.XPATH, value='/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[7]/td[6]').text

        WebDriverWait(self.driver, self.timeout).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div[3]/div/div[2]/div[4]/div/div[1]/span[2]/table/tbody/tr[2]/td[1]")))
        sections = self.driver.find_elements(by=By.CLASS_NAME, value="detailsCaption")
        sec_num = 1
        for el in sections:
            if 'ctl00_ContentPlaceHolder1_LabelSectionTitle' in el.get_attribute('id'):
                info_type = el.text.lower().strip()
                if info_type == "case parties":
                    case_info['case_parties'] = self.get_case_parties_info(sec_num)
                elif info_type == 'charges':
                    case_info['charges'] = self.get_charge_info(sec_num)
                elif info_type == 'sentencing':
                    case_info['sentencing'] = self.get_sentencing_info(sec_num)
                elif info_type == 'actions':
                    case_info['actions'] = self.get_action_info(sec_num)
                elif info_type == 'financials':
                    case_info['financials'] = self.get_financial_info(sec_num)
                elif info_type == 'bonds':
                    case_info['bonds'] = self.get_bonds_info(sec_num)
                sec_num+=1
        return case_info

    def switch_to_other_window(self, old_window: str, close_window=False):
        for window_handle in self.driver.window_handles[-1::]:
            if window_handle != old_window:
                if close_window:
                    self.driver.close()
                self.driver.switch_to.window(window_handle)
                break

    def load_cases_from_file(self, infile="casenums.csv"):
        open_cases = []
        with open(infile, 'r') as f:
            for cn in f:
                open_cases.append(cn)
        return open_cases
