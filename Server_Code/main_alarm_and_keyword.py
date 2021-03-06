import datetime
import sqlite3
import numpy as np
import time
import os
import json
from data_generator import data
from utils import *
from functools import wraps

if __name__ == '__main__':
	d = data()
	conn = sqlite3.connect("/root/POSCHAIR.db")

	c = conn.cursor()
	c.execute("SELECT init_pos_lower FROM User WHERE ID = ?", ("choo@naver.com",))
	rows = c.fetchone()[0]

	lower_init = rows.replace('[','').replace(']','').split(',')
	lower_init = list(map(int, lower_init))

    #계속 돌면서 keyword 저장
	while(True):

		start = time.time()

        #lower_median_total, upper_median_total DB에서 가져옴
		c.execute("SELECT lower_median_total FROM Median WHERE ID = ?", ("choo@naver.com",))
		lower_median_total = c.fetchone()[0]
		c.execute("SELECT upper_median_total FROM Median WHERE ID = ?", ("choo@naver.com",))
		upper_median_total = c.fetchone()[0]

		lower_median_total = rows.replace('[','').replace(']','').split(',')
		lower_median_total = list(map(int, lower_median_total))
		upper_median_total = rows.replace('[','').replace(']','').split(',')
		upper_median_total = list(map(int, upper_median_total))


		if np.count_nonzero(np.asarray(lower_median_total)-10)>6: #사용자가 의자에 앉아있는지 판단
            #각 센서값으로 자세 lower/upper 자세 판단 (이건 median 값)
			lower = LBCNet(d.generator(lower_median_total), d.generator(lower_init)) #lower 자세값
			upper = upper_balance_check(upper_median_total) #upper 자세값 받아옴.

			print("lower: ",lower,"upper: ", upper)

            #실시간 자세 DB에 저장
			messaging(upper, lower) #output은 int 형태로 나옴 이걸 안드로이드로 전송해서 안드로이드에서 메세지 생성

			conn = sqlite3.connect("/root/POSCHAIR.db")
			c = conn.cursor()
			input = [datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "choo@naver.com", upper, lower[0], lower[1], lower[2], lower[3]]
			c.execute("INSERT INTO Posture_data VALUES (?,?,?,?,?,?,?)", input)
			c.commit()

            #키워드 매칭 알고리즘(DB에 저장하는 함수)
			keyword_matching(conn, upper, lower, lower_median_total) #자세 값을 기반으로 디비에 해당 키워드 별 +1 해줌

            #알림 확인 및 전송
			alarm_list = is_alarm(upper, lower, conn) #알람 보낼 리스트가 있는지 확인
			print("alarm_list: ", alarm_list)

			try:
				if len(alarm_list) is not 0: #알람 리스트가 있으면
					result = generate_alarm(alarm_list) #알람 전송
			except:
				pass

		elapsed_time = time.time() - start

		time.sleep(300-elapsed_time)
