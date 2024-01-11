import datetime
import json
import os
import sys


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
