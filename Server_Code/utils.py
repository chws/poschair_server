# -*- coding: utf-8 -*-

# =============================================================================
# Test deep learning model PosCNN in model.py
#
# by Chae Eun Lee (02/2019)
# nuguziii@naver.com
# https://github.com/nuguziii
# =============================================================================

# run this to test the model

import numpy as np
import torch
import torch.nn as nn
import time
import os
import sqlite3
import datetime
from data_generator import data
from model import vgg19
import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging





def LBCNet(image, guide):
    #=======================================
    # deep learning model LBCNet
    # (Lower Balance Check Network)
    # - input: (90*90*3) image
    # - output: posture label(0-15)
    #=======================================
    start_time = time.time()
    model = torch.load('model.pth', map_location='cpu')
    vgg = vgg19()

    model.eval()
    vgg.eval()

    vgg = vgg.cpu()
    model = model.cpu()

    x = image.astype('float32')/255
    x = x.reshape(1,x.shape[0],x.shape[1],x.shape[2])
    x_ = torch.from_numpy(x.transpose((0, 3, 1, 2)))
    x_ = x_.cpu()

    g = guide.astype('float32')/255
    g = g.reshape(1,g.shape[0],g.shape[1],g.shape[2])
    g_ = torch.from_numpy(g.transpose((0, 3, 1, 2)))
    g_ = g_.cpu()

    #print(vgg(x_).size())
    y_p = []
    x_ = vgg(x_)
    g_ = vgg(g_)
    cat = torch.cat((x_,g_),1)

    temp_y = model(cat)
    temp_y = temp_y.detach().numpy()
    y_p = np.rint(temp_y)

    elapsed_time = time.time() - start_time

    y_p = y_p.reshape(4).tolist()
    return y_p

def upper_balance_check(value):
    #=====================================
    # upper posture Check
    # input:
    #  value: ultrasonic sensor value
    #          [sensor1, sensor2]
    # output: upper posture
    #======================================
    posture_list = {"Alright":0, "Turtle/Bowed":1, "Slouched":2}
    # 센서 계산 과정 통해서 result 결과 출력
    result = None

    if (value[0] == -1 and value[1] <= 20):
        result = posture_list["Alright"]
    elif (value[0] == -1 and value[1] >= 150):
        result = posture_list["Turtle/Bowed"]
    else:
        result = posture_list["Slouched"]

    return result

def messaging(upper, lower):
    #=====================================
    # generate message list, save DB and send android
    # - input
    #  upper: int type
    #  lower: list type [0,0,0,0]
    #======================================
    # 메세지는 int 형태로 안드로이드에 전송하고, 안드로이드에서 메세지 정의
    messaging_list = {"Alright":0, "moreThanOne":1, "turtle/bowed":2, "legsOnChair":3, "crossedLegs":4, "backbone":5, "others":6}
    send_result = None


    if upper==0 and sum(lower)==0: #둘다 바른자세일 경우 (바른 자세입니다.)
        send_result = messaging_list["Alright"]
    if (upper==1 or upper==2):
        if (lower[0]+lower[2]+lower[3])>0: #전체적으로 바른자세 유지
        # 전체적으로 몸이 틀어져있습니다.
            send_result = messaging_list["moreThanOne"]
    elif upper==1:
        # 혹시 목을 숙이고 있으신가요?
        send_result = messaging_list["turtle/bowed"]
    elif lower[3]==1:
        # 혹시 다리를 꼬고 계신가요?
        send_result = messaging_list["crossedLegs"]
    elif lower[2]==1:
        # 혹시 다리를 의자 위에 올려놓고 계신가요?
        send_result = messaging_list["legsOnChair"]
    elif lower[1]==1:
        # 허리를 바르게 유지하고 계신가요?
        send_result = messaging_list["backbone"]
    else:
        send_result = messaging_list["others"]

    return send_result

    #send_android:
    #send_result 안드로이드에 전송

