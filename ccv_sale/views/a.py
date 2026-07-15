from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta

import time
import os, glob, shutil
import zipfile
import xml.etree.ElementTree as ET
import xmlrpc.client
import json
from config_loader import get_meinvoice_config, get_odoo_config, get_path_config, get_selenium_config, config
import sys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Load cấu hình
try:
    meinvoice_config = get_meinvoice_config()
    odoo_config = get_odoo_config()
    path_config = get_path_config()
    selenium_config = get_selenium_config()
    
    # Kiểm tra cấu hình bắt buộc
    required_configs = [
        'MEINVOICE_LOGIN_URL', 'MEINVOICE_USERNAME', 'MEINVOICE_PASSWORD',
        'ODOO_URL', 'ODOO_DATABASE', 'ODOO_USERNAME', 'ODOO_PASSWORD',
        'TARGET_FOLDER'
    ]
    config.validate_required_configs(required_configs)
    print("✅ Đã load cấu hình thành công!")
    
except Exception as e:
    print(f"❌ Lỗi khi load cấu hình: {e}")
    exit(1)

def driver_chrome_auto_pull():
# Khởi tạo trình duyệt Chrome với cấu hình
    chrome_options = webdriver.ChromeOptions()
    if selenium_config['headless_mode']:
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # Truy cập trang web
        #today_str = datetime.now().strftime(config.get('DATE_FORMAT', '%d/%m/%Y'))
        today_str = '30/09/2025'
        driver.get(meinvoice_config['login_url'])
        print(f"Tiêu đề trang: {driver.title}")

        driver.maximize_window()

        # Giảm kích thước màn hình xuống 80%
        # Thực hiện Ctrl + lăn chuột để giảm zoom xuống 80%
    
        
    
        
        # Chờ input field xuất hiện
        wait = WebDriverWait(driver, selenium_config['default_wait_time'])
        username_input = wait.until(EC.presence_of_element_located((By.ID, "UserName")))
        
        # Nhập email vào input field
        username_input.clear()
        username_input.send_keys(meinvoice_config['username'])
        print("Đã nhập email thành công!")

        # Tìm và bấm nút "Đã hiểu" với class 'btn livechat-button-understood'
        btn_understood = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.livechat-button-understood"))
        )
        print(btn_understood)
        btn_understood.click()
        print("Đã bấm nút 'Đã hiểu'!")

        # Tìm và bấm nút đăng nhập với id là 'btnLogin'
        btn_login = wait.until(EC.element_to_be_clickable((By.ID, "btnLogin")))
        btn_login.click()
        print("Đã bấm nút tiếp tục!")

        # Chờ input field xuất hiện
        wait = WebDriverWait(driver, selenium_config['login_wait_time'])

        # Nhập mật khẩu vào trường mật khẩu có id là 'Password'
        password_input = wait.until(EC.presence_of_element_located((By.ID, "Password")))
        password_input.clear()
        password_input.send_keys(meinvoice_config['password'])
        print("Đã nhập mật khẩu thành công!")

        # Tìm và bấm nút đăng nhập với id là 'btnLogin'
        btn_login = wait.until(EC.element_to_be_clickable((By.ID, "btnLogin")))
        btn_login.click()
        print("Đã bấm nút đăng nhập!")

        # Chờ trang web load xong
        time.sleep(10)

        # Đợi trang load xong và nhấn nút có id 'invoice'
        btn_invoice = wait.until(EC.element_to_be_clickable((By.ID, "invoice")))
        btn_invoice.click()
        print("Đã bấm nút hóa đơn đầu vào")

        time.sleep(2)
        
        driver.execute_script("document.body.style.zoom='80%'")
        print("Đã giảm kích thước màn hình xuống 80% bằng Ctrl + lăn chuột")

        time.sleep(2)
        # Đợi load
        wait = WebDriverWait(driver, selenium_config['default_wait_time'])
        # Bấm vào chỗ có id 'filter-invoice-list'
        btn_filter_invoice = wait.until(EC.element_to_be_clickable((By.ID, "filter-invoice-list")))
        btn_filter_invoice.click()
        print("Đã bấm nút Lọc hóa đơn!")

        time.sleep(3)

        # Bấm vào nút gợi ý
        btn_suggestion = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "#app > div:nth-child(1) > div.layout--main.navbar-sticky > div:nth-child(4) > div > div.notification-feature > div > div:nth-child(1) > div > div:nth-child(1) > div:nth-child(1) > div.flex.box-feature > div > div.flex.ms-pos-relative.icon-feature.jus-center.align-center.taxaxion-remind"
            ))
        )
        btn_suggestion.click()
        print("Đã bấm vào nút gợi ý!")

        time.sleep(10)

        # Bấm vào <div data-v-0eb71e51="" class="mi mi-24 mi-arrow-dropdown"></div>
        input_date_1 = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "body > div.ms-dropdown.ms-dropdown-menu > div > div > div.content-filter-invoice-list.content-filter-invoice-list-small > div:nth-child(2) > div > div.flex.w-2\/3 > div.from-date.ml-4.w-1\/2 > div.ms-datepicker.ms-editor.hx-32 > div > input"
            ))
        )
        # input_date_1.clear()
        input_date_1.send_keys(Keys.CONTROL + "a")
        input_date_1.send_keys(Keys.DELETE)
        input_date_1.send_keys(today_str)
        print("Đã nhập ngày bắt đầu!")

        input_date_2 = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "body > div.ms-dropdown.ms-dropdown-menu > div > div > div.content-filter-invoice-list.content-filter-invoice-list-small > div:nth-child(2) > div > div.to-date.ml-4.flex-1.w-1\/3 > div.ms-datepicker.ms-editor.hx-32 > div > input"
            ))
        )
        input_date_2.send_keys(Keys.CONTROL + "a")
        input_date_2.send_keys(Keys.DELETE)
        input_date_2.send_keys(today_str)
        print("Đã nhập ngày kết thúc!")




        time.sleep(3)
        
        
        # Tìm và bấm nút "Lọc" với class và text xác định
        btn_loc = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "body > div.ms-dropdown.ms-dropdown-menu > div > div > div.footer.mt-5 > div > div:nth-child(2) > button"
            ))
        )
        btn_loc.click()
        print("Đã bấm nút 'Lọc'!")

        time.sleep(3)

        # Tích vào dropdown phân trang để chọn option 50
        dropdown_pagination = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "#invLst > div.flex.items-center.justify-between.w-full.ms-pagination.ms-pagination-v2 > div.flex.left-pagination.align-center > div.flex.items-center.mr-2 > div > div > div"
            ))
        )
        dropdown_pagination.click()
        print("Đã tích vào dropdown phân trang!")

        time.sleep(3)

        # Chọn option 50 từ dropdown phân trang
        option_50 = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "body > div.combo-dropdown-panel.ms-dropdown > div.dropdown-body-container > ul > div > div.vue-recycle-scroller__item-wrapper > div:nth-child(3) > li > div > div"
            ))
        )
        option_50.click()
        print("Đã chọn option 50 từ dropdown phân trang!")

        time.sleep(3)

        # Bấm vào ô tích chọn tất cả hóa đơn
        checkbox_all = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "#invLst > div.ms-content--header > div > table > thead > tr > th.ms-th.multiple-cell.fix-row.ms-th-bg > label > div > span > div"
            ))
        )
        checkbox_all.click()
        print("Đã bấm vào ô tích chọn tất cả hóa đơn!")

        time.sleep(3)

        btn_download = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "#multiple-action > div:nth-child(4) > button > div.mr-2.mi.mi-24.mi-icon-download.icon-option"
            ))
        )
        btn_download.click()
        print("Đã bấm nút download!")
        
        time.sleep(3)

        # Nhập chữ "XML" vào input chỉ định
        input_xml = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "body > div.ms-popup-main.ms-popup-main > div.vdr.form-popup.inactive > div.ms-popup.placement-center > div.popup-content > div > div.content-viewer > div.ms-mgt-24px.form-item.ms-combobox-selectfile > div.ms-combobox.flex.ms-editor.control-size > input"
            ))
        )
        input_xml.send_keys(Keys.CONTROL + "a")
        input_xml.send_keys(Keys.DELETE)
        input_xml.send_keys("XML")
        input_xml.send_keys(Keys.ENTER)
        print("Đã nhập chữ 'XML' vào input!")

        time.sleep(3)

        btn_download_body = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "body > div.ms-popup-main > div.vdr.form-popup.inactive > div.ms-popup.placement-center > div.popup-footer > div > div > div.ms-button.btn-download > button > div"
            ))
        )
        btn_download_body.click()
        print("Đã bấm nút tải xuống trong popup!")
        # Chờ download hoàn tất
        time.sleep(selenium_config['download_wait_time'])

        # Lấy giá trị tổng số hóa đơn
        total_invoices_element = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "#invLst > div.flex.items-center.justify-between.w-full.ms-pagination.ms-pagination-v2 > div.flex.items-center > div > div > div.total-info > div > strong"
            ))
        )
        total_invoices = total_invoices_element.text
        print(f"Tổng số hóa đơn: {total_invoices}")

        total_split = total_invoices.split("/")

        if int(total_split[1]) > 50:
             # Bấm vào ô tích chọn tất cả hóa đơn lần nữa để bỏ tích chọn tất cả hóa đơn
            checkbox_all = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#invLst > div.ms-content--header > div > table > thead > tr > th.ms-th.multiple-cell.fix-row.ms-th-bg > label > div > span > div"
                ))
            )
            checkbox_all.click()
            print("Đã bấm vào ô tích chọn tất cả hóa đơn lần nữa để bỏ tích chọn tất cả hóa đơn!")

            time.sleep(3)
            # Bấm vào phần tử pagination để xử lý nhiều trang
            pagination_element = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#invLst > div.flex.items-center.justify-between.w-full.ms-pagination.ms-pagination-v2 > div.flex.left-pagination.align-center > div.mr-5.flex.items-center > div:nth-child(3) > div > div"
                ))
            )
            pagination_element.click()
            print("Đã bấm vào phần tử pagination!")
            time.sleep(3)

            # Bấm vào ô tích chọn tất cả hóa đơn
            checkbox_all = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#invLst > div.ms-content--header > div > table > thead > tr > th.ms-th.multiple-cell.fix-row.ms-th-bg > label > div > span > div"
                ))
            )
            checkbox_all.click()
            print("Đã bấm vào ô tích chọn tất cả hóa đơn!")

            time.sleep(3)

            btn_download = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#multiple-action > div:nth-child(4) > button > div.mr-2.mi.mi-24.mi-icon-download.icon-option"
                ))
            )
            btn_download.click()
            print("Đã bấm nút download!")
            
            time.sleep(3)

            # Nhập chữ "XML" vào input chỉ định
            input_xml = wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "body > div.ms-popup-main.ms-popup-main > div.vdr.form-popup.inactive > div.ms-popup.placement-center > div.popup-content > div > div.content-viewer > div.ms-mgt-24px.form-item.ms-combobox-selectfile > div.ms-combobox.flex.ms-editor.control-size > input"
                ))
            )
            input_xml.send_keys(Keys.CONTROL + "a")
            input_xml.send_keys(Keys.DELETE)
            input_xml.send_keys("XML")
            input_xml.send_keys(Keys.ENTER)
            print("Đã nhập chữ 'XML' vào input!")

            time.sleep(3)

            btn_download_body = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "body > div.ms-popup-main > div.vdr.form-popup.inactive > div.ms-popup.placement-center > div.popup-footer > div > div > div.ms-button.btn-download > button > div"
                ))
            )
            btn_download_body.click()
            print("Đã bấm nút tải xuống trong popup!")
            # Chờ download hoàn tất
            time.sleep(selenium_config['download_wait_time'])

        # Bấm vào nút với xpath chỉ định

    finally:
        # Đóng trình duyệt
        driver.quit()
        print("Đã đóng trình duyệt")

    time.sleep(3)

    downloads = path_config['downloads_folder']
    print(downloads)
    # Lấy tất cả các file có tên chứa "hoa_don_dau_vao"
    hoa_don_files = glob.glob(downloads + "/*hoa_don_dau_vao*")
    latest_file = []
    print(hoa_don_files)
    if hoa_don_files:
        for file in hoa_don_files:
            latest_file.append(file)
    else:
        # Fallback về file mới nhất nếu không tìm thấy file hoa_don_dau_vao
        latest_file = max(glob.glob(downloads + "/*"), key=os.path.getctime)
    print("File mới nhất:", latest_file)

    time.sleep(3)

    target_folder = path_config['target_folder']
    for file in latest_file:
        shutil.move(file, target_folder)
        print("Đã di chuyển file vào thư mục: ", os.path.basename(file))

    time.sleep(3)

    # file_path = os.path.join(target_folder, os.path.basename(latest_file))
    # with zipfile.ZipFile(file_path, 'r') as zip_ref:
    #     zip_ref.extractall(target_folder)

    hoa_don_zip_files = glob.glob(os.path.join(target_folder, "*hoa_don_dau_vao*.zip"))
    
    # Giải nén tất cả file tìm được
    for zip_file in hoa_don_zip_files:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(target_folder)
        print(f"Đã giải nén file: {os.path.basename(zip_file)}")
        time.sleep(1)
        os.remove(zip_file)
        # os.remove(zip_file)
        print("Đã xóa file zip sau khi giải nén!")
        time.sleep(1)

    # print("Đã giải nén file!")

    # Xóa file zip sau khi giải nén
    


    def xml_to_json(xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        ns = {}  # nếu có namespace thì thêm vào

        ttchung = root.find(".//TTChung", ns)
        nban = root.find(".//NBan", ns)
        nmua = root.find(".//NMua", ns)
        hhdvus = root.findall(".//HHDVu", ns)
        ttoan = root.find(".//TToan", ns)
        ghi_chu = ''
        invoice = {
            "so_hoa_don": ttchung.find("SHDon").text if ttchung.find("SHDon") is not None else '',
            "ky_hieu": ttchung.find("KHHDon").text if ttchung.find("KHHDon") is not None else '',
            "ngay_lap": ttchung.find("NLap").text if ttchung.find("NLap") is not None else '',
            "nban": {
                "ten": nban.find("Ten").text if nban.find("Ten") is not None else '',
                "mst": nban.find("MST").text if nban.find("MST") is not None else '',
                "dia_chi": nban.find("DChi").text if nban.find("DChi") is not None else '',
            },
            "nmua": {
                "ten": nmua.find("Ten").text if nmua.find("Ten") is not None else '',
                "mst": nmua.find("MST").text if nmua.find("MST") is not None else '',
                "dia_chi": nmua.find("DChi").text if nmua.find("DChi") is not None else '',
            },
            "ds_hhdv": [],
            "ghi_chu": '',
            "tong_tien": ttoan.find("TgTTTBSo").text if ttoan.find("TgTTTBSo") is not None else '',
        }

        for h in hhdvus:
            if h.find("TChat").text != "4":
                line = {
                    "ten": h.find("THHDVu").text if h.find("THHDVu") is not None else '',
                    "dvt": h.find("DVTinh").text if h.find("DVTinh") is not None else '',
                    "so_luong": h.find("SLuong").text if h.find("SLuong") is not None else '',
                    "don_gia": h.find("DGia").text if h.find("DGia") is not None else '',
                    "thanh_tien": h.find("ThTien").text if h.find("ThTien") is not None else '',
                    "thue_suat": h.find("TSuat").text if h.find("TSuat") is not None else "0%"
                }

                invoice["ds_hhdv"].append(line)
                
            if h.find("TChat").text == "4":
                ghi_chu += h.find("THHDVu").text + "\n"
            invoice["ghi_chu"] = ghi_chu
        return invoice

    # Sử dụng cấu hình Odoo từ file config
    url = odoo_config['url']
    db = odoo_config['database']
    username = odoo_config['username']
    password = odoo_config['password']

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)

    def push_invoice_to_odoo(invoice):
        ds_hhdv_ids = []
        invoice_vals = {
            "so_hoa_don": invoice["so_hoa_don"],
            "ky_hieu": invoice["ky_hieu"],
            "ngay_lap": invoice["ngay_lap"],
            "nban_ten": invoice["nban"]["ten"],
            "nban_mst": invoice["nban"]["mst"],
            "nban_dia_chi": invoice["nban"]["dia_chi"],
            "nmua_ten": invoice["nmua"]["ten"],
            "nmua_mst": invoice["nmua"]["mst"],
            "nmua_dia_chi": invoice["nmua"]["dia_chi"],
            "notes": invoice["ghi_chu"],
            "tong_tien": invoice["tong_tien"],
            "ds_hhdv_ids": ds_hhdv_ids,
        }

        for line in invoice["ds_hhdv"]:
            ds_hhdv_ids.append((
                0, 0, {
                    # "sequence": line["sequence"],
                    "ten": line["ten"],
                    "dvt": line["dvt"],
                    "so_luong": line["so_luong"],
                    "don_gia": line["don_gia"],
                    "thanh_tien": line["thanh_tien"],
                    "thue_suat": line["thue_suat"],
                }
            ))

        # Kiểm tra xem hóa đơn đã tồn tại chưa
        existing_invoice = models.execute_kw(
            db, uid, password,
            "invoice.data", "search",
            [[["so_hoa_don", "=", invoice["so_hoa_don"]]]]
        )
        
        if existing_invoice:
            print(f"Hóa đơn {invoice['so_hoa_don']} đã tồn tại với ID: {existing_invoice[0]}")
            return existing_invoice[0]

        invoice_id = models.execute_kw(
            db, uid, password,
            "invoice.data", "create",
            [invoice_vals]
        )

        
        print("Đã tạo hóa đơn Odoo ID:", invoice_id)

        try:
            models.execute_kw(
                db, uid, password,
                "invoice.data", "action_compute_m2o_lines",
                [invoice_id]
            )
        except Exception as e:
            print(f"Lỗi khi chuyển đổi M2O: {e}")
            pass

        print("Đã chuyển đổi M2O!")

        return invoice_id

    for file in os.listdir(target_folder):
        if file.endswith(".xml"):
            file_path = os.path.join(target_folder, file)
            print(file_path)
            json_data = xml_to_json(file_path)

            push_invoice_to_odoo(json_data)

            # Xóa file XML sau khi xử lý
            try:
                os.remove(file_path)
                print(f"Đã xóa file: {file}")
            except Exception as e:
                print(f"Lỗi khi xóa file {file}: {e}")

    print("Kết thức quá trình tự động!")


while True:
    try:
        print(f"🔄 Bắt đầu chu kỳ tự động hóa đơn lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        driver_chrome_auto_pull()
        print("✅ Hoàn thành chu kỳ tự động hóa đơn!")
        
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng chương trình theo yêu cầu người dùng")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Lỗi trong quá trình tự động hóa: {e}")
        print("⏳ Sẽ thử lại trong 5 tiếng...")
    
    sleep_duration = 5 * 60 * 60
    print(f"😴 Ngủ trong {sleep_duration/3600} tiếng, sẽ chạy lại lúc: {(datetime.now() + timedelta(seconds=sleep_duration)).strftime('%d/%m/%Y %H:%M:%S')}")
    time.sleep(sleep_duration)