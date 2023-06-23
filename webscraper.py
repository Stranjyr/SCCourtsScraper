from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from threading import Thread

login_url = "https://apps.sccourts.org/logon/LogonPoint/tmindex.html"
username = ""
password = ""

defendants_info = []
case_errors = []
class Defendant():
    def __init__(self):
        self.caseid = ""
        self.dob = ""
        self.charge = ""
        self.dispoDate = ""
    def __str__(self):
        return "{},{},{},{}\n".format(self.dob, self.caseid, self.charge, self.dispoDate)


def switch_to_other_window(driver: webdriver.Firefox, old_window: str, close_window=False):
    for window_handle in driver.window_handles[-1::]:
        if window_handle != old_window:
            if close_window:
                driver.close()
            driver.switch_to.window(window_handle)
            break

def login(driver: webdriver.Firefox):
    driver.get(login_url)
    # driver.implicitly_wait(0.5)
    WebDriverWait(driver, 100000).until(EC.presence_of_element_located((By.NAME, "login")))
    name_field = driver.find_element(by=By.NAME, value="login")
    password_field = driver.find_element(by=By.NAME, value="passwd")
    login_btn = driver.find_element(by=By.ID, value="nsg-x1-logon-button")
    name_field.send_keys(username)
    password_field.send_keys(password)
    login_btn.click()
    WebDriverWait(driver, 1000000).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#allAppsBtn'))).click()
    # apps_btn = driver.find_element(by=By.CSS_SELECTOR, value="#allAppsBtn")
    # apps_btn.click()
    WebDriverWait(driver, 100000).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.storeapp:nth-child(3) > a:nth-child(2) > div:nth-child(4) > p:nth-child(1)")))

    crim_justice = driver.find_element(by=By.CSS_SELECTOR, value="li.storeapp:nth-child(3) > a:nth-child(2) > div:nth-child(4) > p:nth-child(1)")
    crim_justice.click()

    WebDriverWait(driver, 1000000).until(EC.number_of_windows_to_be(2))

    switch_to_other_window(driver, driver.current_window_handle, True)
    WebDriverWait(driver, 100000).until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$TextBoxCaseNumber")))
    new_base_url = driver.current_url
    return new_base_url

def openCase(driver: webdriver.Firefox, casenum: str, base_url: str):
    # driver.get(base_url)
    # driver.implicitly_wait(0.5)
    orig_window = driver.current_window_handle
    
    
    text_box = driver.find_element(by=By.NAME, value="ctl00$ContentPlaceHolder1$TextBoxCaseNumber")

    text_box.clear()
    text_box.send_keys(casenum)
    WebDriverWait(driver, 100000).until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$ButtonSearch")))
    WebDriverWait(driver, 100000).until(EC.element_to_be_clickable((By.NAME, "ctl00$ContentPlaceHolder1$ButtonSearch"))).click()

    # print(casenum)
    curr_window_count = len(driver.window_handles)
    WebDriverWait(driver, 1000000).until(EC.element_to_be_clickable((By.LINK_TEXT, casenum))).click()

    # wait.until(EC.number_of_windows_to_be(curr_window_count+1))
    # switch_to_other_window(driver, orig_window)
    return orig_window

