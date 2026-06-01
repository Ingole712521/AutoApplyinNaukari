from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time
url = 'https://www.naukri.com/node-dot-js-jobs-in-pune?k=node.js&l=pune&experience=3'
options = Options()
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
driver = webdriver.Chrome(options=options)

def clear_session(driver):
    driver.delete_all_cookies()
    driver.execute_script('window.localStorage.clear();')
    driver.execute_script('window.sessionStorage.clear();')
try:
    while True:
        print('\nStarting new cycle...\n')
        driver.get(url)
        time.sleep(5)
        logs = driver.get_log('performance')
        nkparam = None
        for entry in logs:
            log = json.loads(entry['message'])['message']
            if log['method'] == 'Network.requestWillBeSent':
                request = log['params']['request']
                headers = request.get('headers', {})
                if 'nkparam' in headers:
                    nkparam = headers['nkparam']
                    with open('nkPool.txt', 'a', encoding='utf-8') as f:
                        f.write(nkparam + '\n')
                    print('nkparam captured and stored')
                    break
        if not nkparam:
            print('nkparam not found in this cycle')
        clear_session(driver)
        time.sleep(2)
except KeyboardInterrupt:
    print('Process stopped by user')
finally:
    driver.quit()
