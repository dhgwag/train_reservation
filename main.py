# pyinstaller -F -w -n 기차표예매 -i icon.ico main.py --add-binary "img/qr.png:img"

import time

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QTableWidgetItem, QRadioButton, QWidget, QHBoxLayout, QMessageBox

from design import Ui_dialog
from train.ktx import KTX
from train.srt import SRT

from util import *

version = '6.0.0'


class SrtThread(QThread):
    reservation_func = pyqtSignal()
    update_ctr_signal = pyqtSignal(int)
    fetch_schedule = pyqtSignal()
    check_waiting = pyqtSignal()

    def __init__(self, parent, action="reservation"):
        super().__init__(parent)
        self.parent = parent
        self.action = action
        self.running = False

    def isRunning(self):
        return self.running

    def stop(self):
        self.running = False
        self.quit()
        self.wait(3000)     # 종료 대기

    def run(self):
        self.running = True
        if self.action == "reservation":
            ctr = 0

            while self.running:
                ctr += 1
                self.reservation_func.emit()
                self.update_ctr_signal.emit(ctr)
                time.sleep(float(self.parent.main_ui.doubleSpinBox_srt_delay.text()))
        elif self.action == "fetch_schedule":
            while self.running:
                self.check_waiting.emit()
                time.sleep(1)

            self.fetch_schedule.emit()


class KtxThread(QThread):
    reservation_func = pyqtSignal()
    update_ctr_signal = pyqtSignal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.running = False

    def isRunning(self):
        return self.running

    def stop(self):
        self.running = False
        self.quit()
        self.wait(3000)     # 종료 대기

    def run(self):
        self.running = True
        ctr = 0

        while self.running:
            ctr += 1
            self.reservation_func.emit()
            self.update_ctr_signal.emit(ctr)
            time.sleep(float(self.parent.main_ui.doubleSpinBox_ktx_delay.text()))


