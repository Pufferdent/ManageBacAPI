from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

def taskParser(htmltag):
    ret = {}
    title = htmltag.find('h4', class_='title')

    ret["title"] = title.text.strip()
    ret["taskLink"] = title.find('a')['href'].strip()

    date = htmltag.find('div', class_='date-badge')
    ret["time"] = {}
    ret["time"]["month"] = date.find('div', class_='month').text.strip()
    ret["time"]["day"] = date.find('div', class_='day').text.strip()

    labels = htmltag.find('div', class_='labels-set flex flex-start flex-wrap')
    ret["time"]["duedate"] = labels.find('span', class_='due-date').text.strip()

    late = htmltag.find('div', class_='label label-with-icon label-late')
    pending = htmltag.find('div', class_='label label-with-icon label-pending')
    submitted = htmltag.find('div', class_='label label-with-icon label-submitted')
    if late is not None:
        ret["lps"] = "late"
        ret["late"] = late.get('data-original-title', None)
    elif pending is not None:
        ret["lps"] = "pending"
        ret["pending"] = pending.get('data-original-title', None)
    elif submitted is not None:
        ret["lps"] = "submitted"
        ret["submitted"] = submitted.get('data-original-title', None)

    comment_div = htmltag.find('div', class_='fix-body-margins redactor-styles fr-view fr-element')
    if comment_div is not None:
        ret["comment"] = ''.join(p.get_text(strip=True) for p in comment_div.find_all('p'))


    ret["labels"] = []
    for div in labels.find_all('div'):
        a_tag = div.find('a')  # Find the <a> tag within the div
        if a_tag and 'href' in a_tag.attrs:  # Check if it exists and has href
            ret["classLink"] = a_tag['href'].strip()
            ret["class"] = a_tag.text.strip()
        
        if not a_tag:
            ret["labels"].append(div.text.strip())
    
    status = htmltag.find('div', class_='flex content-center inline-block')
    if status:
        ret["status"] = status.text.strip()
        points = status.find('div', class_='points')
        if points:
            ret["points"] = points.text.strip()
            ret["status"] = ret["status"][:-len(ret["points"])]
    else:
        cell = htmltag.find('div', class_='flex flex-column content-center')
        if cell:
            ret["status"] = cell.text.strip()


    return ret

class Student:
    def __init__(self, name, password, link):
        self.name = name
        self.password = password
        self.link = link
        self.loggedIn = False
        self.classInfo = {}

        self.wait = WebDriverWait(self.driver, 10)

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model (if needed)
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

        self.driver = webdriver.Chrome(options = chrome_options)  # or webdriver.Firefox()

    def login(self):
        self.driver.get(self.link + '/login')

        # Find the username and password fields and enter your credentials
        username_input = self.driver.find_element(By.NAME, 'login')  # Adjust selector as needed
        password_input = self.driver.find_element(By.NAME, 'password')  # Adjust selector as needed

        username_input.send_keys(self.name)
        password_input.send_keys(self.password)

        # Submit the form (you might need to click a button instead)
        password_input.send_keys(Keys.RETURN)  # Or find and click the login button


        if self.driver.current_url != self.link + '/student/home': # Check if login was successful
            raise Exception("Login failed")
        
        self.loggedIn = True
    
    def getCourses(self):
        """Get the courses for the student. Will set self.classes AND return it."""
        self.driver.get(self.link + '/student')
        element = WebDriverWait(self.driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "li.f-menu-item.parent.js-menu-classes-list")))
        element.click()

        time.sleep(0.5)
        # Get the HTML content of the page
        html = self.driver.page_source

        # You can now parse the HTML with Beautiful Soup
        soup = BeautifulSoup(html, 'html.parser')

        classesdata = soup.find("li", class_="f-menu-item parent js-menu-classes-list opened")

        classes = []

        for item in classesdata.find_all("a", class_='f-menu-link f-menu-submenu-link'):
            if item.text.strip()!="Browse All Classes":
                classes.append({"name" : item.text.strip(), "link": item["href"]})
    
        self.classes = classes

        return classes
    
    def getClass(self, classLink):
        """Get the class info for the class with the given link. Will set self.classInfo[classLink] AND return it."""
        ret = {}
        self.driver.get(self.link + classLink + '/core_tasks')
        self.wait.until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
)
        soup2 = BeautifulSoup(self.driver.page_source, 'html.parser')
        singleclass = soup2.find_all("div", class_="fusion-card-item short-assignment section flex flex-wrap")

        ret["tasks"] = ([taskParser(task) for task in singleclass])

        gradelist = soup2.find("div", class_='sidebar-items-list')
        ret["grades"] = []
        for gradeitem in gradelist.find_all("div", class_="list-item"):
            try:
                findgrade = gradeitem.find_all("div", class_="cell")
                temp = {}
                temp["type"] = findgrade[0].text.strip()
                temp["grade"] = findgrade[1].text.strip()
                if temp["type"] != "Category (Weight)":
                    ret["grades"].append(temp)
            except:
                ret["grades"].append({"type": "N/A", "grade": "N/A"})
        
        self.driver.get(self.link + classLink)
        self.wait.until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
)
        soup2 = BeautifulSoup(self.driver.page_source, 'html.parser')
        singleclass = soup2.find("div", class_="members-list students-list")

        ret["classmates"] = []
        for student in singleclass.find_all("div", class_="member"):
            name = student.get("data-original-title", "").strip()
            ret["classmates"].append(name)
        ret["teachers"] = [teacher.get("data-original-title", "").strip() for teacher in soup2.find("div", class_="members-list teachers-list").find_all("div", class_="js-section-owner")]

        self.classInfo[classLink] = ret
        return ret

    def uploadFile(self, file_path, tasklink):
        """taskLink format can be found in classInfo."""
        self.driver.get(self.link+ tasklink +'/dropbox')

        upload_element = self.driver.find_element(By.ID, "dropbox_assets_attributes_0_file")

        
        upload_element.send_keys(file_path)

        submit_button = self.driver.find_element(By.NAME, "commit")  # Update if necessary
        submit_button.click()