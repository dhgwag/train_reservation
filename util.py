import datetime
import json
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import telegram, asyncio


def get_nowtime():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_db_path():
    try:
        # PyInstaller에 의해 임시폴더에서 실행될 경우 임시폴더로 접근하는 함수
        # 한 단계 상위에 db를 생성해야 삭제되지 않음
        return os.path.join(os.path.join(sys._MEIPASS, os.pardir), 'train_db.json')
    except Exception:
        return os.path.join(os.path.abspath("."), 'train_db.json')


def save_db(data):
    with open(get_db_path(), 'w', encoding='utf-8') as file:
        json.dump(data, file, indent="\t")


def load_db():
    try:
        with open(get_db_path(), 'r') as file:
            data = json.load(file)
            return data
    except:  # 파일이 없거나, dict 형태로 변환에 실패했을 경우
        return dict()


class Telegram:
    def __init__(self, token, chatid, error_callback, try_callback):
        self.error_callback = error_callback
        self.try_callback = try_callback

        self.bot = telegram.Bot(token=token)
        self.chatid = chatid

    def send_message(self, msg):
        try:
            asyncio.run(self.bot.sendMessage(chat_id=self.chatid, text=msg))
            self.try_callback(msg)
            return True
        except Exception as e:
            self.error_callback('텔레그램 발송 실패', f"{msg} 발송에 실패했습니다 - \n{e}")
            return False


class Email:
    def __init__(self, sender, passwd, receiver, error_callback, try_callback):
        self.error_callback = error_callback
        self.try_callback = try_callback
        self.gmail_smtp = "smtp.gmail.com"  # gmail smtp 주소
        self.gmail_port = 465  # gmail smtp 포트번호. 고정(변경 불가)

        # 로그인
        self.my_account = sender
        self.my_password = passwd
        self.receiver = receiver

    def send_email(self, msg):
        try:
            smtp = smtplib.SMTP_SSL(self.gmail_smtp, self.gmail_port)
            smtp.login(self.my_account, self.my_password)

            # 메일 기본 정보 설정
            message = MIMEMultipart("alternative")
            message["Subject"] = '기차표 예매 프로그램 알림 이메일'
            message["From"] = self.my_account
            message["To"] = self.receiver

            message.attach(MIMEText(msg, "plain"))

            smtp.sendmail(self.my_account, self.receiver, message.as_string())

            # smtp 서버 연결 해제
            smtp.quit()

            self.try_callback(msg)
            return True
        except Exception as e:
            self.error_callback('이메일 발송 실패', f"{msg} \n발송에 실패했습니다 - \n{e}")
            return False
