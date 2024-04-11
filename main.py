import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from urllib.parse import parse_qs
from urllib.parse import urlparse

import requests
from PIL import Image
from bs4 import BeautifulSoup
from cairosvg import svg2pdf
from dotenv import load_dotenv
from pypdf import PdfWriter
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By


def convert_hpthek(book_id, page_number, platform_domain, cookies):
    print(f"processing page {page_number}...")

    request = requests.Session()
    for cookie in cookies:
        request.cookies.set(cookie['name'], cookie['value'])

    while True:
        try:
            response = request.get(f"https://a.{platform_domain}/ebook/{book_id}/{page_number}.svg")
        except NoSuchElementException:
            time.sleep(0.1)
        finally:
            source = response.text
            break

    # save the svg file
    file_name = f"./tmp/book-{page_number}.svg"

    soup = BeautifulSoup(source, 'xml')
    image_tags = soup.find_all('image')

    # k is the counter for images of the page
    k = 1

    # download all images embedded in the svg
    for image in image_tags:
        # get url of image
        image_href = image['xlink:href']
        file_extension = image_href.split(".")[1]
        image['xlink:href'] = f"{page_number}-{k}.{file_extension}"

        # screenshot image
        while True:
            try:
                img = request.get(f"https://a.{platform_domain}/ebook/{book_id}/{image_href}")
                if img.status_code == 200:
                    with open(f"./tmp/{page_number}-{k}.{file_extension}", 'wb') as f:
                        f.write(img.content)
            except NoSuchElementException:
                time.sleep(0.1)
            except StaleElementReferenceException:
                time.sleep(0.1)
            finally:
                print(f"processed image #{k} of page {page_number}")
                break
        k += 1


def convert_scook(book_url, page_number, cookies):
    print(f"processing page {page_number}...")

    page_number_without_leading_zeros = page_number
    page_number = str(page_number).zfill(3)

    request = requests.Session()
    for cookie in cookies:
        request.cookies.set(cookie['name'], cookie['value'])

    file_name = f"./tmp/{page_number}.jpg"

    while True:
        try:
            img = request.get(f"{book_url}{page_number}.jpg")
            if img.status_code == 200:
                with open(file_name, 'wb') as f:
                    f.write(img.content)
        except NoSuchElementException:
            time.sleep(0.1)
        except StaleElementReferenceException:
            time.sleep(0.1)
        finally:
            time.sleep(1)
            break

    # write svg with modified paths to images
    Image.open(file_name).convert("RGB").save(f"./tmp/book-{page_number_without_leading_zeros}.pdf")


def convert_digi4school(book_id, page_number, platform_domain, cookies, svg_path):
    print(f"processing page {page_number}...")

    request = requests.Session()
    for cookie in cookies:
        request.cookies.set(cookie['name'], cookie['value'])

    while True:
        try:
            response = request.get(f"https://a.{platform_domain}/ebook/{selected_book}/{svg_path}{page_number}.svg")
        except NoSuchElementException:
            time.sleep(0.1)
        finally:
            source = response.text
            break

    # save the svg file
    file_name = f"./tmp/book-{page_number}.svg"

    soup = BeautifulSoup(source, 'xml')
    image_tags = soup.find_all('image')

    # k is the counter for images of the page
    k = 1

    # download all images embedded in the svg
    for image in image_tags:
        # get url of image
        image_href = image['xlink:href']
        file_extension = image_href.split(".")[1]
        image['xlink:href'] = f"{page_number}-{k}.{file_extension}"

        # screenshot image
        while True:
            try:
                img = request.get(f"https://a.{platform_domain}/ebook/{book_id}/{svg_path}{image_href}")
                if img.status_code == 200:
                    with open(f"./tmp/{page_number}-{k}.{file_extension}", 'wb') as f:
                        f.write(img.content)
            except NoSuchElementException:
                time.sleep(0.1)
            except StaleElementReferenceException:
                time.sleep(0.1)
            finally:
                print(f"processed image #{k} of page {page_number}")
                break
        k += 1

    # write svg with modified paths to images
    with open(file_name, 'w') as f:
        f.write(str(soup))

    # write svg with modified paths to images
    svg2pdf(unsafe=True, write_to=f"./tmp/book-{page_number}.pdf", url=file_name)


