import requests
import json


ODS_PAGE_SIZE = 200
DEFAULT_ODS_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

API_LIST = {
    'get_call_history': 'https://api.cloudfone.vn/api/CloudFone/GetCallLogs',
    'get_list_extension': 'https://api.cloudfone.vn/api/CloudFone/AccountsInfo'
}

STATUS_WEBHOOK_VI = {
    'Ringing': 'Đổ chuông',
    'Up': 'Nghe máy',
    'Down': 'Gác máy',
    'Ringing_Out': 'Đổ chuông',
    'Up_Out': 'Nghe máy',
    'Down_Out': 'Gác máy'
}

DIRECTION_WEBHOOK_VI = {
    'Inbound': 'Cuộc gọi vào',
    'Outbound': 'Cuộc gọi ra'
}


class ODS:
    request_data = {}
    response_data = {}

    def get_call_history_v2(self, **kwargs):
        url = API_LIST.get('get_call_history')
        payload = json.dumps(self.request_data)
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return response

    def get_list_extension(self, **kwargs):
        url = API_LIST.get('get_list_extension')
        payload = json.dumps(self.request_data)
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return response