class UiMainClass(QDialog):
    def __init__(self):
        self.max_error_log = 20
        self.max_try_log = 100

        self.srt = SRT(self.error_callback, self.srt_try_callback)
        self.srt_stations = self.srt.get_stations()
        self.srt_thread = None
        self.srt_schedule_thread = None
        self.dot_cnt = 0

        self.srt_radiobuttons = []
        self.srt_schedules = []

        self.srt_reservation_list = []
        self.srt_reservation_idx = 0
        self.srt_waiting_key = ""

        self.ktx = KTX(self.error_callback, self.ktx_try_callback)
        self.ktx_stations = self.ktx.get_stations()
        self.ktx_thread = None

        self.ktx_radiobuttons = []
        self.ktx_schedules = []

        self.ktx_reservation_list = []
        self.ktx_reservation_idx = 0

        self.db = load_db()

        QDialog.__init__(self)
        # UI 선언
        self.main_ui = Ui_dialog()
        # UI 준비
        self.main_ui.setupUi(self)
        self.init_ui()
        # 화면을 보여준다.
        self.show()

    def init_ui(self):
        self.main_ui.label_version.setText(version)
        self.main_ui.label_srt_logged_in.hide()
        self.main_ui.label_ktx_logged_in.hide()

        ### SRT ###
        # db에 데이터가 있는 경우 불러오기
        if 'srt_login_type' in self.db.keys():
            if self.db['srt_login_type'] == 0 or self.db['srt_login_type'] == 1 or self.db['srt_login_type'] == 2:
                self.main_ui.comboBox_srt_login_type.setCurrentIndex(self.db['srt_login_type'])
        if 'srt_id' in self.db.keys():
            self.main_ui.lineEdit_srt_id.setText(self.db['srt_id'])
        if 'srt_pwd' in self.db.keys():
            self.main_ui.lineEdit_srt_pwd.setText(self.db['srt_pwd'])
        if 'srt_save_login_info' in self.db.keys() and self.db['srt_save_login_info']:
            self.main_ui.checkBox_srt_save_login.setChecked(True)

        self.main_ui.comboBox_srt_adult.setCurrentIndex(1)
        self.main_ui.comboBox_srt_dpt_stn.addItems(self.srt_stations.keys())
        self.main_ui.comboBox_srt_arv_stn.addItems(self.srt_stations.keys())
        self.main_ui.comboBox_srt_arv_stn.setCurrentIndex(1)

        self.main_ui.dateTimeEdit_srt_time.setDateTime(datetime.datetime.now())

        self.main_ui.pushButton_srt_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")

        self.main_ui.pushButton_donation.clicked.connect(self.pushButton_donation_clicked)

        # 로그인 타입 변경
        self.main_ui.comboBox_srt_login_type.currentIndexChanged.connect(self.comboBox_srt_login_type_changed)
        # 로그인
        self.main_ui.pushButton_srt_login.clicked.connect(self.pushButton_srt_login_clicked)
        # 열차 조회
        self.main_ui.pushButton_srt_search.clicked.connect(self.pushButton_srt_search_clicked)
        # 열차 예매
        self.main_ui.pushButton_srt_reservation.clicked.connect(self.pushButton_srt_reservation_clicked)

        ### KTX ###
        # db에 데이터가 있는 경우 불러오기
        if 'ktx_login_type' in self.db.keys():
            if self.db['ktx_login_type'] == 0 or self.db['ktx_login_type'] == 1 or self.db['ktx_login_type'] == 2:
                self.main_ui.comboBox_ktx_login_type.setCurrentIndex(self.db['ktx_login_type'])
        if 'ktx_id' in self.db.keys():
            self.main_ui.lineEdit_ktx_id.setText(self.db['ktx_id'])
        if 'ktx_pwd' in self.db.keys():
            self.main_ui.lineEdit_ktx_pwd.setText(self.db['ktx_pwd'])
        if 'ktx_save_login_info' in self.db.keys() and self.db['ktx_save_login_info']:
            self.main_ui.checkBox_ktx_save_login.setChecked(True)

        self.main_ui.comboBox_ktx_adult.setCurrentIndex(1)
        self.main_ui.comboBox_ktx_dpt_stn.addItems(self.ktx_stations.keys())
        self.main_ui.comboBox_ktx_arv_stn.addItems(self.ktx_stations.keys())
        self.main_ui.comboBox_ktx_arv_stn.setCurrentIndex(1)

        self.main_ui.dateTimeEdit_ktx_time.setDateTime(datetime.datetime.now())

        self.main_ui.pushButton_ktx_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")

        # 로그인 타입 변경
        self.main_ui.comboBox_ktx_login_type.currentIndexChanged.connect(self.comboBox_ktx_login_type_changed)
        # 로그인
        self.main_ui.pushButton_ktx_login.clicked.connect(self.pushButton_ktx_login_clicked)
        # 열차 조회
        self.main_ui.pushButton_ktx_search.clicked.connect(self.pushButton_ktx_search_clicked)
        # 열차 예매
        self.main_ui.pushButton_ktx_reservation.clicked.connect(self.pushButton_ktx_reservation_clicked)

        ### Settings
        if 'max_error_log' in self.db.keys():
            try:
                self.db['max_error_log'] = int(self.db['max_error_log'])
                self.max_error_log = self.db['max_error_log']
            except:
                self.error_callback("DB 로드 실패", f"max_error_log - {self.db['max_error_log']}")
        if 'max_try_log' in self.db.keys():
            try:
                self.db['max_try_log'] = int(self.db['max_try_log'])
                self.max_try_log = self.db['max_try_log']
            except:
                self.error_callback("DB 로드 실패", f"max_try_log - {self.db['max_try_log']}")
        self.main_ui.lineEdit_max_error_log.setText(str(self.max_error_log))
        self.main_ui.lineEdit_max_try_log.setText(str(self.max_try_log))

        self.main_ui.pushButton_settings_save.clicked.connect(self.pushButton_settings_save_clicked)

        ### Telegram
        if 'telegram_enable' in self.db.keys() and self.db['telegram_enable']:
            self.main_ui.checkBox_telegram_enable.setChecked(True)
        if 'telegram_token' in self.db.keys():
            self.main_ui.lineEdit_telegram_token.setText(self.db['telegram_token'])
        if 'telegram_chatid' in self.db.keys():
            self.main_ui.lineEdit_telegram_chatid.setText(self.db['telegram_chatid'])

        self.main_ui.pushButton_telegram_test.clicked.connect(self.pushButton_telegram_test_clicked)
        self.main_ui.pushButton_telegram_save.clicked.connect(self.pushButton_telegram_save_clicked)

        ### Email
        if 'email_enable' in self.db.keys() and self.db['email_enable']:
            self.main_ui.checkBox_email_enable.setChecked(True)
        if 'email_sender' in self.db.keys():
            self.main_ui.lineEdit_email_sender.setText(self.db['email_sender'])
        if 'email_passwd' in self.db.keys():
            self.main_ui.lineEdit_email_passwd.setText(self.db['email_passwd'])
        if 'email_receiver' in self.db.keys():
            self.main_ui.lineEdit_email_receiver.setText(self.db['email_receiver'])

        self.main_ui.pushButton_email_test.clicked.connect(self.pushButton_email_test_clicked)
        self.main_ui.pushButton_email_save.clicked.connect(self.pushButton_email_save_clicked)

    def pushButton_donation_clicked(self):
        dialog = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel()
        lay.addWidget(label)

        img_path = ""
        if os.path.exists("img/qr.png"):
            img_path = "img/qr.png"
        try:
            if os.path.exists(os.path.join(sys._MEIPASS, "img/qr.png")):
                img_path = os.path.join(sys._MEIPASS, "img/qr.png")
        except:
            pass
        pixmap = QtGui.QPixmap(img_path)
        pixmap.scaledToWidth(100)
        label.setPixmap(pixmap)
        dialog.exec_()

    def pushButton_settings_save_clicked(self):
        try:
            max_error_log_tmp = int(self.main_ui.lineEdit_max_error_log.text())
            self.main_ui.lineEdit_max_error_log.setText(str(max_error_log_tmp))
            self.db['max_error_log'] = max_error_log_tmp
        except:
            self.error_callback("DB 저장 실패", f"최대 에러 로그 - {self.main_ui.lineEdit_max_error_log.text()}")
            return False
        try:
            max_try_log_tmp = int(self.main_ui.lineEdit_max_try_log.text())
            self.main_ui.lineEdit_max_try_log.setText(str(max_try_log_tmp))
            self.db['max_try_log'] = max_try_log_tmp
        except:
            self.error_callback("DB 저장 실패", f"최대 예매 로그 - {self.main_ui.lineEdit_max_try_log.text()}")
            return False

        save_db(self.db)
        QMessageBox.about(self, '저장 완료', '저장 완료')

    def pushButton_telegram_test_clicked(self):
        token = self.main_ui.lineEdit_telegram_token.text()
        chatid = self.main_ui.lineEdit_telegram_chatid.text()

        telegram_ = Telegram(token, chatid, self.error_callback, self.telegram_try_callback)
        if telegram_.send_message("기차 예매 프로그램 테스트 메세지입니다"):
            QMessageBox.about(self, '테스트 성공', '텔레그램 발송 성공')
        else:
            QMessageBox.about(self, '테스트 실패', '텔레그램 발송 실패')

    def pushButton_telegram_save_clicked(self):
        self.db['telegram_enable'] = self.main_ui.checkBox_telegram_enable.isChecked()
        self.db['telegram_token'] = self.main_ui.lineEdit_telegram_token.text()
        self.db['telegram_chatid'] = self.main_ui.lineEdit_telegram_chatid.text()

        save_db(self.db)
        QMessageBox.about(self, '저장 완료', '저장 완료')

    def telegram_try_callback(self, msg):
        self.main_ui.tableWidget_telegram_try.insertRow(0)
        self.main_ui.tableWidget_telegram_try.setItem(0, 0, QTableWidgetItem(get_nowtime()))
        self.main_ui.tableWidget_telegram_try.setItem(0, 1, QTableWidgetItem(msg))

        self.main_ui.tableWidget_telegram_try.resizeColumnToContents(0)
        self.main_ui.tableWidget_telegram_try.resizeRowsToContents()

    def pushButton_email_test_clicked(self):
        sender = self.main_ui.lineEdit_email_sender.text() + "@gmail.com"
        passwd = self.main_ui.lineEdit_email_passwd.text()
        receiver = self.main_ui.lineEdit_email_receiver.text()

        email_ = Email(sender, passwd, receiver, self.error_callback, self.email_try_callback)
        if email_.send_email("기차 예매 프로그램 테스트 이메일입니다"):
            QMessageBox.about(self, '테스트 성공', '이메일 발송 성공')
        else:
            QMessageBox.about(self, '테스트 실패', '이메일 발송 실패')

    def pushButton_email_save_clicked(self):
        self.db['email_enable'] = self.main_ui.checkBox_email_enable.isChecked()
        self.db['email_sender'] = self.main_ui.lineEdit_email_sender.text()
        self.db['email_passwd'] = self.main_ui.lineEdit_email_passwd.text()
        self.db['email_receiver'] = self.main_ui.lineEdit_email_receiver.text()

        save_db(self.db)
        QMessageBox.about(self, '저장 완료', '저장 완료')

    def email_try_callback(self, msg):
        self.main_ui.tableWidget_email_try.insertRow(0)
        self.main_ui.tableWidget_email_try.setItem(0, 0, QTableWidgetItem(get_nowtime()))
        self.main_ui.tableWidget_email_try.setItem(0, 1, QTableWidgetItem(msg))

        self.main_ui.tableWidget_email_try.resizeColumnToContents(0)
        self.main_ui.tableWidget_email_try.resizeRowsToContents()

    def send_success_message(self, msg):
        if self.main_ui.checkBox_telegram_enable.isChecked():       # 텔레그램 발송
            token = self.main_ui.lineEdit_telegram_token.text()
            chatid = self.main_ui.lineEdit_telegram_chatid.text()

            telegram_ = Telegram(token, chatid, self.error_callback, self.telegram_try_callback)
            telegram_.send_message(msg)

        if self.main_ui.checkBox_email_enable.isChecked():          # 이메일 발송
            sender = self.main_ui.lineEdit_email_sender.text() + "@gmail.com"
            passwd = self.main_ui.lineEdit_email_passwd.text()
            receiver = self.main_ui.lineEdit_email_receiver.text()

            email_ = Email(sender, passwd, receiver, self.error_callback, self.email_try_callback)
            email_.send_email(msg)

    def comboBox_srt_login_type_changed(self):
        self.main_ui.label_srt_id.setText(self.main_ui.comboBox_srt_login_type.currentText())

    def pushButton_srt_login_clicked(self):
        login_type = self.main_ui.comboBox_srt_login_type.currentIndex()
        srt_id = self.main_ui.lineEdit_srt_id.text()
        srt_pwd = self.main_ui.lineEdit_srt_pwd.text()

        if self.srt.login(str(login_type + 1), srt_id, srt_pwd):
            # 로그인 성공
            self.main_ui.groupBox_srt_login.hide()
            self.main_ui.label_srt_logged_in.setText(f'로그인 계정 : {srt_id}')
            self.main_ui.label_srt_logged_in.show()

            if self.main_ui.checkBox_srt_save_login.isChecked():
                # 로그인 정보 저장
                self.db['srt_login_type'] = login_type
                self.db['srt_id'] = srt_id
                self.db['srt_pwd'] = srt_pwd
                self.db['srt_save_login_info'] = True
            else:
                # 로그인 정보 삭제
                self.db['srt_login_type'] = 0
                self.db['srt_id'] = ''
                self.db['srt_pwd'] = ''
                self.db['srt_save_login_info'] = False
            save_db(self.db)

    def pushButton_srt_search_clicked(self):
        if not self.srt_schedule_thread:
            self.srt_schedule_thread = SrtThread(self, "fetch_schedule")
            self.srt_schedule_thread.fetch_schedule.connect(self.srt_fetch_schedule_func)
            self.srt_schedule_thread.check_waiting.connect(self.srt_check_waiting_func)

        if not self.srt_schedule_thread.isRunning():
            self.main_ui.pushButton_srt_search.setText('조회 중...')
            self.srt_schedule_thread.start()

    def pushButton_srt_reservation_clicked(self):
        if not self.srt_thread:
            self.srt_thread = SrtThread(self)
            self.srt_thread.reservation_func.connect(self.srt_reservation_func)
            self.srt_thread.update_ctr_signal.connect(self.srt_update_ctr)

        if self.srt_thread.isRunning():     # 동작 중일 때
            self.srt_thread.stop()
            self.main_ui.pushButton_srt_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")
            self.main_ui.pushButton_srt_reservation.setText('예매시작')
        else:                   # 동작 중 아닐 때
            self.main_ui.tableWidget_srt_try_log.setRowCount(0)
            self.srt_reservation_list = []
            self.srt_reservation_idx = 0
            adult = self.main_ui.comboBox_srt_adult.currentIndex()
            child = self.main_ui.comboBox_srt_child.currentIndex()
            senior = self.main_ui.comboBox_srt_senior.currentIndex()
            svrDsb = self.main_ui.comboBox_srt_svrDsb.currentIndex()
            mldDsb = self.main_ui.comboBox_srt_mldDsb.currentIndex()

            for idx, radiobutton in enumerate(self.srt_radiobuttons):
                if radiobutton.isChecked():
                    class_idx = self.main_ui.comboBox_srt_class.currentIndex()
                    if class_idx == 0 or class_idx == 2:
                        self.srt_reservation_list.append({
                            'adult': adult,
                            'child': child,
                            'senior': senior,
                            'svrDsb': svrDsb,
                            'mldDsb': mldDsb,
                            'train_schedule': self.srt_schedules[idx],
                            'locSeatAttCd': self.get_srt_locSeatAttCd(),
                            'rqSeatAttCd': self.get_srt_rqSeatAttCd(),
                            'isReservation': self.main_ui.radioButton_srt_waiting.isChecked(),
                            'isBusiness': False,
                        })
                    if class_idx == 1 or class_idx == 2:
                        self.srt_reservation_list.append({
                            'adult': adult,
                            'child': child,
                            'senior': senior,
                            'svrDsb': svrDsb,
                            'mldDsb': mldDsb,
                            'train_schedule': self.srt_schedules[idx],
                            'locSeatAttCd': self.get_srt_locSeatAttCd(),
                            'rqSeatAttCd': self.get_srt_rqSeatAttCd(),
                            'isReservation': self.main_ui.radioButton_srt_waiting.isChecked(),
                            'isBusiness': True,
                        })

            if not self.srt.is_logged_in():
                self.error_callback('SRT 예매 실패', '로그인을 먼저 해주세요')
                self.main_ui.groupBox_srt_login.show()
                self.main_ui.label_srt_logged_in.hide()
                return False
            if adult + child + senior + svrDsb + mldDsb < 1:
                self.error_callback('SRT 예매 실패', '인원을 선택해주세요')
                return False
            if not self.srt_schedules:
                self.error_callback('SRT 예매 실패', '열차 조회를 먼저 해주세요')
                return False
            if not self.srt_reservation_list:
                self.error_callback('SRT 예매 실패', '선택된 열차가 없습니다')
                return False

            self.srt_thread.start()
            self.main_ui.pushButton_srt_reservation.setStyleSheet("QPushButton{background-color : red;}")
            self.main_ui.pushButton_srt_reservation.setText('예매중지')

    def srt_check_waiting_func(self):
        waiting_exists, nwait, key = self.srt.check_waiting(self.srt_waiting_key)
        self.srt_waiting_key = key
        if waiting_exists:
            self.main_ui.pushButton_srt_search.setText(f'조회 중{"."*(self.dot_cnt+1)}(대기 인원 : {nwait}명)')
            self.dot_cnt = (self.dot_cnt+1) % 3
        else:
            self.srt_schedule_thread.stop()

    def srt_fetch_schedule_func(self):
        dptRsStnCdNm = self.main_ui.comboBox_srt_dpt_stn.currentText()
        arvRsStnCdNm = self.main_ui.comboBox_srt_arv_stn.currentText()
        dptDt = self.main_ui.dateTimeEdit_srt_time.date().toString('yyyyMMdd')
        dptTm = self.main_ui.dateTimeEdit_srt_time.time().toString('HHmmss')
        adult = self.main_ui.comboBox_srt_adult.currentIndex()
        child = self.main_ui.comboBox_srt_child.currentIndex()
        senior = self.main_ui.comboBox_srt_senior.currentIndex()
        svrDsb = self.main_ui.comboBox_srt_svrDsb.currentIndex()
        mldDsb = self.main_ui.comboBox_srt_mldDsb.currentIndex()
        chtnDvCd = '1'  # 직통
        locSeatAttCd1 = self.get_srt_locSeatAttCd()
        rqSeatAttCd1 = self.get_srt_rqSeatAttCd()
        trnGpCd = '300' # SRT
        dlayTnumAplFlg = 'Y'

        if dptRsStnCdNm == arvRsStnCdNm:
            self.error_callback('SRT 열차 조회 실패', '출발역과 도착역이 같습니다')
            return False
        self.srt_schedules = self.srt.fetch_schedule(dptRsStnCdNm, arvRsStnCdNm, dptDt, dptTm, adult, child, senior, svrDsb,
                                                     mldDsb, chtnDvCd, locSeatAttCd1, rqSeatAttCd1, trnGpCd,
                                                     dlayTnumAplFlg, self.srt_waiting_key)
        self.srt_waiting_key = ""
        # 기차 스케쥴 초기화
        self.srt_radiobuttons = []
        self.main_ui.tableWidget_srt_schedule.setRowCount(0)

        if len(self.srt_schedules) == 0:
            self.error_callback('SRT 열차 없음', '검색된 열차가 없습니다')

        for idx, schedule in enumerate(self.srt_schedules):
            dptTm = schedule['dptTm'][0:2] + ':' + schedule['dptTm'][2:4]

            self.main_ui.tableWidget_srt_schedule.insertRow(idx)
            self.main_ui.tableWidget_srt_schedule.setItem(idx, 0, QTableWidgetItem(str(int(schedule['trnNo']))))
            self.main_ui.tableWidget_srt_schedule.setItem(idx, 1, QTableWidgetItem(schedule['dptRsStnCdNm']))
            self.main_ui.tableWidget_srt_schedule.setItem(idx, 2, QTableWidgetItem(schedule['arvRsStnCdNm']))
            self.main_ui.tableWidget_srt_schedule.setItem(idx, 3, QTableWidgetItem(dptTm))

            self.main_ui.tableWidget_srt_schedule.item(idx, 0).setTextAlignment(Qt.AlignCenter)
            self.main_ui.tableWidget_srt_schedule.item(idx, 1).setTextAlignment(Qt.AlignCenter)
            self.main_ui.tableWidget_srt_schedule.item(idx, 2).setTextAlignment(Qt.AlignCenter)
            self.main_ui.tableWidget_srt_schedule.item(idx, 3).setTextAlignment(Qt.AlignCenter)

            radiobutton = QRadioButton()
            radiobutton.setAutoExclusive(False)
            self.srt_radiobuttons.append(radiobutton)
            cellWidget = QWidget()
            layoutCB = QHBoxLayout(cellWidget)
            layoutCB.addWidget(self.srt_radiobuttons[-1])
            layoutCB.setAlignment(Qt.AlignCenter)
            layoutCB.setContentsMargins(0, 0, 0, 0)
            cellWidget.setLayout(layoutCB)

            self.main_ui.tableWidget_srt_schedule.setCellWidget(idx, 4, cellWidget)
        self.main_ui.pushButton_srt_search.setText('조회')

    def srt_reservation_func(self):
        while True:
            waiting_exists, nwait, key = self.srt.check_booking(self.srt_waiting_key)
            self.srt_waiting_key = key
            if waiting_exists:
                time.sleep(1)
            else:
                break

        rsv_item = self.srt_reservation_list[self.srt_reservation_idx]
        success = self.srt.book_ticket(
            self.srt_waiting_key,
            rsv_item['adult'],
            rsv_item['child'],
            rsv_item['senior'],
            rsv_item['svrDsb'],
            rsv_item['mldDsb'],
            rsv_item['train_schedule'],
            rsv_item['locSeatAttCd'],
            rsv_item['rqSeatAttCd'],
            rsv_item['isReservation'],
            rsv_item['isBusiness'],
        )
        self.srt_waiting_key = ""

        self.srt_reservation_idx = (self.srt_reservation_idx+1) % len(self.srt_reservation_list)

        if success:
            self.srt_thread.stop()
            self.main_ui.pushButton_srt_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")
            self.main_ui.pushButton_srt_reservation.setText('예매시작')

            self.send_success_message('SRT 예매 성공\n\n10분 내에 SRT 앱에서 결제해주세요')
            QMessageBox.about(self, 'SRT 예매 성공', '10분 내에 SRT 앱에서 결제해주세요')

    def srt_update_ctr(self, ctr):
        self.main_ui.lcdNumber_srt_ctr.display(ctr)

    def srt_try_callback(self, success, reason, detail_info):
        self.main_ui.tableWidget_srt_try_log.insertRow(0)
        self.main_ui.tableWidget_srt_try_log.setItem(0, 0, QTableWidgetItem(get_nowtime()))
        self.main_ui.tableWidget_srt_try_log.setItem(0, 1, QTableWidgetItem("성공" if success else "실패"))
        self.main_ui.tableWidget_srt_try_log.setItem(0, 2, QTableWidgetItem(reason))
        self.main_ui.tableWidget_srt_try_log.setItem(0, 3, QTableWidgetItem(detail_info))

        # 일정 개수 이상 로그가 쌓이면 삭제
        if self.main_ui.tableWidget_srt_try_log.rowCount() > self.max_try_log:
            self.main_ui.tableWidget_srt_try_log.removeRow(self.max_try_log)

        self.main_ui.tableWidget_srt_try_log.resizeColumnToContents(0)
        self.main_ui.tableWidget_srt_try_log.resizeColumnToContents(1)
        self.main_ui.tableWidget_srt_try_log.resizeColumnToContents(2)
        self.main_ui.tableWidget_srt_try_log.resizeRowsToContents()

    def get_srt_locSeatAttCd(self): # 좌석 위치
        idx = self.main_ui.comboBox_srt_locSeatAttCd.currentIndex()
        if idx == 0:
            return "000"    # default
        elif idx == 1:
            return "011"    # 1인석
        elif idx == 2:
            return "012"    # 창측좌석
        elif idx == 3:
            return "013"    # 내측좌석
        else:
            self.error_callback('SRT 좌석 위치 인덱스 에러', f"인덱스 - {idx}")
            return "000"

    def get_srt_rqSeatAttCd(self):  # 좌석 종류
        idx = self.main_ui.comboBox_srt_rqSeatAttCd.currentIndex()
        if idx == 0:
            return "015"    # 일반
        elif idx == 1:
            return "021"    # 휠체어
        elif idx == 2:
            return "028"    # 전동휠체어
        else:
            self.error_callback('SRT 좌석 종류 인덱스 에러', f"인덱스 - {idx}")
            return "015"    # 일반

    def comboBox_ktx_login_type_changed(self):
        self.main_ui.label_ktx_id.setText(self.main_ui.comboBox_ktx_login_type.currentText())

    def pushButton_ktx_login_clicked(self):
        login_type = self.main_ui.comboBox_ktx_login_type.currentIndex()
        ktx_id = self.main_ui.lineEdit_ktx_id.text()
        ktx_pwd = self.main_ui.lineEdit_ktx_pwd.text()

        if self.ktx.login(str(login_type), ktx_id, ktx_pwd):
            # 로그인 성공
            self.main_ui.groupBox_ktx_login.hide()
            self.main_ui.label_ktx_logged_in.setText(f'로그인 계정 : {ktx_id}')
            self.main_ui.label_ktx_logged_in.show()

            if self.main_ui.checkBox_ktx_save_login.isChecked():
                # 로그인 정보 저장
                self.db['ktx_login_type'] = login_type
                self.db['ktx_id'] = ktx_id
                self.db['ktx_pwd'] = ktx_pwd
                self.db['ktx_save_login_info'] = True
            else:
                # 로그인 정보 삭제
                self.db['ktx_login_type'] = 0
                self.db['ktx_id'] = ''
                self.db['ktx_pwd'] = ''
                self.db['ktx_save_login_info'] = False
            save_db(self.db)

    def pushButton_ktx_search_clicked(self):
        txtGoStart = self.main_ui.comboBox_ktx_dpt_stn.currentText()
        txtGoEnd = self.main_ui.comboBox_ktx_arv_stn.currentText()
        txtGoAbrdDt = self.main_ui.dateTimeEdit_ktx_time.date().toString('yyyyMMdd')
        txtGoHour = self.main_ui.dateTimeEdit_ktx_time.time().toString('HHmmss')
        adult = self.main_ui.comboBox_ktx_adult.currentIndex()
        child = self.main_ui.comboBox_ktx_child.currentIndex()
        baby = self.main_ui.comboBox_ktx_baby.currentIndex()
        senior = self.main_ui.comboBox_ktx_senior.currentIndex()
        svrDsb = self.main_ui.comboBox_ktx_svrDsb.currentIndex()
        mldDsb = self.main_ui.comboBox_ktx_mldDsb.currentIndex()
        radJobId = '1'  # 직통
        txtSeatAttCd_3 = self.get_ktx_txtSeatAttCd_3()
        txtSeatAttCd_2 = self.get_ktx_txtSeatAttCd_2()
        txtSeatAttCd_4 = self.get_ktx_txtSeatAttCd_4()
        selGoTrain = '00'   # KTX

        if txtGoStart == txtGoEnd:
            self.error_callback('KTX 열차 조회 실패', '출발역과 도착역이 같습니다')
            return False
        self.ktx_schedules = self.ktx.fetch_schedule(txtGoStart, txtGoEnd, txtGoAbrdDt, txtGoHour, adult, child, baby,
                                                     senior, svrDsb, mldDsb, radJobId, txtSeatAttCd_3, txtSeatAttCd_2,
                                                     txtSeatAttCd_4, selGoTrain)

        # 기차 스케쥴 초기화
        self.ktx_radiobuttons = []
        self.main_ui.tableWidget_ktx_schedule.setRowCount(0)

        if len(self.ktx_schedules) == 0:
            self.error_callback('KTX 열차 없음', '검색된 열차가 없습니다')

        for idx, schedule in enumerate(self.ktx_schedules):
            dptTm = schedule['h_dpt_tm'][0:2] + ':' + schedule['h_dpt_tm'][2:4]

            self.main_ui.tableWidget_ktx_schedule.insertRow(idx)
            self.main_ui.tableWidget_ktx_schedule.setItem(idx, 0, QTableWidgetItem(str(int(schedule['h_trn_no']))))
            self.main_ui.tableWidget_ktx_schedule.setItem(idx, 1, QTableWidgetItem(schedule['h_dpt_rs_stn_cd_nm']))
            self.main_ui.tableWidget_ktx_schedule.setItem(idx, 2, QTableWidgetItem(schedule['h_arv_rs_stn_cd_nm']))
            self.main_ui.tableWidget_ktx_schedule.setItem(idx, 3, QTableWidgetItem(dptTm))

            self.main_ui.tableWidget_ktx_schedule.item(idx, 0).setTextAlignment(Qt.AlignCenter)
            self.main_ui.tableWidget_ktx_schedule.item(idx, 1).setTextAlignment(Qt.AlignCenter)
            self.main_ui.tableWidget_ktx_schedule.item(idx, 2).setTextAlignment(Qt.AlignCenter)
            self.main_ui.tableWidget_ktx_schedule.item(idx, 3).setTextAlignment(Qt.AlignCenter)

            radiobutton = QRadioButton()
            radiobutton.setAutoExclusive(False)
            self.ktx_radiobuttons.append(radiobutton)
            cellWidget = QWidget()
            layoutCB = QHBoxLayout(cellWidget)
            layoutCB.addWidget(self.ktx_radiobuttons[-1])
            layoutCB.setAlignment(Qt.AlignCenter)
            layoutCB.setContentsMargins(0, 0, 0, 0)
            cellWidget.setLayout(layoutCB)

            self.main_ui.tableWidget_ktx_schedule.setCellWidget(idx, 4, cellWidget)

    def pushButton_ktx_reservation_clicked(self):
        if not self.ktx_thread:
            self.ktx_thread = KtxThread(self)
            self.ktx_thread.reservation_func.connect(self.ktx_reservation_func)
            self.ktx_thread.update_ctr_signal.connect(self.ktx_update_ctr)

        if self.ktx_thread.isRunning():     # 동작 중일 때
            self.ktx_thread.stop()
            self.main_ui.pushButton_ktx_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")
            self.main_ui.pushButton_ktx_reservation.setText('예매시작')
        else:                   # 동작 중 아닐 때
            self.main_ui.tableWidget_ktx_try_log.setRowCount(0)
            self.ktx_reservation_list = []
            self.ktx_reservation_idx = 0
            adult = self.main_ui.comboBox_ktx_adult.currentIndex()
            child = self.main_ui.comboBox_ktx_child.currentIndex()
            baby = self.main_ui.comboBox_ktx_baby.currentIndex()
            senior = self.main_ui.comboBox_ktx_senior.currentIndex()
            svrDsb = self.main_ui.comboBox_ktx_svrDsb.currentIndex()
            mldDsb = self.main_ui.comboBox_ktx_mldDsb.currentIndex()

            for idx, radiobutton in enumerate(self.ktx_radiobuttons):
                if radiobutton.isChecked():
                    class_idx = self.main_ui.comboBox_ktx_class.currentIndex()
                    if class_idx == 0 or class_idx == 2:
                        self.ktx_reservation_list.append({
                            'adult': adult,
                            'child': child,
                            'baby': baby,
                            'senior': senior,
                            'svrDsb': svrDsb,
                            'mldDsb': mldDsb,
                            'train_schedule': self.ktx_schedules[idx],
                            'txtSeatAttCd_3': self.get_ktx_txtSeatAttCd_3(),
                            'txtSeatAttCd_2': self.get_ktx_txtSeatAttCd_2(),
                            'txtSeatAttCd_4': self.get_ktx_txtSeatAttCd_4(),
                            'isReservation': self.main_ui.radioButton_ktx_waiting.isChecked(),
                            'isBusiness': False,
                        })
                    if class_idx == 1 or class_idx == 2:
                        self.ktx_reservation_list.append({
                            'adult': adult,
                            'child': child,
                            'baby': baby,
                            'senior': senior,
                            'svrDsb': svrDsb,
                            'mldDsb': mldDsb,
                            'train_schedule': self.ktx_schedules[idx],
                            'txtSeatAttCd_3': self.get_ktx_txtSeatAttCd_3(),
                            'txtSeatAttCd_2': self.get_ktx_txtSeatAttCd_2(),
                            'txtSeatAttCd_4': self.get_ktx_txtSeatAttCd_4(),
                            'isReservation': self.main_ui.radioButton_ktx_waiting.isChecked(),
                            'isBusiness': True,
                        })

            if not self.ktx.is_logged_in():
                self.error_callback('KTX 예매 실패', '로그인을 먼저 해주세요')
                self.main_ui.groupBox_ktx_login.show()
                self.main_ui.label_ktx_logged_in.hide()
                return False
            if adult + child + baby + senior + svrDsb + mldDsb < 1:
                self.error_callback('KTX 예매 실패', '인원을 선택해주세요')
                return False
            if not self.ktx_schedules:
                self.error_callback('KTX 예매 실패', '열차 조회를 먼저 해주세요')
                return False
            if not self.ktx_reservation_list:
                self.error_callback('KTX 예매 실패', '선택된 열차가 없습니다')
                return False

            self.ktx_thread.start()
            self.main_ui.pushButton_ktx_reservation.setStyleSheet("QPushButton{background-color : red;}")
            self.main_ui.pushButton_ktx_reservation.setText('예매중지')

    def ktx_reservation_func(self):
        rsv_item = self.ktx_reservation_list[self.ktx_reservation_idx]
        success = self.ktx.book_ticket(
            rsv_item['adult'],
            rsv_item['child'],
            rsv_item['baby'],
            rsv_item['senior'],
            rsv_item['svrDsb'],
            rsv_item['mldDsb'],
            rsv_item['train_schedule'],
            rsv_item['txtSeatAttCd_3'],
            rsv_item['txtSeatAttCd_2'],
            rsv_item['txtSeatAttCd_4'],
            rsv_item['isReservation'],
            rsv_item['isBusiness'],
        )

        self.ktx_reservation_idx = (self.ktx_reservation_idx+1) % len(self.ktx_reservation_list)

        if success:
            self.ktx_thread.stop()
            self.main_ui.pushButton_ktx_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")
            self.main_ui.pushButton_ktx_reservation.setText('예매시작')

            self.send_success_message('KTX 예매 성공\n\n20분 내에 KTX 홈페이지에서 결제해주세요')
            QMessageBox.about(self, 'KTX 예매 성공', '20분 내에 KTX 홈페이지에서 결제해주세요')

    def ktx_update_ctr(self, ctr):
        self.main_ui.lcdNumber_ktx_ctr.display(ctr)

    def ktx_try_callback(self, success, reason, detail_info):
        self.main_ui.tableWidget_ktx_try_log.insertRow(0)
        self.main_ui.tableWidget_ktx_try_log.setItem(0, 0, QTableWidgetItem(get_nowtime()))
        self.main_ui.tableWidget_ktx_try_log.setItem(0, 1, QTableWidgetItem("성공" if success else "실패"))
        self.main_ui.tableWidget_ktx_try_log.setItem(0, 2, QTableWidgetItem(reason))
        self.main_ui.tableWidget_ktx_try_log.setItem(0, 3, QTableWidgetItem(detail_info))

        # 일정 개수 이상 로그가 쌓이면 삭제
        if self.main_ui.tableWidget_ktx_try_log.rowCount() > self.max_try_log:
            self.main_ui.tableWidget_ktx_try_log.removeRow(self.max_try_log)

        self.main_ui.tableWidget_ktx_try_log.resizeColumnToContents(0)
        self.main_ui.tableWidget_ktx_try_log.resizeColumnToContents(1)
        self.main_ui.tableWidget_ktx_try_log.resizeColumnToContents(2)
        self.main_ui.tableWidget_ktx_try_log.resizeRowsToContents()

    def get_ktx_txtSeatAttCd_3(self):  # 좌석 위치
        idx = self.main_ui.comboBox_ktx_txtSeatAttCd_3.currentIndex()
        if idx == 0:
            return "000"    # 일반
        elif idx == 1:
            return "011"    # 1인석
        elif idx == 2:
            return "012"    # 창측좌석
        elif idx == 3:
            return "013"    # 내측좌석
        else:
            self.error_callback('KTX 좌석 위치 인덱스 에러', f"인덱스 - {idx}")
            return "000"    # 일반

    def get_ktx_txtSeatAttCd_2(self):  # 좌석 방향
        idx = self.main_ui.comboBox_ktx_txtSeatAttCd_2.currentIndex()
        if idx == 0:
            return "000"    # 일반
        elif idx == 1:
            return "009"    # 순방향석
        elif idx == 2:
            return "010"    # 역방향석
        else:
            self.error_callback('KTX 좌석 방향 인덱스 에러', f"인덱스 - {idx}")
            return "000"    # 일반

    def get_ktx_txtSeatAttCd_4(self):  # 좌석 종류
        idx = self.main_ui.comboBox_ktx_txtSeatAttCd_4.currentIndex()
        if idx == 0:
            return "015"    # 일반
        elif idx == 1 or idx == 2:
            return "019"    # 유아동반 / 편한대화
        elif idx == 3:
            return "031"    # 노트북
        elif idx == 4:
            return "021"    # 수동휠체어
        elif idx == 5:
            return "028"    # 전동휠체어
        elif idx == 6:
            return "XXX"    # 수유실 인접
        elif idx == 7:
            return "018"    # 2층석
        elif idx == 8:
            return "032"    # 자전거거치대
        else:
            self.error_callback('KTX 좌석 종류 인덱스 에러', f"인덱스 - {idx}")
            return "015"    # 일반

    def error_callback(self, type_, detail_):
        self.main_ui.tableWidget_error_log.insertRow(0)
        self.main_ui.tableWidget_error_log.setItem(0, 0, QTableWidgetItem(get_nowtime()))
        self.main_ui.tableWidget_error_log.setItem(0, 1, QTableWidgetItem(type_))
        self.main_ui.tableWidget_error_log.setItem(0, 2, QTableWidgetItem(detail_))

        # 일정 개수 이상 로그가 쌓이면 삭제
        if self.main_ui.tableWidget_error_log.rowCount() > self.max_error_log:
            self.main_ui.tableWidget_error_log.removeRow(self.max_error_log)

        self.main_ui.tableWidget_error_log.resizeColumnToContents(0)
        self.main_ui.tableWidget_error_log.resizeColumnToContents(1)
        self.main_ui.tableWidget_error_log.resizeRowsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UiMainClass()
    app.exec_()