def is_alarm(upper, lower, conn):
    #=====================================
    # check if we should alert alarm
    # - output: list type (alarm_list)
    #======================================
    #{"바른자세":0, "목":2, "어깨":3, "다리꼬기":4, "앞으로 기울임":5, "뒤로기댐":6, "양반다리":7, "불균형":8, "error":-1}
    alarm_list = []
    '''DB에서 10분간 데이터 계산해서 85% 비율을 차지한 자세를 alarm_list에 넣음'''

    d = data()
    conn = sqlite3.connect("/root/POSCHAIR.db")
    c = conn.cursor()

    #bring data of 10 minutes from the database
    t_now = datetime.datetime.now()
    t_old = t_now - datetime.timedelta(minutes = 10)

    #posture_data 이용해서 판단하기 10분전
    c.execute("SELECT * FROM Posture_data WHERE date BETWEEN ? AND ?", (t_old, t_now))
    rows = c.fetchall()


    upper1cnt = 0
    upper2cnt = 0
    lower1cnt = 0
    lower2cnt = 0
    lower3cnt = 0
    lower4cnt = 0
    cnt = 0

    for row in rows:
        if row[2]==1:
            upper1cnt += 1
        if row[2]==2:
            upper2cnt += 1
        lower1cnt += row[3]
        lower2cnt += row[4]
        lower3cnt += row[5]
        lower4cnt += row[6]
        cnt += 1

    #calculate whether percentage is over 85%
    percent = [0,0,0,0,0,0]
    percent[0] = upper1cnt / cnt
    percent[1] = upper2cnt / cnt
    percent[2] = lower1cnt / cnt
    percent[3] = lower2cnt / cnt
    percent[4] = lower3cnt / cnt
    percent[5] = lower4cnt / cnt

    #if it is over 85% add 1 at the end of alarm_list else add 0
    for i in range(len(percent)):
        if percent[i] >= 0.85:
            alarm_list.append(1)
        else: alarm_list.append(0)


    #교집합 구하기
    upper_temp = [0,0]
    if upper==1:
        upper_temp[0]=1
    if upper==2:
        upper_temp[1]=1
    current = upper_temp+lower
    result = [0]*len(current)
    for i in range(len(current)):
        if current[i]==alarm_list[i]:
            result[i]=current[i]

    notification_list = {"Alright":0, "moreThanOne":1, "turtle/bowed":2, "backbone":3, "legs":4, "others":5}
    if sum(result)==0: #바른자세
        return notification_list["Alright"]
    elif sum(result)>=2: #전체적으로 바른 자세 유지 알람
        return notification_list["moreThanOne"]
    elif result[1]==1: #목 운동 알람
        return notification_list["turtle/bowed"]
    elif result[4]==1: #허리 운동 알람
        return notification_list["backbone"]
    elif result[5]==1 or result[6]==1: #다리 바르게 알람
        return notification_list["legs"]
    else: #자세 바르게 알람
        return notification_list["others"]


    return alarm_list

def generate_alarm(alarm_value):
    #=====================================
    # send alarm alert to android
    # - input:
    #     integer(indicates the current posture alarm label)
    #======================================

    posture = None

    if alarm_value == 0:
    	return 0 #don't send the alarm
    elif alarm_value == 1:
        posture = 'Mind your posture! Stretch out a bit :)'
    elif alarm_value == 2:
        posture = 'Mind your neck! Better stretch your neck :)'
    elif alarm_value == 3:
        posture = 'Mind your back! Better stretch your back right and left :)'
    elif alarm_value == 4:
        posture = 'You are crossing your legs for too long. How about changing your legs direction :)'
    else:
        posture = 'Sorry, no idea about your posture for the moment... :('

    print("entered firebase credential")
    cred = credentials.Certificate('/root/poschair-134c8-firebase-adminsdk-1i2vn-01f260312b.json')
    app = firebase_admin.initialize_app(cred)
    print("finished firebase credential")

    message = messaging.Message(
        android=messaging.AndroidConfig(
            ttl=0,
            priority='normal',
            notification=messaging.AndroidNotification(
                title='PosChair',
                body=posture,
                ),
                ),
                topic='poschair',
                )

    # Send a message to the devices subscribed to the provided topic.
    response = messaging.send(message)
    # Response is a message ID string.
    print('Successfully sent message:', response)

