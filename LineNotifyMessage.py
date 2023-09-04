# -- coding: utf-8 --
import requests


def line_notify_message(msg):
    # 跟line申請權杖
    token = '這邊填自己的權杖token'

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {'message': msg}
    r = requests.post("https://notify-api.line.me/api/notify", headers=headers, params=payload)
    return r.status_code


if __name__ == '__main__':

    # 你要傳送的訊息內容(字串)
    message = "TEST"

    line_notify_message(message)
