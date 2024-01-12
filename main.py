import time

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QTableWidgetItem, QRadioButton, QWidget, QHBoxLayout, QMessageBox

from design import Ui_dialog
from train.srt import SRT

from util import *

version = '1.0.0'
max_error_log = 20
max_try_log = 100


class SrtThread(QThread):
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
            time.sleep(float(self.parent.main_ui.doubleSpinBox_srt_delay.text()))


class UiMainClass(QDialog):
    def __init__(self):
        self.srt = SRT(self.error_callback, self.srt_try_callback)
        self.srt_stations = self.srt.get_stations()
        self.srt_thread = None

        self.radiobuttons = []
        self.schedules = []

        self.reservation_list = []
        self.reservation_idx = 0

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

        ### SRT ###
        # db에 데이터가 있는 경우 불러오기
        if 'srt_login_type' in self.db.keys():
            if self.db['srt_login_type'] == 0 or self.db['srt_login_type'] == 1 or self.db['srt_login_type'] == 2:
                self.main_ui.comboBox_srt_login_type.setCurrentIndex(self.db['srt_login_type'])
        if 'srt_id' in self.db.keys():
            self.main_ui.lineEdit_srt_id.setText(self.db['srt_id'])
        if 'srt_pwd' in self.db.keys():
            self.main_ui.lineEdit_srt_pwd.setText(self.db['srt_pwd'])
        if 'save_login_info' in self.db.keys() and self.db['save_login_info']:
            self.main_ui.checkBox_srt_save_login.setChecked(True)

        self.main_ui.comboBox_srt_adult.setCurrentIndex(1)
        self.main_ui.comboBox_srt_dpt_stn.addItems(self.srt_stations.keys())
        self.main_ui.comboBox_srt_arv_stn.addItems(self.srt_stations.keys())
        self.main_ui.comboBox_srt_arv_stn.setCurrentIndex(1)

        self.main_ui.dateTimeEdit_srt_time.setDateTime(datetime.datetime.now())

        self.main_ui.pushButton_srt_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")

        # 로그인 타입 변경
        self.main_ui.comboBox_srt_login_type.currentIndexChanged.connect(self.comboBox_srt_login_type_changed)
        # 로그인
        self.main_ui.pushButton_srt_login.clicked.connect(self.pushButton_srt_login_clicked)
        # 열차 조회
        self.main_ui.pushButton_srt_search.clicked.connect(self.pushButton_srt_search_clicked)
        # 열차 예매
        self.main_ui.pushButton_srt_reservation.clicked.connect(self.pushButton_srt_reservation_clicked)

    def comboBox_srt_login_type_changed(self):
        self.main_ui.label_srt_id.setText(self.main_ui.comboBox_srt_login_type.currentText())

    def pushButton_srt_login_clicked(self):
        login_type = self.main_ui.comboBox_srt_login_type.currentIndex()
        srt_id = self.main_ui.lineEdit_srt_id.text()
        srt_pwd = self.main_ui.lineEdit_srt_pwd.text()

        if self.srt.login(str(login_type + 1), srt_id, srt_pwd):
            # 로그인 성공
            self.main_ui.groupBox_login.hide()
            self.main_ui.label_srt_logged_in.setText(f'로그인 계정 : {srt_id}')
            self.main_ui.label_srt_logged_in.show()

            if self.main_ui.checkBox_srt_save_login.isChecked():
                # 로그인 정보 저장
                self.db['srt_login_type'] = login_type
                self.db['srt_id'] = srt_id
                self.db['srt_pwd'] = srt_pwd
                self.db['save_login_info'] = True
            else:
                # 로그인 정보 삭제
                self.db['srt_login_type'] = 0
                self.db['srt_id'] = ''
                self.db['srt_pwd'] = ''
                self.db['save_login_info'] = False
            save_db(self.db)

    def pushButton_srt_search_clicked(self):
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
            self.error_callback('열차 조회 실패', '출발역과 도착역이 같습니다')
            return False
        self.schedules = self.srt.fetch_schedule(dptRsStnCdNm, arvRsStnCdNm, dptDt, dptTm, adult, child, senior, svrDsb,
                                                 mldDsb, chtnDvCd, locSeatAttCd1, rqSeatAttCd1, trnGpCd, dlayTnumAplFlg)

        # 기차 스케쥴 초기화
        self.radiobuttons = []
        self.main_ui.tableWidget_srt_schedule.setRowCount(0)

        for idx, schedule in enumerate(self.schedules):
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
            self.radiobuttons.append(radiobutton)
            cellWidget = QWidget()
            layoutCB = QHBoxLayout(cellWidget)
            layoutCB.addWidget(self.radiobuttons[-1])
            layoutCB.setAlignment(Qt.AlignCenter)
            layoutCB.setContentsMargins(0, 0, 0, 0)
            cellWidget.setLayout(layoutCB)

            self.main_ui.tableWidget_srt_schedule.setCellWidget(idx, 4, cellWidget)

    def pushButton_srt_reservation_clicked(self):
        if not self.srt_thread:
            self.srt_thread = SrtThread(self)
            self.srt_thread.reservation_func.connect(self.reservation_func)
            self.srt_thread.update_ctr_signal.connect(self.update_ctr)

        if self.srt_thread.isRunning():     # 동작 중일 때
            self.srt_thread.stop()
            self.main_ui.pushButton_srt_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")
            self.main_ui.pushButton_srt_reservation.setText('예매시작')
        else:                   # 동작 중 아닐 때
            self.main_ui.tableWidget_srt_try_log.setRowCount(0)
            self.reservation_list = []
            self.reservation_idx = 0
            adult = self.main_ui.comboBox_srt_adult.currentIndex()
            child = self.main_ui.comboBox_srt_child.currentIndex()
            senior = self.main_ui.comboBox_srt_senior.currentIndex()
            svrDsb = self.main_ui.comboBox_srt_svrDsb.currentIndex()
            mldDsb = self.main_ui.comboBox_srt_mldDsb.currentIndex()

            for idx, radiobutton in enumerate(self.radiobuttons):
                if radiobutton.isChecked():
                    class_idx = self.main_ui.comboBox_srt_class.currentIndex()
                    if class_idx == 0 or class_idx == 2:
                        self.reservation_list.append({
                            'adult': adult,
                            'child': child,
                            'senior': senior,
                            'svrDsb': svrDsb,
                            'mldDsb': mldDsb,
                            'train_schedule': self.schedules[idx],
                            'locSeatAttCd': self.get_srt_locSeatAttCd(),
                            'rqSeatAttCd': self.get_srt_rqSeatAttCd(),
                            'isReservation': self.main_ui.radioButton_srt_waiting.isChecked(),
                            'isBusiness': False,
                        })
                    if class_idx == 1 or class_idx == 2:
                        self.reservation_list.append({
                            'adult': adult,
                            'child': child,
                            'senior': senior,
                            'svrDsb': svrDsb,
                            'mldDsb': mldDsb,
                            'train_schedule': self.schedules[idx],
                            'locSeatAttCd': self.get_srt_locSeatAttCd(),
                            'rqSeatAttCd': self.get_srt_rqSeatAttCd(),
                            'isReservation': self.main_ui.radioButton_srt_waiting.isChecked(),
                            'isBusiness': True,
                        })

            if not self.srt.is_logged_in():
                self.error_callback('예매 실패', '로그인을 먼저 해주세요')
                self.main_ui.groupBox_login.show()
                self.main_ui.label_srt_logged_in.hide()
                return False
            if adult + child + senior + svrDsb + mldDsb < 1:
                self.error_callback('예매 실패', '인원을 선택해주세요')
                return False
            if not self.schedules:
                self.error_callback('예매 실패', '열차 조회를 먼저 해주세요')
                return False
            if not self.reservation_list:
                self.error_callback('예매 실패', '선택된 열차가 없습니다')
                return False

            self.srt_thread.start()
            self.main_ui.pushButton_srt_reservation.setStyleSheet("QPushButton{background-color : red;}")
            self.main_ui.pushButton_srt_reservation.setText('예매중지')

    def reservation_func(self):
        rsv_item = self.reservation_list[self.reservation_idx]
        success = self.srt.book_ticket(
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

        self.reservation_idx = (self.reservation_idx+1) % len(self.reservation_list)

        if success:
            self.srt_thread.stop()
            self.main_ui.pushButton_srt_reservation.setStyleSheet("QPushButton{background-color : lightblue;}")
            self.main_ui.pushButton_srt_reservation.setText('예매시작')
            QMessageBox.about(self, '예매 성공', '10분 내에 앱에서 결제해주세요')

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
            self.error_callback('좌석 위치 인덱스 에러', f"인덱스 - {idx}")
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
            self.error_callback('좌석 종류 인덱스 에러', f"인덱스 - {idx}")
            return "015"    # 일반

    def update_ctr(self, ctr):
        self.main_ui.lcdNumber_srt_ctr.display(ctr)

    def srt_try_callback(self, success, reason, detail_info):
        self.main_ui.tableWidget_srt_try_log.insertRow(0)
        self.main_ui.tableWidget_srt_try_log.setItem(0, 0, QTableWidgetItem(get_nowtime()))
        self.main_ui.tableWidget_srt_try_log.setItem(0, 1, QTableWidgetItem("성공" if success else "실패"))
        self.main_ui.tableWidget_srt_try_log.setItem(0, 2, QTableWidgetItem(reason))
        self.main_ui.tableWidget_srt_try_log.setItem(0, 3, QTableWidgetItem(detail_info))

        # 일정 개수 이상 로그가 쌓이면 삭제
        if self.main_ui.tableWidget_srt_try_log.rowCount() > max_try_log:
            self.main_ui.tableWidget_srt_try_log.removeRow(max_try_log)

        self.main_ui.tableWidget_srt_try_log.resizeColumnToContents(0)
        self.main_ui.tableWidget_srt_try_log.resizeColumnToContents(1)
        self.main_ui.tableWidget_srt_try_log.resizeColumnToContents(2)
        self.main_ui.tableWidget_srt_try_log.resizeRowsToContents()

    def error_callback(self, type_, detail_):
        self.main_ui.tableWidget_error_log.insertRow(0)
        self.main_ui.tableWidget_error_log.setItem(0, 0, QTableWidgetItem(get_nowtime()))
        self.main_ui.tableWidget_error_log.setItem(0, 1, QTableWidgetItem(type_))
        self.main_ui.tableWidget_error_log.setItem(0, 2, QTableWidgetItem(detail_))

        # 일정 개수 이상 로그가 쌓이면 삭제
        if self.main_ui.tableWidget_error_log.rowCount() > max_error_log:
            self.main_ui.tableWidget_error_log.removeRow(max_error_log)

        self.main_ui.tableWidget_error_log.resizeColumnToContents(0)
        self.main_ui.tableWidget_error_log.resizeColumnToContents(1)
        self.main_ui.tableWidget_error_log.resizeRowsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UiMainClass()
    app.exec_()
