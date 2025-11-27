# tests/test_demo.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_add_todo(driver):
    driver.get("http://microsoftedge.github.io/Demos/demo-to-do")

    wait = WebDriverWait(driver, 10)

    # Wait for input box and send keys
    input_box = wait.until(EC.presence_of_element_located((By.ID, "new-task")))
    input_box.send_keys("Test automation")

    # Click the submit button
    submit_button = driver.find_element(By.CSS_SELECTOR, "div.new-task-form input[type='submit']")
    submit_button.click()

    # Wait for the new task to appear in the list
    tasks_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#tasks li")))
    assert any("Test automation" in t.text for t in tasks_list)


def test_fail_example(driver):
    driver.get("http://microsoftedge.github.io/Demos/demo-to-do")
    assert False, "Intentional failure"
