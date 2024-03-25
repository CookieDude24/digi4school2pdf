import getpass
import os
import re
import sys
import time
from urllib.parse import parse_qs
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from cairosvg import svg2pdf
from pypdf import PdfWriter
from selenium import webdriver
from selenium.common import NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# digi4school userdata
print("Digi4School Credentials:")
username = input("Email: ")
password = getpass.getpass()

# Set the path where the screenshot will be saved
path = os.path.dirname(os.path.abspath(__file__))

# Configure Chrome WebDriver options
options = Options()
options.add_argument("--window-size=7680,4320")
options.add_argument("--start-maximized")
options.add_argument("--headless")
options.add_argument("--disable-gpu")
print("initializing browser...")

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
selection = int(input(f"Select the book you want to convert to pdf or abort [{index}]: "))

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
    platform = 0
    platform_domain = "digi4school.at"

elif "https://a.hpthek.at/" in driver.current_url:
    print("platform: hpthek")
    platform = 1
    platform_domain = "hpthek.at"

elif "https://www.scook.at/" in driver.current_url:
    print("platform: scook.at")
    platform = 2
    platform_domain = "scook.at"
else:
    print("platform not detected, defaulting to Digi4School")
    platform = 0
    platform_domain = "digi4school.at"

if platform == 2:
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

    go_next = driver.find_element(By.CSS_SELECTOR, "button[class='btn go-next'")

    # take screenshot of all pages
    for i in range(first_page_index, last_page_index):
        print(f"processing page {i}...")
        full_page = driver.find_element(By.XPATH, "/html/body/div[3]/div/div[2]/div/div/div/div[4]/img")
        while not (full_page.get_property("complete")):
            time.sleep(0.1)
        full_page.screenshot(f"{book}-{i}.png")

        # go to next page
        go_next.click()

elif platform == 1:
    time.sleep(2)

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

    # get hpthek book-id because it differs from the digi4school book-id
    svg_path = driver.find_element(By.XPATH, "//object").get_attribute("data")
    driver.get(svg_path)
    temp = re.findall(r'\d+', svg_path)
    selected_book = list(map(int, temp))[0]

    while i != last_page_index:
        print(f"processing page {i}...")

        # if the script fails during compilation or merging of the pages, this skips the redundant download of
        # everything, this is not at the start because break statements cannot be used outside a loop
        if os.path.exists(f"./tmp/book-{i}.svg"):
            print(f"skipping downloading of pages because they already are")
            i += 1
            break

        # download the svg
        while True:
            try:
                driver.get(f"https://a.{platform_domain}/ebook/{selected_book}/{i}.svg")
            except NoSuchElementException:
                time.sleep(0.1)
            finally:
                break

        # save the svg file
        file_name = f"./tmp/book-{i}.svg"
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(driver.page_source)

        # open svg file to process all images
        with open(file_name, "r", encoding="utf-8") as file:
            svg_content = file.read()

        soup = BeautifulSoup(svg_content, 'xml')
        image_tags = soup.find_all('image')

        # k is the counter for images of the page
        k = 1
        # download all images embedded in the svg
        for image in image_tags:
            # get url of image
            print(f"processing image #{k} of page {i}")
            image_href = image['xlink:href']

            # screenshot image
            driver.get(f"https://a.{platform_domain}/ebook/{selected_book}/{image_href}")
            while True:
                try:
                    img = driver.find_element(By.TAG_NAME, "img")
                    img.screenshot(f"./tmp/{i}-{k}.png")
                    image['xlink:href'] = f"{i}-{k}.png"
                except NoSuchElementException:
                    time.sleep(0.1)
                except StaleElementReferenceException:
                    time.sleep(0.1)
                finally:
                    break
            k += 1

        # write svg with modified paths to images
        with open(file_name, 'w') as f:
            f.write(str(soup))

        # go to next page
        while True:
            try:
                go_next = driver.find_element(By.CSS_SELECTOR, "#btnNext")
                go_next.click()
            except ElementClickInterceptedException:
                time.sleep(0.1)
            except StaleElementReferenceException:
                time.sleep(0.1)
            except NoSuchElementException:
                time.sleep(0.1)
            finally:
                break
        i += 1
else:
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

    # detect if ebook uses special path to svg
    # noinspection RegExpRedundantEscape
    regex_pattern = re.compile(r'^(https:\/\/a\.digi4school\.at\/ebook\/\d+\/\d+\/)([^\/]+\.svg)$')
    if regex_pattern.match(svg_path):
        svg_path = "placeholder"
    else:
        # in this case the standard path is used
        svg_path = ''

    while i != last_page_index:
        print(f"processing page {i}...")

        # if the script fails during compilation or merging of the pages, this skips the redundant download of
        # everything, this is not at the start because break statements cannot be used outside a loop
        if os.path.exists(f"./tmp/book-{i}.svg"):
            print(f"skipping downloading of pages because they already are")
            i += 1
            break

        current_url = driver.current_url

        # some books have special paths
        # most books with special paths use the following path ebook/$EBOOK-ID/$PAGE-NUMBER/$PAGE-NUMBER.svg
        # but some ebooks use extra special paths: ebook/$EBOOK-ID/1/$PAGE-NUMBER.svg
        if svg_path != '':
            svg_path = str(i) + "/"

        # download the svg
        while True:
            try:
                driver.get(f"https://a.{platform_domain}/ebook/{selected_book}/{svg_path}{i}.svg")

                # some books have extra special paths, detection simply works by checking if the requested page exists
                if driver.find_element(By.TAG_NAME, "h3").text == "digi4school - Fehler":
                    driver.get(f"https://a.{platform_domain}/ebook/{selected_book}/1/{i}.svg")
                    svg_path = "1/"
            except NoSuchElementException:
                time.sleep(0.1)
            finally:
                break

        # save the svg file
        file_name = f"./tmp/book-{i}.svg"
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(driver.page_source)

        # open svg file to process all images
        with open(file_name, "r", encoding="utf-8") as file:
            svg_content = file.read()

        soup = BeautifulSoup(svg_content, 'xml')
        image_tags = soup.find_all('image')

        # k is the counter for images of the page
        k = 1
        # download all images embedded in the svg
        for image in image_tags:
            # get url of image
            print(f"processing image #{k} of page {i}")
            image_href = image['xlink:href']

            # screenshot image
            driver.get(f"https://a.{platform_domain}/ebook/{selected_book}/{svg_path}{image_href}")
            while True:
                try:
                    img = driver.find_element(By.TAG_NAME, "img")
                    img.screenshot(f"./tmp/{i}-{k}.png")
                    image['xlink:href'] = f"{i}-{k}.png"
                except NoSuchElementException:
                    time.sleep(0.1)
                except StaleElementReferenceException:
                    time.sleep(0.1)
                finally:
                    break
            k += 1

        # write svg with modified paths to images
        with open(file_name, 'w') as f:
            f.write(str(soup))

        # go to next page
        while True:
            try:
                go_next = driver.find_element(By.CSS_SELECTOR, "#btnNext")
                go_next.click()
            except ElementClickInterceptedException:
                time.sleep(0.1)
            except StaleElementReferenceException:
                time.sleep(0.1)
            except NoSuchElementException:
                time.sleep(0.1)
            finally:
                break
        i += 1

# svg to pdf
print("compiling pages")
for i in range(first_page_index, last_page_index):
    print(f"compiling page {i}...")
    svg2pdf(unsafe=True, write_to=f"./tmp/book-{i}.pdf", url=f"./tmp/book-{i}.svg")

# merge page into pdf
merger = PdfWriter()
print("merging pages...")
print(first_page_index, last_page_index)
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
