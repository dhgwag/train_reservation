import json
import re
import time
import urllib

import requests
from bs4 import BeautifulSoup
from collections import OrderedDict


class KTX:
    def __init__(self, error_callback, try_callback):
        self.error_callback = error_callback
        self.try_callback = try_callback

        self.session = requests.Session()
        self.session.get("https://www.letskorail.com/")

        self.stations = self.fetch_stations()

        self.forms = []

    def login(self, login_type='', login_id='', login_pwd=''):
        login_url = "https://www.letskorail.com/korail/com/loginAction.do"

        if login_type == '0':
            login_type = '2'
        elif login_type == '1':
            login_type = '5'
        elif login_type == '2':
            login_type = '4'
        else:
            self.error_callback('KTX 로그인 실패', f"잘못된 로그인 타입입니다 - {login_type}")
            return False

        # 아이디 검증
        if login_type == '2':  # 회원번호 로그인
            if len(login_id) != 10:
                self.error_callback('KTX 로그인 실패', f"회원번호는 10자리 숫자입니다")
                return False
        elif login_type == '4':  # 휴대전화번호 로그인
            login_id = login_id.replace('-', '')
            if len(login_id) == 10:
                login_id = login_id[0:3] + '-' + login_id[3:6] + '-' + login_id[6:]
            elif len(login_id) == 11:
                login_id = login_id[0:3] + '-' + login_id[3:7] + '-' + login_id[7:]
            else:
                self.error_callback('KTX 로그인 실패', f"휴대전화번호 입력 오류")
                return False
        elif login_type == '5':  # 이메일 로그인
            if '@' not in login_id:
                self.error_callback('KTX 로그인 실패', f"이메일 입력 오류")
                return False
        else:
            self.error_callback('KTX 로그인 실패', f"로그인 타입 코드 오류 - {login_type}")
            return False

        # 비밀번호 길이 검증
        if len(login_pwd) == 4:
            txtDv = "1"
        elif len(login_pwd) >= 4:
            txtDv = "2"
        else:
            self.error_callback('KTX 로그인 실패', f"비밀번호는 4자리 또는 8자리 이상 필수 [비밀번호 길이 : {len(login_pwd)}]")
            return False

        body = {
            "txtBookCnt": "",
            "txtIvntDt": "",
            "txtTotCnt": "",
            "selValues": "",
            "selInputFlg": login_type,
            "radIngrDvCd": "2",
            "ret_url": "",
            "hidMemberFlg": "1",
            "txtHaeRang": "",
            "hidEmailAdr": "",
            "txtDv": txtDv,
            "useKeySec": "",
            "UserId": login_id,
            "UserPwd": login_pwd,
            "encUserId": "",
            "encUserPwd": "",
            "keyname": "",
            "useKeySecFlg": "",
            "acsURI": "https://www.letskorail.com:443/ebizsso/sso/acs",
            "providerName": "Ebiz Sso",
            "forwardingURI": "/ebizsso/sso/sp/service_proc.jsp",
            "RelayState": "/ebizsso/sso/sp/service_front.jsp",
            "IPType": "Ebiz Sso Identity Provider"
        }
        try:
            res = self.session.post(login_url, data=body,
                                    headers=self.get_req_headers('https://www.letskorail.com/korail/com/login.do'))
        except Exception as e:
            self.error_callback('KTX 로그인 요청 실패', f"HTTP 로그인 요청에 실패했습니다 - \n{e}")
            return False

        if 'preset_list_json.do' not in res.text:
            self.error_callback('KTX 로그인 요청 실패', f"아이디 혹은 패스워드가 틀렸습니다")
            return False
        body = {
            'hidSetDv': '02',
            'hidRegSqno': '0'
        }
        try:
            res = self.session.post(
                f"https://www.letskorail.com/korail/com/mypage/preset/preset_list_json.do;jsessionid={self.session.cookies.get('JSESSIONID')}",
                data=body, headers=self.get_req_headers())
        except Exception as e:
            self.error_callback('KTX 로그인 요청 실패', f"HTTP 로그인 확인 요청에 실패했습니다 - \n{e}")
            return False

        if 'SUCC' not in res.text:
            self.error_callback('KTX 로그인 요청 실패', f"로그인 결과 확인에 실패했습니다")
            return False

        return self.is_logged_in()

    def is_logged_in(self):
        try:
            res = self.session.get(f"https://www.letskorail.com/index.jsp")
        except Exception as e:
            self.error_callback('KTX 로그인 여부 확인 실패', f"HTTP 요청에 실패했습니다 - \n{e}")
            return False
        # print(res.text)

        try:
            if '로그아웃' in res.text:
                return True
        except Exception as e:
            self.error_callback('KTX 로그인 여부 확인 실패', f"로그인 여부 확인에 실패했습니다 - \n{e}")
        return False

    def get_stations(self):
        return self.stations

    def fetch_schedule(self, txtGoStart, txtGoEnd, txtGoAbrdDt, txtGoHour, adult, child, baby, senior, svrDsb, mldDsb,
                       radJobId='1', txtSeatAttCd_3='000', txtSeatAttCd_2='000', txtSeatAttCd_4='015', selGoTrain='00'):
        schedule_url = "https://www.letskorail.com/ebizprd/EbizPrdTicketPr21111_i1.do"
        body = {
            "selGoTrain": selGoTrain,  # 기차 종류 (05-전체, 00-KTX, 09-ITX-청춘, 18-ITX-마음, 02-무궁화, 03-통근열차)
            "txtPsgFlg_1": adult,  # 성인 수
            "txtPsgFlg_2": child,  # 어린이 수(만6~12세)
            "txtPsgFlg_8": baby,  # 아기 수(만6세 미만)
            "txtPsgFlg_3": senior,  # 노인 수
            "txtPsgFlg_4": svrDsb,  # 중증장애인 수
            "txtPsgFlg_5": mldDsb,  # 경증장애인 수
            "txtSeatAttCd_3": txtSeatAttCd_3,  # 좌석위치 (000 - 기본, 011 - 1인석, 012 - 창측좌석, 013 - 내측좌석)
            "txtSeatAttCd_2": txtSeatAttCd_2,  # 좌석방향 (000 - 기본, 009 - 순방향석, 010 - 역방향석)
            "txtSeatAttCd_4": txtSeatAttCd_4,  # 좌석종류 (015 - 일반, 019 - 유아동반/편한대화, 031 - 노트북,  021 - 수동휠체어,
            # 028 - 전동휠체어, XXX - 수유실 인접, 018 - 2층석, 032 - 자전거거치대)
            "selGoTrainRa": selGoTrain,  # [추정] selGoTrain과 동일
            "radJobId": radJobId,  # 여정 경로(1 - 직통, 2 - 환승, 3 - 왕복)
            "adjcCheckYn": "N",  # 인접역 포함 여부 ("Y", "N")
            "txtGoStart": txtGoStart,  # 출발역 텍스트 (e.g. 서울)
            "txtGoEnd": txtGoEnd,  # 도착역 텍스트 (e.g. 청량리)
            "txtGoHour": txtGoHour,  # 출발 시간 (e.g. 180000 - HHMMSS)
            "txtGoPage": "1",  # 조회 페이지 - 항상 1
            "txtGoAbrdDt": txtGoAbrdDt,  # 출발일(e.g. 20240120)
            "checkStnNm": "Y",  # 항상 "Y"
            "hidRsvTpCd": "03",  # 예약구분 (03 - 일반예약, 09 - 단체예약)
        }
        try:
            res = self.session.post(schedule_url, data=body)
        except Exception as e:
            self.error_callback('KTX 열차 조회 실패', f"HTTP 요청에 실패했습니다 - \n{e}")
            return []

        try:
            soup = BeautifulSoup(res.text, 'html.parser')
            trains = soup.find_all("script", string=re.compile('new train_info'))
        except Exception as e:
            self.error_callback('KTX 열차 조회 실패', f"HTML 파싱에 실패했습니다 - \n{e}")
            return []

        result = []
        try:
            for tr in trains:
                tr = tr.text.replace('\t', '').replace(' ', '').replace("\r\n", "").replace("\"", "")
                tr = tr[tr.find('(') + 1:]
                tr = tr[:tr.rfind(')')]
                tr = tr.split(',')

                schedule_info = dict()
                schedule_info["txtGoAbrdDt"] = tr[0]
                schedule_info["txtGoStartCode"] = tr[1]
                schedule_info["txtGoEndCode"] = tr[2]
                schedule_info["selGoTrain"] = tr[3]
                schedule_info["selGoRoom"] = tr[4]
                schedule_info["txtGoHour"] = tr[5]
                schedule_info["txtGoTrnNo"] = tr[6]
                schedule_info["useSeatFlg"] = tr[7]
                schedule_info["useServiceFlg"] = tr[8]
                schedule_info["selGoSeat"] = tr[9]
                schedule_info["selGoSeat1"] = tr[10]
                schedule_info["selGoSeat2"] = tr[11]
                schedule_info["txtPsgCnt1"] = tr[12]
                schedule_info["txtPsgCnt2"] = tr[13]
                schedule_info["selGoService"] = tr[14]
                schedule_info["h_trn_seq"] = tr[15]
                schedule_info["h_chg_trn_dv_cd"] = tr[16]
                schedule_info["h_chg_trn_seq"] = tr[17]
                schedule_info["h_dpt_rs_stn_cd"] = tr[18]
                schedule_info["h_dpt_rs_stn_cd_nm"] = tr[19]
                schedule_info["h_arv_rs_stn_cd"] = tr[20]
                schedule_info["h_arv_rs_stn_cd_nm"] = tr[21]
                schedule_info["h_trn_no"] = tr[22]
                schedule_info["h_yms_apl_flg"] = tr[23]
                schedule_info["h_trn_clsf_cd"] = tr[24]
                schedule_info["h_trn_gp_cd"] = tr[25]
                schedule_info["h_seat_att_cd"] = tr[26]
                schedule_info["h_run_dt"] = tr[27]
                schedule_info["h_dpt_dt"] = tr[28]
                schedule_info["h_dpt_tm"] = tr[29]
                schedule_info["h_arv_dt"] = tr[30]
                schedule_info["h_arv_tm"] = tr[31]
                schedule_info["h_dlay_hr"] = tr[32]
                schedule_info["h_rsv_wait_ps_cnt"] = tr[33]
                schedule_info["h_dtour_flg"] = tr[34]
                schedule_info["h_car_tp_cd"] = tr[35]
                schedule_info["h_trn_cps_cd1"] = tr[36]
                schedule_info["h_trn_cps_cd2"] = tr[37]
                schedule_info["h_trn_cps_cd3"] = tr[38]
                schedule_info["h_trn_cps_cd4"] = tr[39]
                schedule_info["h_trn_cps_cd5"] = tr[40]
                schedule_info["h_no_ticket_dpt_rs_stn_cd"] = tr[41]
                schedule_info["h_no_ticket_arv_rs_stn_cd"] = tr[42]
                schedule_info["h_nonstop_msg"] = tr[43]
                schedule_info["h_dpt_stn_cons_ordr"] = tr[44]
                schedule_info["h_arv_stn_cons_ordr"] = tr[45]
                schedule_info["h_dpt_stn_run_ordr"] = tr[46]
                schedule_info["h_arv_stn_run_ordr"] = tr[47]
                schedule_info["h_stnd_rest_seat_cnt"] = tr[48]
                schedule_info["h_free_rest_seat_cnt"] = tr[49]

                if schedule_info['h_trn_gp_cd'] != '100':   # KTX 가 아닌 경우, SRT = 300
                    continue

                result.append(schedule_info)
        except Exception as e:
            self.error_callback('KTX 열차 조회 실패', f"열차 시간표 파싱에 실패했습니다 - \n{e}")

        return result

    def fetch_stations(self):
        result = dict()
        try:
            res = self.session.get("https://www.letskorail.com/ebizprd/EbizPrdTicketPr11100/searchTnCode.do")
        except Exception as e:
            self.error_callback('KTX 역 조회 실패', f"HTTP 요청에 실패했습니다 - \n{e}")
            return result
        # print(res.text)
        try:
            soup = BeautifulSoup(res.text, 'html.parser')
            stations = soup.find_all("td", {"class": re.compile(r'bg03')})

            for station in stations:
                station = station.find("a")
                station_split = station['href'].split("'")
                result[station_split[1]] = station_split[3]
        except Exception as e:
            self.error_callback('KTX 역 조회 실패', f"파싱에 실패했습니다 - \n{e}")

        return result

    def book_ticket(self, adult, child, baby, senior, svrDsb, mldDsb, train_schedule, txtSeatAttCd_3='000',
                    txtSeatAttCd_2='000', txtSeatAttCd_4='015', isReservation=False, isBusiness=False):
        reservation_url = "https://www.letskorail.com/ebizprd/EbizPrdTicketPr12111_i1.do"

        txtTotPsgCnt = adult + child + baby + senior + svrDsb + mldDsb
        body = {
            "txtSeatAttCd2": txtSeatAttCd_2,                            # 좌석방향 (000 - 기본, 009 - 순방향석, 010 - 역방향석)
            "txtSeatAttCd3": txtSeatAttCd_3,                            # 좌석위치 (000 - 기본, 011 - 1인석, 012 - 창측좌석, 013 - 내측좌석)
            "txtSeatAttCd4": txtSeatAttCd_4,                            # 좌석종류
            "txtTotPsgCnt": txtTotPsgCnt,                               # 총 인원 수
            "txtPsgTpCd1": "1",                                         # 고정값
            "txtPsgTpCd2": "3",                                         # 고정값
            "txtPsgTpCd3": "1",                                         # 고정값
            "txtPsgTpCd5": "1",                                         # 고정값
            "txtPsgTpCd7": "1",                                         # 고정값
            "txtPsgTpCd8": "3",                                         # 고정값
            "txtCompaCnt1": str(adult),                                 # 일반 어른
            "txtCompaCnt2": str(child),                                 # 일반 어린이
            "txtCompaCnt3": str(svrDsb),                                # 중증 장애인
            "txtCompaCnt5": str(senior),                                # 노인
            "txtCompaCnt7": str(mldDsb),                                # 경증 장애인
            "txtCompaCnt8": str(baby),                                  # 유아
            "txtJobId": "1102" if isReservation else "1101",            # 예약타입(1101 - 일반, 1102 - 예약, 1103 - 좌석선택)
            "txtJrnyCnt": "1",                                          # 여정 개수
            "txtPsrmClCd1": "2" if isBusiness else "1",                 # 좌석 등급 (1-일반실, 2-특실)
            "txtJrnySqno1": "001",                                      # 여정경로 (001 - 직통)
            "txtJrnyTpCd1": "11",                                       # 여정타입 (11 - 편도)
            "txtDptDt1": train_schedule['h_dpt_dt'],                    # 출발일 - 스케쥴 정보에 포함
            "txtDptRsStnCd1": train_schedule['h_dpt_rs_stn_cd'],        # 출발역 코드 - 스케쥴 정보에 포함
            "txtDptRsStnCdNm1": train_schedule['h_dpt_rs_stn_cd_nm'],   # 출발역 이름 - 스케쥴 정보에 포함
            "txtDptTm1": train_schedule['h_dpt_tm'],                    # 출발 시간 - 스케쥴 정보에 포함
            "txtArvRsStnCd1": train_schedule['h_arv_rs_stn_cd'],        # 도착역 코드 - 스케쥴 정보에 포함
            "txtArvRsStnCdNm1": train_schedule['h_arv_rs_stn_cd_nm'],   # 도착역 이름 - 스케쥴 정보에 포함
            "txtArvTm1": train_schedule['h_arv_tm'],                    # 열차 도착 시간 - 스케쥴 정보에 포함
            "txtTrnNo1": train_schedule['h_trn_no'],                    # 열차 번호 - 스케쥴 정보에 포함
            "txtRunDt1": train_schedule['h_run_dt'],                    # 출발일 - 스케쥴 정보에 포함
            "txtTrnClsfCd1": train_schedule['h_trn_clsf_cd'],           # 열차 종류 - 스케쥴 정보에 포함
            "txtTrnGpCd1": train_schedule['h_trn_gp_cd'],               # 기차 종류 - 스케쥴 정보에 포함
        }
        try:
            reservation_res = self.session.post(reservation_url, data=body, headers=self.get_req_headers(
                'https://www.letskorail.com/ebizprd/EbizPrdTicketPr21111_i1.do'))
        except Exception as e:
            self.error_callback('KTX 예매 실패', f"HTTP 요청에 실패했습니다 - \n{e}")
            return False

        try:
            if '로그아웃' not in reservation_res.text:
                if not self.login():
                    self.error_callback('KTX 예매 실패', '예약 중 로그인 재시도 실패')  # 로그인 실패
                    return False
                try:
                    reservation_res = self.session.post(reservation_url, data=body, headers=self.get_req_headers(
                        'https://www.letskorail.com/ebizprd/EbizPrdTicketPr21111_i1.do'))
                except Exception as e:
                    self.error_callback('KTX 예매 실패', f"예약 중 재로그인 후 HTTP 요청에 실패했습니다 - \n{e}")
                    return False

        except Exception as e:
            self.error_callback('KTX 예매 실패', f"알 수 없는 에러 - \n{e}")
            return False

        detail_info = f"[{'특실' if isBusiness else '일반실'}] " \
                      f"{train_schedule['h_dpt_rs_stn_cd_nm']}⇀{train_schedule['h_arv_rs_stn_cd_nm']} " \
                      f"{train_schedule['h_dpt_tm'][0:2] + ':' + train_schedule['h_dpt_tm'][2:4]} " \
                      f"{'' if adult == 0 else '성인 ' + str(adult) + '명'} " \
                      f"{'' if child == 0 else '어린이 ' + str(child) + '명'} " \
                      f"{'' if baby == 0 else '아기 ' + str(baby) + '명'} " \
                      f"{'' if senior == 0 else '노인 ' + str(senior) + '명'} " \
                      f"{'' if svrDsb == 0 else '중증장애인 ' + str(svrDsb) + '명'} " \
                      f"{'' if mldDsb == 0 else '경증장애인 ' + str(mldDsb) + '명'} "

        if "20분 이내 결제" in reservation_res.text or "예약 대기" in reservation_res.text:
            self.try_callback(True, "", detail_info)
            return True
        if "잔여석없음" in reservation_res.text:
            self.try_callback(False, "잔여석 없음", detail_info)
        elif "예약대기자한도수초과" in reservation_res.text:
            self.try_callback(False, "예약대기자 한도수 초과", detail_info)
        elif "20분 이내 열차는 예약" in reservation_res.text:
            self.try_callback(False, "20분 이내 열차 예약 불가", detail_info)
        elif "일반최대 단체최소" in reservation_res.text:
            self.try_callback(False, "인원 수 오류, 9명 이하만 예약 가능", detail_info)
        else:
            self.try_callback(False, "기타 사유", detail_info + reservation_res.text)

        return False

    def get_req_headers(self, referer=''):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Length': '0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'www.letskorail.com',
            'Origin': 'https://www.letskorail.com',
            'Pragma': 'no-cache',
            'Referer': referer,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }
        return headers


if __name__ == "__main__":
    ktx = KTX()
    ktx.login('4', '', '')
    ktx.fetch_stations()
    schedules = ktx.fetch_schedule('서울', '부산', '20240115', '200000', 1, 2, 3, 2, 1, 1)

    # print(schedules[0])
    #
    ktx.book_ticket(1, 0, 0, 0, 0, 0, schedules[0], '012', '009', '015', True, False)
    # print(ktx.is_logged_in())