def keyword_matching(conn, upper, lower, lower_median_total):
    #=====================================
    # save in Keyword Database
    # - input:
    #   upper: int type
    #   lower: list type
    #======================================

    # {"Alright":0, "Turtle/Bowed":1, "Slouched":2}
    keyword_list = {"Turtle/Bowed":"k0", "Slouched":"k1", "PelvisImbalance":"k2", "Scoliosis":"k3", "HipPain":"k4", "KneePain":"k5", "PoorCirculation":"k6"}
    c = conn.cursor()
    correct = True

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT date FROM Keyword WHERE date = ?", (today,))
    data = c.fetchall()
    if len(data) == 0:
        input = ["choo@naver.com", today, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        c.execute("INSERT INTO Keyword(ID, date, total_time, k0, k1, k2, k3, k4, k5, k6, left, right) VALUES (?,?,?,?,?,?,?,?,?,?)", today)

    else:
        c.execute("SELECT total_time FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET total_time = ? WHERE date = ?", (today,))



    if upper is 1:
        c.execute("SELECT k0 FROM Keyword WHERE date = ?", (today))
        k0 = c.fetchone()[0]
        k0 += 1
        c.execute("UPDATE Keyword SET k0 = ? WHERE date = ?", (key, today))
        correct = False


    elif upper is 2:
        c.execute("SELECT k1 FROM Keyword WHERE date = ?", (today,))
        key = c.fetchone()[0]
        key += 1
        c.execute("UPDATE Keyword SET k1 = ? WHERE date = ?", (key, today))
        correct = False

    #DB에서 해당되는 키워드에 +1을 해줌 (Lower 경우)
    if lower[2] is 1:
        c.execute("SELECT k2 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k2 = ? WHERE date = ?", (key, today))

        c.execute("SELECT k3 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k3 = ? WHERE date = ?", (key, today))

        c.execute("SELECT k4 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k4 = ? WHERE date = ?", (key, today))

        c.execute("SELECT k5 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k5 = ? WHERE date = ?", (key, today))
        correct = False

    elif lower[3] is 1:
        c.execute("SELECT k2 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k2 = ? WHERE date = ?", (key, today))

        c.execute("SELECT k3 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k3 = ? WHERE date = ?", (key, today))

        c.execute("SELECT k6 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k6 = ? WHERE date = ?", (key, today))
        correct = False

        if lower_median_total[0]>lower_median_total[4]:
            c.execute("SELECT left FROM Keyword WHERE date = ?", (today,))
            key = int(c.fetchone()[0])
            key += 1
            c.execute("UPDATE Keyword SET left = ? WHERE date = ?", (key, today))
        else:
            c.execute("SELECT right FROM Keyword WHERE date = ?", (today,))
            key = int(c.fetchone()[0])
            key += 1
            c.execute("UPDATE Keyword SET right = ? WHERE date = ?", (key, today))

    elif lower[0] is 1:
        c.execute("SELECT k2 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k2 = ? WHERE date = ?", (key, today))

        c.execute("SELECT k3 FROM Keyword WHERE date = ?", (today,))

        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k3 = ? WHERE date = ?", (key, today))
        correct = False

    if lower[1] is 1 and upper is not 2:
        c.execute("SELECT k1 FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET k1 = ? WHERE date = ?", (key, today))
        correct = False;

    if correct:
        c = conn.cursor()
        c.execute("SELECT correct_time FROM Keyword WHERE date = ?", (today,))
        key = int(c.fetchone()[0])
        key += 1
        c.execute("UPDATE Keyword SET correct_time = ? WHERE date = ?", (key, today))

    conn.commit()



def generate_keyword_for_video_matching(conn):
    #=====================================
    # generate keyword from Database
    # DB에 n시간 정도의 자세 키워드 데이터를 확인한 다음
    # 각 키워드, 시간을 출력함
    # - output: dictionary
    # ex) {"k0": 128, 1:330 ...}
    #======================================
    '''
    1. DB에서 n시간 정도의 자세 키워드 데이터 가져옴
    2. 각 키워드 별 시간 계산해서 dictionary 형태로 출력
    '''

    conn = sqlite3.connect("/root/POSCHAIR.db")
    c = conn.cursor()

    keyword_dict = {"k0":0, "k1":0, "k2":0, "k3":0, "k4":0, "k5":0, "k6":0}

    t_now = datetime.datetime.now()
    t_old = t_now - datetime.timedelta(hours = 48)

    c.execute("SELECT * FROM Keyword WHERE ID = ?", ("choo@naver.com",))
    rows = c.fetchall()

    for row in rows:
        for i in range(7): #3-9
            keyword_dict["k"+str(i)] += row[i+3]


    return keyword_dict

def video_matching(keyword, conn):
    #=====================================
    # generate_keyword_for_video_matching 으로부터 keyword 받아와서
    # video url list string 형태로 안드로이드에 보냄
    # - input: keyword(dictionary)
    #======================================
    # {"Turtle/Bowed":"k0", "Slouched":"k1", "PelvisImbalance":"k2", "Scoliosis":"k3", "HipPain":"k4", "KneePain":"k5", "PoorCirculation":"k6"}
    keyword_list = {"k0":1, "k1":2, "k2":3, "k3":4, "k4":5, "k5":6, "k6":7}
    # {"k0":"거북목운동", "k1":"어깨/허리스트레칭", "k2":"골반교정운동/체형교정운동", "k3":"척추교정운동", "k4":"고관절스트레칭", "k5":"무릎운동", "k6":"다리스트레칭/혈액순환", "k7":"전신"}
    video_dict = {"k0":0, "k1":1, "k2":2, "k3":3, "k4":4, "k5":5, "k6":6, "k7":7}
    import operator
    sorted_key = sorted(keyword.items(), key=operator.itemgetter(1), reverse=True) #시간 많은 순으로 정렬

    video_list = []

    if sorted_key[0][1] == sorted_key[1][1]:
        video_keyword = video_dict["k7"]
    else:
        video_keyword = video_dict[sorted_key[0][0]]


    '''
    video_list에 해당하는 url들 db에서 가져오기
    가져올 때 조희수/like 수 등 생각해서 높은 순서대로 상위 5개 가져오기.
    '''

    conn = sqlite3.connect("/root/POSCHAIR.db")
    c = conn.cursor()

    weighted = []
    for i in range(7):
        tmp = "k"+str(i)
        c.execute("SELECT * FROM Youtube_Video WHERE keyword = ?", (tmp,))
        #조회수/like 수
        #liked
        row = c.fetchone()
        weighted.append((row[6], row[5]/row[4], tmp))
        weighted.sort(reverse=True)

    for i in range(4):
        c.execute("SELECT vidID FROM Youtube_Video WHERE keyword = ?", (weighted[i][2],))
        tmpID = c.fetchone()[0]
        video_list.append(tmpID)

    return video_list
