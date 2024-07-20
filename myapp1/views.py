import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from .forms import UploadFileForm
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from django.http import FileResponse, HttpResponse

def handle_uploaded_file(file):
    # Read the uploaded Excel file
    df = pd.read_excel(file)
    print("Column names:", df.columns.tolist())  # Debugging statement
    return df

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            df = handle_uploaded_file(file)
            request.session['excel_data'] = df.to_dict('records')  # Save data in session

            # Clear any previous not-on-whatsapp file session
            if 'not_on_whatsapp_file' in request.session:
                del request.session['not_on_whatsapp_file']

            return redirect('display_data')
    else:
        form = UploadFileForm()

    # Check if there is a not-on-whatsapp file to download
    not_on_whatsapp_file_path = request.session.get('not_on_whatsapp_file')
    download_button = False
    if not_on_whatsapp_file_path:
        download_button = True

    return render(request, 'upload.html', {'form': form, 'download_button': download_button})

def display_data(request):
    data = request.session.get('excel_data')
    if data is None:
        return redirect('upload_file')
    return render(request, 'display_data.html', {'data': data})

def send_messages(request):
    if request.method == 'POST':
        data = request.session.get('excel_data')
        if data is None:
            return redirect('upload_file')

        not_on_whatsapp = []
        driver = None

        try:
            # Setup Chrome WebDriver
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")

            # Use WebDriver Manager to ensure the latest ChromeDriver is used
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            # Login to WhatsApp Web
            driver.get("https://web.whatsapp.com/")
            input("Press ENTER after logging into WhatsApp Web and your chats are visible.")

            # Wait for WhatsApp Web to load
            wait_time = 120  # 2 minutes (in seconds)
            print(f"Waiting for {wait_time} seconds to ensure WhatsApp Web loads completely...")
            time.sleep(wait_time)

            # Send messages
            for row in data:
                phone_number = row['Phone Number']
                message = row['Message']

                try:
                    # Search for the contact by phone number
                    search_xpath = '//div[@role="textbox"][@contenteditable="true"][@data-tab="3"]'
                    search_box = driver.find_element(By.XPATH, search_xpath)
                    search_box.clear()  # Clear the search box
                    search_box.send_keys(phone_number)
                    search_box.send_keys(Keys.ENTER)
                    time.sleep(10)  # Wait for the chat to open

                    # Check if the contact exists on WhatsApp
                    contact_not_found_xpath = '//div[@class="_2sNbV"][contains(text(), "phone number shared via url is invalid")]'
                    if driver.find_elements(By.XPATH, contact_not_found_xpath):
                        not_on_whatsapp.append(phone_number)
                        continue

                    # Find the message box and send the message
                    message_box_xpath = '//div[@role="textbox"][@contenteditable="true"][@data-tab="10"]'
                    message_box = driver.find_element(By.XPATH, message_box_xpath)
                    message_box.send_keys(message)
                    message_box.send_keys(Keys.ENTER)
                    time.sleep(2)  # Wait for the message to be sent

                    messages.success(request, f"Message sent to {phone_number}")

                    # Go back to the search box for the next contact
                    back_button_xpath = '//button[@class="_1E0Oz"]'
                    back_button = driver.find_element(By.XPATH, back_button_xpath)
                    back_button.click()
                    time.sleep(2)  # Wait to ensure the back action is completed

                except Exception as e:
                    messages.error(request, f"Error sending message to {phone_number}: {e}")
                    print(f"Error sending message to {phone_number}: {e}")  # Add debug print

            # Save numbers not on WhatsApp to a file
            if not_on_whatsapp:
                not_on_whatsapp_df = pd.DataFrame(not_on_whatsapp, columns=['Phone Number'])
                not_on_whatsapp_file = 'not_on_whatsapp.xlsx'
                file_path = os.path.join(settings.MEDIA_ROOT, not_on_whatsapp_file)
                not_on_whatsapp_df.to_excel(file_path, index=False)
                request.session['not_on_whatsapp_file'] = file_path

            # Redirect to upload page
            return redirect('upload_file')

        except Exception as e:
            messages.error(request, f"Failed to send messages: {e}")
            print(f"Failed to send messages: {e}")  # Add debug print

        finally:
            # Close the browser session in finally block to ensure cleanup
            if driver:
                driver.quit()
                print("WebDriver session closed.")  # Add debug print

    return redirect('upload_file')


def generate_report(success_list, failure_list):
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.append(['Phone Number', 'Status'])
    for number in success_list:
        ws.append([number, 'Success'])
    for number in failure_list:
        ws.append([number, 'Failed'])
    wb.save('/mnt/data/report.xlsx')

def download_report(request):
    with open('/mnt/data/report.xlsx', 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=report.xlsx'
        return response

def download_not_on_whatsapp_file(request):
    not_on_whatsapp_file_path = request.session.get('not_on_whatsapp_file')
    if not_on_whatsapp_file_path:
        with open(not_on_whatsapp_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={os.path.basename(not_on_whatsapp_file_path)}'
            return response
    return redirect('upload_file')