def getCaseInfo(driver: webdriver.Firefox, casenum: str, orig_window: str):
    my_defendant = Defendant()
    # /html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody
    my_defendant.caseid = casenum
    WebDriverWait(driver, 100000).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody/tr[2]/td[6]")))
    driver.implicitly_wait(0.1)
    name_table = driver.find_elements(by=By.XPATH, 
                                      value="/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody/tr")
    row_count = len(name_table)
    # print(row_count)
    for i in range(2, row_count+1):
        # print(i)
        party_type_value = "/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody/tr[{}]/td[6]".format(i)
        # print(party_type_value)
        party_type = driver.find_element(by=By.XPATH, value=party_type_value)
        # print(party_type)
        if party_type.text == "Defendant":
            my_defendant.dob = (driver.find_element(by=By.XPATH, value="/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody/tr[{}]/td[5]".format(i)).text)
            if my_defendant.dob == "":
                my_defendant.dob = "N\A"

    WebDriverWait(driver, 1000000).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__tab_ctl00_ContentPlaceHolder1_TabContainerCaseDetails_TabPanel2"]'))).click()
    WebDriverWait(driver, 1000000).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="ctl00_ContentPlaceHolder1_TabContainerCaseDetails_TabPanel2"]')))
    my_defendant.charge = (driver.find_element(by=By.XPATH, value="/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[2]/span/table/tbody/tr[2]/td[2]").text)
    if len(my_defendant.charge.split('/ ')) >1:
        my_defendant.charge = '"' + my_defendant.charge.split('/ ')[1] + '"'

    my_defendant.dispoDate = (driver.find_element(by=By.XPATH, value="/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[2]/span/table/tbody/tr[2]/td[4]").text)
    driver.close()
    driver.switch_to.window(orig_window)
    return my_defendant

def getCaseInfoFindCasenum(driver: webdriver.Firefox, orig_window: str):
    my_defendant = Defendant()
    # defendants_info[-1].append(casenum)

    # /html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody
    WebDriverWait(driver, 100000).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[3]/td[2]")))
    my_defendant.caseid = driver.find_element(by=By.XPATH, value="/html/body/form/div[3]/div/div[2]/div[3]/table/tbody/tr[3]/td[2]").text
    my_defendant.caseid = my_defendant.caseid.strip('\n')

    WebDriverWait(driver, 100000).until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody/tr[2]/td[6]")))
    driver.implicitly_wait(0.1)
    name_table = driver.find_elements(by=By.XPATH, 
                                      value="/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody/tr")
    row_count = len(name_table)
    # print(row_count)
    for i in range(2, row_count+1):
        # print(i)
        party_type_value = "/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody/tr[{}]/td[6]".format(i)
        # print(party_type_value)
        party_type = driver.find_element(by=By.XPATH, value=party_type_value)
        # print(party_type)
        if party_type.text == "Defendant":
            my_defendant.dob = (driver.find_element(by=By.XPATH, value="/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[1]/span/table/tbody/tr[{}]/td[5]".format(i)).text)
            if my_defendant.dob == "":
                my_defendant.dob = "N\A"

    WebDriverWait(driver, 1000000).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__tab_ctl00_ContentPlaceHolder1_TabContainerCaseDetails_TabPanel2"]'))).click()
    WebDriverWait(driver, 1000000).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="ctl00_ContentPlaceHolder1_TabContainerCaseDetails_TabPanel2"]')))
    my_defendant.charge = (driver.find_element(by=By.XPATH, value="/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[2]/span/table/tbody/tr[2]/td[2]").text)
    if len(my_defendant.charge.split('/ ')) >1:
        my_defendant.charge = '"' + my_defendant.charge.split('/ ')[1] + '"'

    my_defendant.dispoDate = (driver.find_element(by=By.XPATH, value="/html/body/form/div[3]/div/div[2]/div[5]/div/div/div[2]/div[2]/span/table/tbody/tr[2]/td[4]").text)
    driver.close()
    driver.switch_to.window(orig_window)
    return my_defendant

def print_to_csv():
    with open("reinstatment_scrape.csv", 'w') as f:
        for d in defendants_info:
            f.write("{},{},{},{}\n".format(d.dob, d.caseid, d.charge, d.dispoDate))


def load_cases(infile="casenums.csv"):
    open_cases = []
    with open(infile, 'r') as f:
        for cn in f:
            open_cases.append(cn)
    return open_cases

def fix_birthdays(borked_file, new_file):
    options = Options()
    options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    main_driver = webdriver.Firefox(options=options)
    base_url = login(main_driver)
    i = 0
    actual_missing = []
    with open(borked_file, 'r') as bf:
        with open(new_file, 'w') as nf:
            for line in bf:
                print(i)
                i+=1
                fields = line.split(',')
                if fields[0] == 'N\A':
                    print("fixing")
                    orig_window = openCase(main_driver, fields[1], base_url)
                    fixed_defendant = getCaseInfo(main_driver, fields[1], orig_window)
                    if fixed_defendant.dob == "N\A":
                        actual_missing.append(fields[1])
                        print("No DOB")
                    nf.write(str(fixed_defendant))
                else:
                    nf.write(line)
    print(actual_missing)