# digi4school userdata
load_dotenv()
if os.getenv('DIGI4SCHOOL_USERNAME') is None:
    username = input("Username: ")
else:
    username = str(os.getenv('DIGI4SCHOOL_USERNAME'))
if os.getenv('DIGI4SCHOOL_PASSWORD') is None:
    password = getpass()
else:
    password = str(os.getenv('DIGI4SCHOOL_PASSWORD'))

# Set things up
path = os.path.dirname(os.path.abspath(__file__))
merger = PdfWriter()

# Configure Chrome WebDriver options
print("initializing browser...")
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.enable_downloads = True

# Initialize the Chrome WebDriver
driver = webdriver.Chrome(options=options)
driver.maximize_window()
driver.implicitly_wait(10)

# Navigate to the Ebook
print("navigating to the ebook...")
driver.get("https://digi4school.at/")
original_window = driver.current_window_handle

# Accept Cookies
print("accepting cookies...")
accept_button = driver.find_element("id", "cookies_confirm")
accept_button.click()

# pass login data
print("logging in...")
driver.find_element("id", "email").send_keys(username)
driver.find_element("id", "password").send_keys(password)

# find login button via xpath
login_button = driver.find_element(By.XPATH, "/html/body/div[3]/div/div[1]/div/div[3]/div[2]/form/button")
login_button.click()

# fetch books
all_books = driver.find_elements(By.CSS_SELECTOR, "a[class='bag']")

# output all books
print("----------------------------------------------------------------")
print("Total amount of books: ", len(all_books))
print("----------------------------------------------------------------")

index = 0
book = "book"
for book in all_books:
    print(str(index).zfill(2) + " | " + book.find_element(By.CSS_SELECTOR, "h1").text)
    index += 1
print(str(index).zfill(2) + " | abort")
print("----------------------------------------------------------------")

# get user selection
if os.getenv('BOOK_INDEX') is None:
    selection = int(input(f"Select the book you want to convert to pdf or abort [{index}]: "))
else:
    selection = int(os.getenv('BOOK_INDEX'))

# validate input
if selection == index:
    sys.exit(0)
if selection < 0 or selection > index:
    sys.exit("Invalid input")

# get selected book
i = 0
selected_book = 0
for book in all_books:
    if selection == i:
        selected_book = book.get_attribute("data-id")
        book = book.find_element(By.CSS_SELECTOR, "h1").text
        break
    i += 1

# open selected book
print("processing ebook website...")
book_button = driver.find_element(By.CSS_SELECTOR, f"a[data-id='{selected_book}'")
driver.execute_script("arguments[0].setAttribute('target','_self')", book_button)
book_button.click()

# create tmp dir
try:
    os.mkdir("./tmp")
except FileExistsError:
    print("WARNING: directory already exists, files may be overwritten")
    time.sleep(1)
# check which platform the ebook uses
if "https://a.digi4school.at/" in driver.current_url:
    print("platform: Digi4School")
    platform_domain = "digi4school.at"

elif "https://a.hpthek.at/" in driver.current_url:
    print("platform: hpthek")
    platform_domain = "hpthek.at"

elif "https://www.scook.at/" in driver.current_url:
    print("platform: scook.at")
    platform_domain = "scook.at"
else:
    print("platform not detected, defaulting to Digi4School")
    platform_domain = "digi4school.at"

if platform_domain == "scook.at":
    # switch to iframe
    iframe = driver.find_element(By.XPATH, "//iframe")
    driver.switch_to.frame(iframe)

    # go to last page
    go_last = driver.find_element(By.CSS_SELECTOR, ".go-last")
    go_last.click()

    # get index of the last page
    last_page_index = int(
        driver.find_element(By.CSS_SELECTOR, "input[class='current-page']").get_attribute("placeholder"))
    print(f"last_page_index: {last_page_index}")
    last_page_index += 1

    # go to first page
    go_first = driver.find_element(By.CSS_SELECTOR, "button[class='btn go-first'")
    go_first.click()
    first_page_index = int(
        driver.find_element(By.CSS_SELECTOR, "input[class='current-page']").get_attribute("placeholder"))

    # get all cookies
    cookies = driver.get_cookies()

    # this value is hardcoded it should only cut off ${3_DIGIT_PAGE_NUMBER}.jpg
    # if it doesn't idc because I'm to lazy to properly implement this feature
    image_href = driver.find_element(By.XPATH, "//img").get_attribute("src")
    book_url = image_href[0:-7]

    # download all pages
    with ThreadPoolExecutor() as executor:
        for i in range(first_page_index, last_page_index):
            t = executor.submit(convert_scook, book_url, i, cookies)


