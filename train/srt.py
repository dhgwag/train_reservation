import re
import time
import requests
from bs4 import BeautifulSoup


class SRT:
    def __init__(self, error_callback, try_callback):
        self.error_callback = error_callback
        self.try_callback = try_callback

        self.session = requests.Session()
        self.session.get("https://etk.srail.kr/main.do")

        self.stations = self.fetch_stations()

    def login(self, login_type='', login_id='', login_pwd=''):
        login_url = "https://etk.srail.kr/cmc/01/selectLoginInfo.do"
        body = {
            "rsvTpCd": "",
            "goUrl": "",
            "from": "",
            "srchDvCd": login_type,
            "srchDvNm": login_id,
            "hmpgPwdCphd": login_pwd
        }
        try:
            res = self.session.post(login_url, data=body)
        except Exception as e:
            self.error_callback('SRT 로그인 요청 실패', f"HTTP 요청에 실패했습니다 - \n{e}")
            return False

        try:
            if "location.replace('/main.do')" in res.text:
                return True
            elif "periodicPassInfo" in res.text:
                self.error_callback('SRT 로그인 실패', "비밀번호 주기적 변경 필요. 홈페이지 로그인 후 비밀번호를 변경해주세요.")
            elif "존재하지않는 회원" in res.text:
                self.error_callback('SRT 로그인 실패', "존재하지 않는 회원입니다")
            elif "비밀번호 오류횟수" in res.text:
                self.error_callback('SRT 로그인 실패', "비밀번호 오류횟수 초과입니다. 웹사이트에서 비밀번호를 재설정 해주세요.")
            elif "비밀번호 오류" in res.text:
                self.error_callback('SRT 로그인 실패', "비밀번호 오류입니다")
            else:
                self.error_callback('SRT 로그인 실패', f"알 수 없는 오류 - \n{res.text}")
            return False
        except Exception as e:
            self.error_callback('SRT 로그인 확인 실패', f"로그인 결과 확인에 실패했습니다 - \n{e}")

    def is_logged_in(self):
        try:
            res = self.session.get("https://etk.srail.kr/main.do")
        except Exception as e:
            self.error_callback('SRT 로그인 여부 확인 실패', f"HTTP 요청에 실패했습니다 - \n{e}")
            return False

        try:
            if '로그아웃' in res.text:
                return True
        except Exception as e:
            self.error_callback('SRT 로그인 여부 확인 실패', f"로그인 여부 확인에 실패했습니다 - \n{e}")
        return False

    def get_stations(self):
        return self.stations

    def check_waiting(self, key):
        nwait = 0
        if key == "": # first
            waiting_url = "https://nf.letskorail.com/ts.wseq?opcode=5101&nfid=0&prefix=NetFunnel.gRtype=5101;&sid=service_1&aid=act_9&js=true"
            res = self.session.get(waiting_url)
            waiting_exists = '5002:200' not in res.text.split('key=')[0]
            key = res.text.split('key=')[1].split('&')[0]
            if waiting_exists:
                nwait = int(res.text.split('key=')[1].split('&')[1].split('=')[1])
        else:
            waiting_url = f"https://nf.letskorail.com/ts.wseq?opcode=5002&key={key}&nfid=0&prefix=NetFunnel.gRtype=5002;&ttl=1&sid=service_1&aid=act_9&js=true"
            res = self.session.get(waiting_url)
            key = res.text.split('key=')[1].split('&')[0]
            waiting_exists = '5002:200' not in res.text.split('key=')[0]
            nwait = int(res.text.split('key=')[1].split('&')[1].split('=')[1])

        return waiting_exists, nwait, key

    def check_booking(self, key):
        nwait = 0
        if key == "": # first
            waiting_url = "https://nf.letskorail.com/ts.wseq?opcode=5101&nfid=0&prefix=NetFunnel.gRtype=5101;&sid=service_1&aid=act_19&js=true"
            res = self.session.get(waiting_url)
            waiting_exists = '5002:200' not in res.text.split('key=')[0]
            key = res.text.split('key=')[1].split('&')[0]
            if waiting_exists:
                nwait = int(res.text.split('key=')[1].split('&')[1].split('=')[1])
        else:
            waiting_url = f"https://nf.letskorail.com/ts.wseq?opcode=5002&key={key}&nfid=0&prefix=NetFunnel.gRtype=5002;&ttl=1&sid=service_1&aid=act_19&js=true"
            res = self.session.get(waiting_url)
            key = res.text.split('key=')[1].split('&')[0]
            waiting_exists = '5002:200' not in res.text.split('key=')[0]
            nwait = int(res.text.split('key=')[1].split('&')[1].split('=')[1])

        return waiting_exists, nwait, key

    def fetch_schedule(self, dptRsStnCdNm, arvRsStnCdNm, dptDt, dptTm, adult, child, senior, svrDsb, mldDsb,
                       chtnDvCd='1', locSeatAttCd1='000', rqSeatAttCd1='015', trnGpCd='300', dlayTnumAplFlg='Y', key=""):
        schedule_url = "https://etk.srail.kr/hpg/hra/01/selectScheduleList.do"
        body = {
            "dptRsStnCd": self.stations[dptRsStnCdNm],  # 출발역 코드 (e.g. 0551)
            "arvRsStnCd": self.stations[arvRsStnCdNm],  # 도착역 코드
            "stlbTrnClsfCd": "05",  # [추정] 항상 '05' - ~~ Train Classification Code 같은데, 변하지 않음
            "psgNum": str(adult + child + senior + svrDsb + mldDsb),  # 총 승객 인원
            "seatAttCd": rqSeatAttCd1,  # [추정] 좌석 속성, rqSeatAttCd1와 같은 값인 것으로 보임
            "isRequest": "Y",  # [추정] 항상 'Y'
            "dptRsStnCdNm": dptRsStnCdNm,  # 출발역 이름
            "arvRsStnCdNm": arvRsStnCdNm,  # 도착역 이름
            "dptDt": dptDt,  # 출발 날짜 (e.g. 20240108)
            "dptTm": dptTm,  # 출발 시간 (e.g. 194500)
            "chtnDvCd": chtnDvCd,  # 여정경로 (1 - 직통, 2 - 환승, 3 - 왕복)
            "psgInfoPerPrnb1": str(adult),  # 어른 인원
            "psgInfoPerPrnb5": str(child),  # 어린이 인원
            "psgInfoPerPrnb4": str(senior),  # 노인 인원
            "psgInfoPerPrnb2": str(svrDsb),  # 중증장애인 인원
            "psgInfoPerPrnb3": str(mldDsb),  # 경증장애인 인원
            "locSeatAttCd1": locSeatAttCd1,  # 좌석위치 (000 - default, 011 - 1인석, 012 - 창측좌석, 013 - 내측좌석)
            "rqSeatAttCd1": rqSeatAttCd1,  # 좌석속성 (015 - 일반, 021 - 휠체어, 028 - 전동휠체어)
            "trnGpCd": trnGpCd,  # 차종구분 (109 - 전체, 300 - SRT, 900 - SRT+KTX)
            "dlayTnumAplFlg": dlayTnumAplFlg,  # 지연열차포함 (Y - 포함, N - 미포함)
        }
        if key != "":
            body['key'] = key
        try:
            res = self.session.post(schedule_url, data=body)
        except Exception as e:
            self.error_callback('SRT 열차 조회 실패', f"HTTP 요청에 실패했습니다 - \n{e}")
            return []

        try:
            soup = BeautifulSoup(res.text, 'html.parser')
            trains = soup.find_all("td", {"class": "trnNo"})
        except Exception as e:
            self.error_callback('SRT 열차 조회 실패', f"HTML 파싱에 실패했습니다 - \n{e}")
            return []

        result = []
        try:
            for tr in trains:
                schedule_info = dict()
                schedule_info["trnOrdrNo"] = tr.find("input", {"name": re.compile(r'trnOrdrNo')})['value']
                schedule_info["jrnySqno"] = tr.find("input", {"name": re.compile(r'jrnySqno')})['value']
                schedule_info["runDt"] = tr.find("input", {"name": re.compile(r'runDt')})['value']
                schedule_info["trnNo"] = tr.find("input", {"name": re.compile(r'trnNo')})['value']
                schedule_info["trnGpCd"] = tr.find("input", {"name": re.compile(r'trnGpCd')})['value']
                schedule_info["stlbTrnClsfCd"] = tr.find("input", {"name": re.compile(r'stlbTrnClsfCd')})['value']
                schedule_info["dptDt"] = tr.find("input", {"name": re.compile(r'dptDt')})['value']
                schedule_info["dptTm"] = tr.find("input", {"name": re.compile(r'dptTm')})['value']
                schedule_info["dptRsStnCd"] = tr.find("input", {"name": re.compile(r'dptRsStnCd')})['value']
                schedule_info["dptRsStnCdNm"] = tr.find("input", {"name": re.compile(r'dptRsStnCdNm')})['value']
                schedule_info["dptStnConsOrdr"] = tr.find("input", {"name": re.compile(r'dptStnConsOrdr')})['value']
                schedule_info["dptStnRunOrdr"] = tr.find("input", {"name": re.compile(r'dptStnRunOrdr')})['value']
                schedule_info["arvRsStnCd"] = tr.find("input", {"name": re.compile(r'arvRsStnCd')})['value']
                schedule_info["arvRsStnCdNm"] = tr.find("input", {"name": re.compile(r'arvRsStnCdNm')})['value']
                schedule_info["arvStnConsOrdr"] = tr.find("input", {"name": re.compile(r'arvStnConsOrdr')})['value']
                schedule_info["arvStnRunOrdr"] = tr.find("input", {"name": re.compile(r'arvStnRunOrdr')})['value']
                schedule_info["seatAttCd"] = tr.find("input", {"name": re.compile(r'seatAttCd')})['value']
                schedule_info["scarGridcnt"] = tr.find("input", {"name": re.compile(r'scarGridcnt')})['value']
                schedule_info["scarNo"] = tr.find("input", {"name": re.compile(r'scarNo')})['value']
                schedule_info["seatNo_1"] = tr.find("input", {"name": re.compile(r'seatNo_1')})['value']
                schedule_info["seatNo_2"] = tr.find("input", {"name": re.compile(r'seatNo_2')})['value']
                schedule_info["seatNo_3"] = tr.find("input", {"name": re.compile(r'seatNo_3')})['value']
                schedule_info["seatNo_4"] = tr.find("input", {"name": re.compile(r'seatNo_4')})['value']
                schedule_info["seatNo_5"] = tr.find("input", {"name": re.compile(r'seatNo_5')})['value']
                schedule_info["seatNo_6"] = tr.find("input", {"name": re.compile(r'seatNo_6')})['value']
                schedule_info["seatNo_7"] = tr.find("input", {"name": re.compile(r'seatNo_7')})['value']
                schedule_info["seatNo_8"] = tr.find("input", {"name": re.compile(r'seatNo_8')})['value']
                schedule_info["seatNo_9"] = tr.find("input", {"name": re.compile(r'seatNo_9')})['value']
                schedule_info["trainDiscGenRt"] = tr.find("input", {"name": re.compile(r'trainDiscGenRt')})['value']
                schedule_info["rcvdAmt"] = tr.find("input", {"name": re.compile(r'rcvdAmt')})['value']
                schedule_info["rcvdFare"] = tr.find("input", {"name": re.compile(r'rcvdFare')})['value']
                schedule_info["trnNstpLeadInfo"] = tr.find("input", {"name": re.compile(r'trnNstpLeadInfo')})['value']

                result.append(schedule_info)
        except Exception as e:
            self.error_callback('SRT 열차 조회 실패', f"열차 시간표 파싱에 실패했습니다 - \n{e}")

        return result

    def fetch_stations(self):
        result = dict()
        try:
            res = self.session.get("https://etk.srail.kr/hpg/hra/01/selectMapInfo.do")
        except Exception as e:
            self.error_callback('SRT 역 조회 실패', f"HTTP 요청에 실패했습니다 - \n{e}")
            return result

        try:
            soup = BeautifulSoup(res.text, 'html.parser')
            stations = soup.find_all("a", {"class": re.compile(r'map')})

            for station in stations:
                station_split = station['onclick'].split("'")
                result[station_split[3]] = station_split[1]
        except Exception as e:
            self.error_callback('SRT 역 조회 실패', f"파싱에 실패했습니다 - \n{e}")
        return result

    def book_ticket(self, key, adult, child, senior, svrDsb, mldDsb, train_schedule, locSeatAttCd, rqSeatAttCd,
                    isReservation=False, isBusiness=False):
        check_user_url = "https://etk.srail.kr/hpg/hra/01/checkUserInfo.do"
        reservation_url = "https://etk.srail.kr/hpg/hra/02/requestReservationInfo.do"
        confirm_url = "https://etk.srail.kr/hpg/hra/02/confirmReservationInfo.do"

        psgGridcnt = 0
        psgGrid = []
        if adult > 0:
            psgGridcnt += 1
            psgGrid.append(["1", str(adult)])
        if child > 0:
            psgGridcnt += 1
            psgGrid.append(["5", str(child)])
        if senior > 0:
            psgGridcnt += 1
            psgGrid.append(["4", str(senior)])
        if svrDsb > 0:
            psgGridcnt += 1
            psgGrid.append(["2", str(svrDsb)])
        if mldDsb > 0:
            psgGridcnt += 1
            psgGrid.append(["3", str(mldDsb)])

        body = {
            "key": key,
            "rsvTpCd": "05" if isReservation else "01",
            "jobId": "1102" if isReservation else "1101",
            "jrnyTpCd": "11",
            "jrnyCnt": "1",
            "totPrnb": str(adult + child + senior + svrDsb + mldDsb),
            "stndFlg": "N",
            "trnOrdrNo1": train_schedule['trnOrdrNo'],
            "jrnySqno1": train_schedule['jrnySqno'],
            "runDt1": train_schedule['runDt'],
            "trnNo1": train_schedule['trnNo'],
            "trnGpCd1": train_schedule['trnGpCd'],
            "stlbTrnClsfCd1": train_schedule['stlbTrnClsfCd'],
            "dptDt1": train_schedule['dptDt'],
            "dptTm1": train_schedule['dptTm'],
            "dptRsStnCd1": train_schedule['dptRsStnCd'],
            "dptStnConsOrdr1": train_schedule['dptStnConsOrdr'],
            "dptStnRunOrdr1": train_schedule['dptStnRunOrdr'],
            "arvRsStnCd1": train_schedule['arvRsStnCd'],
            "arvStnConsOrdr1": train_schedule['arvStnConsOrdr'],
            "arvStnRunOrdr1": train_schedule['arvStnRunOrdr'],
            "scarYn1": "N",
            "scarGridcnt1": "",
            "scarNo1": "",
            "seatNo1_1": "",
            "seatNo1_2": "",
            "seatNo1_3": "",
            "seatNo1_4": "",
            "seatNo1_5": "",
            "seatNo1_6": "",
            "seatNo1_7": "",
            "seatNo1_8": "",
            "seatNo1_9": "",
            "psrmClCd1": "2" if isBusiness else "1",
            "smkSeatAttCd1": "000",
            "dirSeatAttCd1": "000",
            "locSeatAttCd1": locSeatAttCd,  # 좌석위치 (000 - default, 011 - 1인석, 012 - 창측좌석, 013 - 내측좌석)
            "rqSeatAttCd1": rqSeatAttCd,  # 좌석속성 (015 - 일반, 021 - 휠체어, 028 - 전동휠체어)
            "etcSeatAttCd1": "000",
            "jrnyTpCd1": "",
            "jrnyTpCd2": "",
            "trnOrdrNo2": "",
            "jrnySqno2": "",
            "runDt2": "",
            "trnNo2": "",
            "trnGpCd2": "",
            "stlbTrnClsfCd2": "",
            "dptDt2": "",
            "dptTm2": "",
            "dptRsStnCd2": "",
            "dptStnConsOrdr2": "",
            "dptStnRunOrdr2": "",
            "arvRsStnCd2": "",
            "arvStnConsOrdr2": "",
            "arvStnRunOrdr2": "",
            "scarYn2": "",
            "scarGridcnt2": "",
            "scarNo2": "",
            "seatNo2_1": "",
            "seatNo2_2": "",
            "seatNo2_3": "",
            "seatNo2_4": "",
            "seatNo2_5": "",
            "seatNo2_6": "",
            "seatNo2_7": "",
            "seatNo2_8": "",
            "seatNo2_9": "",
            "psrmClCd2": "",
            "smkSeatAttCd2": "",
            "dirSeatAttCd2": "",
            "locSeatAttCd2": "",
            "rqSeatAttCd2": "",
            "etcSeatAttCd2": "",
            "psgGridcnt": psgGridcnt,
            "psgTpCd1": "" if len(psgGrid) < 1 else psgGrid[0][0],
            "psgInfoPerPrnb1": "" if len(psgGrid) < 1 else psgGrid[0][1],
            "psgTpCd2": "" if len(psgGrid) < 2 else psgGrid[1][0],
            "psgInfoPerPrnb2": "" if len(psgGrid) < 2 else psgGrid[1][1],
            "psgTpCd3": "" if len(psgGrid) < 3 else psgGrid[2][0],
            "psgInfoPerPrnb3": "" if len(psgGrid) < 3 else psgGrid[2][1],
            "psgTpCd4": "" if len(psgGrid) < 4 else psgGrid[3][0],
            "psgInfoPerPrnb4": "" if len(psgGrid) < 4 else psgGrid[3][1],
            "psgTpCd5": "" if len(psgGrid) < 5 else psgGrid[4][0],
            "psgInfoPerPrnb5": "" if len(psgGrid) < 5 else psgGrid[4][1],
            "mutMrkVrfCd": "",
            "reqTime": str(int(time.time()) * 1000),
            "crossYn": "N"
        }
        try:
            check_user_res = self.session.post(check_user_url, data=body)
        except Exception as e:
            self.error_callback('SRT 예매 실패', f"checkUserInfo HTTP 요청에 실패했습니다 - \n{e}")
            return False

        try:
            if 'selectLoginForm' in check_user_res.text:
                if not self.login():
                    self.error_callback('SRT 예매 실패', '예약 중 로그인 재시도 실패')      # 로그인 실패
                    return False
                try:
                    check_user_res = self.session.post('https://etk.srail.kr/hpg/hra/01/checkUserInfo.do', data=body)
                except Exception as e:
                    self.error_callback('SRT 예매 실패', f"checkUserInfo HTTP 요청에 실패했습니다 - \n{e}")
                    return False

                if 'requestReservationInfo' in check_user_res.text:
                    try:
                        reservation_res = self.session.post(reservation_url, data=body)
                    except Exception as e:
                        self.error_callback('SRT 예매 실패', f"requestReservation HTTP 요청에 실패했습니다 - \n{e}")
                        return False
                else:
                    self.error_callback('SRT 예매 실패', f'예약 중 재로그인 후 user check fail - \n{check_user_res.text}')
                    return False
            elif 'requestReservationInfo' in check_user_res.text:
                try:
                    reservation_res = self.session.post(reservation_url, data=body)
                except Exception as e:
                    self.error_callback('SRT 예매 실패', f"requestReservation HTTP 요청에 실패했습니다 - \n{e}")
                    return False
            else:
                self.error_callback('SRT 예매 실패', f'예약 중 user check fail - \n{check_user_res.text}')
                return False
        except Exception as e:
            self.error_callback('SRT 예매 실패', f"알 수 없는 에러 - \n{e}")
            return False

        if 'confirmReservationInfo' in reservation_res.text:
            try:
                confirm_res = self.session.post(confirm_url, data=body)
            except Exception as e:
                self.error_callback('SRT 예매 실패', f"confirmRes HTTP 요청에 실패했습니다 - \n{e}")
                return False
        else:
            self.error_callback('SRT 예매 실패', f'예약 중 reservation fail - \n{check_user_res.text}')
            return False

        detail_info = f"[{'특실' if isBusiness else '일반실'}] " \
                      f"{train_schedule['dptRsStnCdNm']}⇀{train_schedule['arvRsStnCdNm']} " \
                      f"{train_schedule['dptTm'][0:2] + ':' + train_schedule['dptTm'][2:4]} " \
                      f"{'' if adult == 0 else '성인 '+str(adult)+'명'} "\
                      f"{'' if child == 0 else '어린이 '+str(child)+'명'} "\
                      f"{'' if senior == 0 else '노인 '+str(senior)+'명'} "\
                      f"{'' if svrDsb == 0 else '중증장애인 '+str(svrDsb)+'명'} "\
                      f"{'' if mldDsb == 0 else '경증장애인 '+str(mldDsb)+'명'} "
        if "10분 내에 결제하지 않으면" in confirm_res.text:
            self.try_callback(True, "", detail_info)
            return True
        if "잔여석없음" in confirm_res.text:
            self.try_callback(False, "잔여석 없음", detail_info)
        elif "예약대기자한도수초과" in confirm_res.text:
            self.try_callback(False, "예약대기자 한도수 초과", detail_info)
        elif "20분 이내 열차는 예약" in confirm_res.text:
            self.try_callback(False, "20분 이내 열차 예약 불가", detail_info)
        elif "일반최대 단체최소" in confirm_res.text:
            self.try_callback(False, "인원 수 오류, 9명 이하만 예약 가능", detail_info)
        else:
            self.try_callback(False, "기타 사유", detail_info + confirm_res.text)

        return False


if __name__ == "__main__":
    srt = SRT(None, None)
    srt.login('1', '', '')
    a, b, c = srt.check_waiting("")
    schedules = srt.fetch_schedule('수서', '부산', '20240312', '053100', 1, 0, 0, 0, 0, key=c)
    print(schedules)
    # srt.book_ticket(1, 0, 0, 0, 0, schedules[0], '000', '015', True, True)