def scrape_threading_setup(input_file, output_file, thread_split_size, bucket_size):
    case_list = load_cases(infile=input_file)
    thread_list = []
    thread_count = int(len(case_list)/thread_split_size)
    if len(case_list)%thread_split_size != 0:
        thread_count+=1
    for i in range(thread_count):
        thread_split_end = min(len(case_list), (i+1)*thread_split_size)
        thread_list.append(Thread(target=scrape_load_multiple, args=(case_list[i*thread_split_size:thread_split_end], output_file+"{}".format(i)+".csv", bucket_size)))
        thread_list[-1].start()
    for thr in thread_list:
        thr.join()

def scrape_load_multiple(case_list, output_file, bucket_size=10):
    print("Thread start")
    options = Options()
    options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    driver = webdriver.Firefox(options=options)
    base_url = login(driver)
    # case_list = load_cases(infile=input_file)
    def_dict = {}
    num_buckets = int(len(case_list)/bucket_size)
    if len(case_list)%bucket_size > 0:
        num_buckets+=1
    search_window = driver.current_window_handle
    with open(output_file, 'w') as out_f:
        for i in range(num_buckets):
            last_case = ""
            bucket_end = min((i+1)*bucket_size, len(case_list))
            try:
                for j in range(i*bucket_size, bucket_end):
                    last_case = case_list[j].strip('\n')
                    openCase(driver, last_case, base_url)
                    # driver.implicitly_wait(0.1)
                    driver.switch_to.window(search_window)
                for jj in range(i*bucket_size, bucket_end):
                    switch_to_other_window(driver, search_window)
                    defendant = getCaseInfoFindCasenum(driver, search_window)
                    def_dict[defendant.caseid] = defendant
                    
                for jjj in range(i*bucket_size, bucket_end):
                    last_case = case_list[jjj].strip('\n')
                    next_defendant = def_dict[last_case]
                    out_f.write(str(next_defendant))
            except KeyboardInterrupt:
                print("User Canceled")
                return
            except Exception as e:
                print("Error with case : {} - {}".format(last_case, e))
            print("{}/{}".format(i+1, num_buckets))
    driver.close()
    return def_dict


#18735GT no case num - line 12
if __name__ == "__main__":
    scrape_threading_setup("msngbdy_test.txt", "thread_missing_bday_fix", 200, 10)
    # scrape_load_multiple("missing_bday_casenums_first.txt", "missing_bday_file.csv", 20)
    # fix_birthdays("fixed_lines.csv", "bday_fill.csv")
    # options = Options()
    # options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    # main_driver = webdriver.Firefox(options=options)
    # casenums = load_cases()
    # print(type(main_driver))
    # base_url = login(main_driver)
    # orig_window = openCase(main_driver, "47945HB", base_url)
    # getCaseInfo(main_driver, "47945HB", orig_window)
    # # # for indx, cn in enumerate(casenums):
    # # #     print("{}/{}".format(indx+1, len(casenums)))
    # # #     with open("casenums.csv", 'r') as f:
    # # #         try:
    # # #             orig_window = openCase(main_driver, cn, base_url)
    # # #             defendants_info.append(getCaseInfo(main_driver, cn, orig_window))
    # # #         except KeyboardInterrupt:
    # # #             print("User Canceled")
    # # #             break
    # # #         except Exception as e:
    # # #             print("Error with case : {} - {}".format(cn, e))
    # # #             case_errors.append(cn)
    # # #         d = defendants_info[-1]
    # # #         f.write("{},{},{},{}\n".format(d.dob, d.caseid, d.charge, d.dispoDate))
    # # # main_driver.close()
    # # print([str(d) for d in defendants_info])
    # # print(case_errors)
    # # # print_to_csv()