elif platform_domain == "hpthek.at":
    time.sleep(2)
    print("plattform 1")
    # go to last page
    time.sleep(1)
    go_last = driver.find_element(By.CSS_SELECTOR, '#btnLast')
    go_last.click()
    time.sleep(2)
    last_page_index = int(parse_qs((urlparse(driver.current_url)).query)['page'][0])
    last_page_index += 1  # the first index of the books is 1, therefore the last index is incremented by 1

    # go to first page
    go_first = driver.find_element(By.CSS_SELECTOR, "#btnFirst")
    go_first.click()
    time.sleep(2)
    first_page_index = int(parse_qs((urlparse(driver.current_url)).query)['page'][0])
    print(first_page_index, last_page_index)
    i = first_page_index

    # get all cookies
    cookies = driver.get_cookies()

    # get hpthek book-id because it differs from the digi4school book-id
    svg_path = driver.find_element(By.XPATH, "//object").get_attribute("data")
    driver.get(svg_path)
    temp = re.findall(r'\d+', svg_path)
    selected_book = list(map(int, temp))[0]

    # initialize requests
    with ThreadPoolExecutor() as executor:
        for i in range(first_page_index, last_page_index):
            t = executor.submit(convert_hpthek, selected_book, i, platform_domain, cookies)

elif platform_domain == "digi4school.at":
    time.sleep(2)

    if driver.current_url == f"https://a.digi4school.at/ebook/{selected_book}/":
        book_button = driver.find_element(By.XPATH, "/html/body/div[2]/div/div/a[1]")
        driver.execute_script("arguments[0].setAttribute('target','_self')", book_button)
        book_button.click()

    # go to last page
    time.sleep(1)
    go_last = driver.find_element(By.CSS_SELECTOR, '#btnLast')
    go_last.click()
    time.sleep(1)
    last_page_index = int(parse_qs((urlparse(driver.current_url)).query)['page'][0])
    last_page_index += 1  # the first index of the books is 1, therefore the last index is incremented by 1

    # go to first page
    go_first = driver.find_element(By.CSS_SELECTOR, "#btnFirst")
    go_first.click()
    time.sleep(1)
    first_page_index = int(parse_qs((urlparse(driver.current_url)).query)['page'][0])
    print(first_page_index, last_page_index)
    i = first_page_index

    # get path to svg
    svg_path = driver.find_element(By.XPATH, "//object").get_attribute("data")

    # get cookies
    cookies = driver.get_cookies()

    # detect if ebook uses special path to svg
    # noinspection RegExpRedundantEscape
    regex_pattern = re.compile(r'^(https:\/\/a\.digi4school\.at\/ebook\/\d+\/\d+\/)([^\/]+\.svg)$')
    if regex_pattern.match(svg_path):
        svg_path = "placeholder"
    else:
        # in this case the standard path is used
        svg_path = ''
    with ThreadPoolExecutor() as executor:
        for i in range(first_page_index, last_page_index):
            print(f"processing page {i}...")

            if svg_path != '' and svg_path != 'placeholder':
                svg_path = str(i) + "/"

            executor.submit(convert_digi4school, selected_book, i, platform_domain, cookies, svg_path)

# merge page into pdf
print("merging pages...")
for i in range(first_page_index, last_page_index):
    # convert to pdf
    try:
        merger.append(f'./tmp/book-{i}.pdf')
    except FileNotFoundError:
        print(f"page {i} could not be found")
    finally:
        print(f"merging page {i} to .pdf...")

# write final pdf
print("processing final pdf...")
try:
    merger.write(f'{book}.pdf')
except FileNotFoundError:
    merger.write("book.pdf")

# stop everything
driver.quit()
merger.close()
executor.shutdown()
