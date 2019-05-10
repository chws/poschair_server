import datetime
from flask import Flask
from flask import redirect
from flask import request
from flask import session
from flask import url_for, abort, render_template, flash
#from data_generator import data
from functools import wraps
import sqlite3
import json
import random




# create a flask application - this ``app`` object will be used to handle
# inbound requests, routing them to the proper 'view' functions, etc
app = Flask(__name__)
app.config.from_object(__name__)


@app.route('/image/',methods=['GET','POST'])
def getImage():
        return redirect(url_for('static',filename='posture_sample.png'))


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form['email']:
        conn = sqlite3.connect("../POSCHAIR.db")
        c = conn.cursor()
        iemail = request.form['email']
        ipwd = request.form['pwd']
        c.execute("SELECT ID, pwd FROM User WHERE ID = ?", (iemail,))
        k = c.fetchone()[0]

        if k[0]==iemail and k[1] == ipwd :
            print('fetch success')
        else:
            print('fetch failed')

        return 'success'
       
@app.route('/signup/', methods=['GET', 'POST'])
def signup():
	if request.method == 'POST':
            conn = sqlite3.connect("../POSCHAIR.db")
            c = conn.cursor()
            input = [request.form['email'], request.form['name'], request.form['pwd']]
            c.execute("INSERT INTO User(ID, name, pwd) VALUES (?,?,?)", input)
            conn.commit()
            conn.close()

            return 'success'

'''
@app.route('/addInfo/', methods=['GET', 'POST'])
def addInfo():
	#age, sex, height, weight
	if request.method == 'POST':

	return render_template('./index.html')
'''

@app.route('/video/',methods=['GET','POST']) #추천 영상 비디오
def sendVideoList():
    if request.method == 'GET':

        result = get_info_video()
        return result



@app.route('/likeVideo/',methods=['GET','POST'])  #사용자가 좋아한 비디오
def sendlikeVideoList():
    if request.method == 'GET':
        conn = sqlite3.connect("../POSCHAIR.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        rows = c.execute('''
                         select vidID,vidTitle,view,uploadDate,liked from Youtube_Video where liked=1
                         ''').fetchall()
        conn.close()

        if rows == None:
            return json.dumps([])
        else:
            return json.dumps([dict(i) for i in rows])


@app.route('/changeVideoLike/',methods=['GET','POST'])
def updateVideoLike():
    if request.method == 'POST':
        user_id = request.form['user_id']
        videoID = request.form['videoID']
        isLike = request.form['isLike']

        conn = sqlite3.connect("../POSCHAIR.db")
        c = conn.cursor()

        if isLike == "like": # 좋아요 x -> 좋아요 db 업데이트
            c.execute("update Youtube_Video set liked=1 where vidID='{}'".format(videoID))
            conn.commit()
            conn.close()

            return "success"

        else: #isLike=="unlike" : 좋아요 -> 좋아요 취소 db 업데이트
            c.execute("update Youtube_Video set liked=0 where vidID='{}'".format(videoID))
            conn.commit()
            conn.close()

            return "success"


@app.route('/posture/', methods=['GET', 'POST'])
def getLabel():
	#label(int 값) string으로 반환한다
    if request.method == 'GET':
        conn = sqlite3.connect("/root/POSCHAIR.db")
        c = conn.cursor()

        c.execute("SELECT init_pos_lower FROM User WHERE ID = ?", ("choo@naver.com",))
        lower_origin = c.fetchone()[0]
        print(lower_origin)

        c.execute("SELECT total_time FROM Keyword WHERE ID = ?", ("choo@naver.com",))
        total_hour = c.fetchone()[0]
        print(total_hour)

        '''lower_median DB에서 가져옴'''
        c.execute("SELECT lower_median FROM Median WHERE ID = ?", ("choo@naver.com",))
        lower_median = c.fetchone()[0]
        c.execute("SELECT upper_median FROM Median WHERE ID = ?", ("choo@naver.com",))
        upper_median = c.fetchone()[0]

        label = 0

        if np.count_nonzero(lower_median-10)>6: #사용자가 의자에 앉아있는지 판단
            '''각 센서값으로 자세 lower/upper 자세 판단 (이건 median 값)'''
            lower = LBCNet(d.generator(lower_median), d.generator(lower_origin))
            upper = upper_balance_check(upper_median) #upper 자세값 받아옴.
            label = messaging(upper, lower)

        return str(label)


if __name__=='__main__':
	print('connection succeeded')
	app.run(host='0.0.0.0',port=80,debug=True)
