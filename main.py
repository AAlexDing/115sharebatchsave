#!/usr/local/bin/python3
#coding:  utf-8
import requests
import json
import sys
import sqlite3
import re
import codecs
import os
from time import sleep

class SharedLinksDB:
    def __init__(self, db_file):
        self.conn = self.create_connection(db_file)
        if self.conn is not None:
            self.create_table('''CREATE TABLE IF NOT EXISTS shared_link
                                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 share_code TEXT,
                                 receive_code TEXT,
                                 snap_id INTEGER,
                                 file_size INTEGER,
                                 share_title TEXT,
                                 share_state INTEGER,
                                forbid_reason INTEGER,
                                    create_time INTEGER,
                                    receive_count INTEGER,
                                    expire_time INTEGER,
                                    file_category INTEGER,
                                    auto_renewal INTEGER,
                                    auto_fill_recvcode INTEGER,
                                    can_report INTEGER,
                                    can_notice INTEGER,
                                    have_vio_file INTEGER,
                                 status INTEGER)''')

            self.create_table('''CREATE TABLE IF NOT EXISTS saved_data
                                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 n TEXT,
                                 cid TEXT)''')

    def __del__(self):
        self.close_connection()

    # 创建数据库连接
    def create_connection(self, db_file):
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            return conn
        except:
            print("[x] 无法创建数据库连接")
        return conn

    # 创建数据表
    def create_table(self, create_table_sql):
        try:
            cursor = self.conn.cursor()
            cursor.execute(create_table_sql)
        except:
            print("[x] 无法创建数据表")

    # 插入分享链接信息
    def insert_shared_link(self, share_code, receive_code,share_info, status):
        sql = '''INSERT INTO shared_link (share_code, receive_code, snap_id, file_size, share_title, share_state, forbid_reason, create_time, receive_count, expire_time, file_category, auto_renewal, auto_fill_recvcode, can_report, can_notice, have_vio_file, status)'''
        sql += '''VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
        cursor = self.conn.cursor()
        if share_info:
            cursor.execute(sql, (share_code, receive_code, share_info['snap_id'], share_info['file_size'], share_info['share_title'], share_info['share_state'], share_info['forbid_reason'], share_info['create_time'], share_info['receive_count'], share_info['expire_time'], share_info['file_category'], share_info['auto_renewal'], share_info['auto_fill_recvcode'], share_info['can_report'], share_info['can_notice'], share_info['have_vio_file'], status))
        else:
            cursor.execute(sql, (share_code, receive_code, 0, 0, '', 0, '', 0, 0, 0, 0, 0, 0, 0, 0, 0, status))
        self.conn.commit()

    # 检查分享链接信息是否存在
    def check_shared_link(self, share_code, receive_code):
        sql = '''SELECT * FROM shared_link WHERE share_code = ? AND receive_code = ?'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (share_code, receive_code))
        rows = cursor.fetchall()
        return len(rows) > 0

    # 插入data_list中的n值和cid值
    def insert_saved_data(self, data_list):
        cursor = self.conn.cursor()
        for i, data in enumerate(data_list):
            sql = '''INSERT INTO saved_data (n, cid)
                    VALUES (?, ?)'''
            cursor.execute(sql, (str(data['n']), data['cid']))
        self.conn.commit()

    # 检查saved_data表中是否已经存在n值
    def check_saved_data(self, n):
        sql = '''SELECT * FROM saved_data WHERE n = ?'''
        cursor = self.conn.cursor()
        cursor.execute(sql, (n,))
        rows = cursor.fetchall()
        return len(rows) > 0

    # 关闭数据库连接
    def close_connection(self):
        if self.conn is not None:
            self.conn.close()

class Fake115Client(object):

    def __init__(self,  cookie):
        self.cookie = cookie
        self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
        self.content_type = 'application/x-www-form-urlencoded'
        self.header = {"User-Agent":  self.ua,
                       "Content-Type":  self.content_type,  "Cookie": self.cookie}
        self.db = SharedLinksDB('shared_links.db')
        self.target_dir_cid = TARGETDIRCID
        self.get_userid()


    # 获取UID
    def get_userid(self):
        try:
            self.user_id = ''
            url = "https://my.115.com/?ct=ajax&ac=get_user_aq" ############
            p = requests.get(url, headers=self.header)
            if p:
                rootobject = p.json()
                if not rootobject.get("state"):
                    self.err = "[x] 获取 UID 错误：{}".format(rootobject.get("error_msg"))
                    return False
                self.user_id = rootobject.get("data").get("uid")
                return True
        except Exception as result:
            print("[x] 异常错误：{}".format(result))
        return False

    def request_datalist(self,share_code,receive_code):
        url = f"https://webapi.115.com/share/snap?share_code={share_code}&offset=0&limit=20&receive_code={receive_code}&cid="
        data_list = []
        share_info = {}
        try:
            response = requests.get(url, headers=self.header)
            response_json = json.loads(response.content.decode())
            share_info = response_json['data'].get('shareinfo')
            if response_json['state'] == False:
                print('error:',response_json['error'])
                return share_info,[]
            count = response_json['data']['count']
            data_list.extend(response_json['data']['list'])
            while len(data_list) < count:
                offset = len(data_list)
                response = requests.get(f"{url}&offset={offset}")
                response_json = json.loads(response.content.decode())
                data_list.extend(response_json['data']['list'])
        except:
            data_list = []
        return share_info,data_list

    def post_save(self, share_code, receive_code, file_ids,pid=''):
        print('[√]正在转存 %s:%s 中的 %d 项' % (share_code,receive_code, len(file_ids)))
        # 将 file_ids 用逗号拼接为一个字符串
        file_id_str = ','.join(file_ids)
        # 构造 POST 请求的 payload
        if pid == '':
            payload = {
                'user_id': self.user_id,
                'share_code': share_code,
                'receive_code': receive_code,
                'file_id': file_id_str
            }
        else:
            payload = {
                'user_id': self.user_id,
                'share_code': share_code,
                'receive_code': receive_code,
                'file_id': file_id_str,
                'cid': pid
            }
        # 发送 POST 请求
        try:
            response = requests.post('https://webapi.115.com/share/receive', data=payload, headers=self.header)
        except:
            sleep(5)
            response = requests.post('https://webapi.115.com/share/receive', data=payload, headers=self.header)
        # 解析响应的 JSON 数据
        result = response.json()
        # 判断转存是否成功
        if result['state']:
            print('[√]转存 %s:%s 成功' % (share_code,receive_code))
            return True
        else:
            print('[x]转存 %s:%s 失败，原因：%s' % (share_code,receive_code,result['error']))
            return False
        
    def create_dir(self,cname):
        '''
        pid:父目录id
        cname:目录名
        '''
        if not cname:
            return self.target_dir_cid
        data = {'pid': self.target_dir_cid,'cname':cname}
        try:
            response=requests.post('http://web.api.115.com/files/add',data=data,headers=self.header)
            data=response.json()
            if data['state']:
                return data['cid']
            else:
                print('[x]'+'新建文件夹失败,错误信息:'+data['error'])
                return self.target_dir_cid
        except:
                print('[x]'+'新建文件夹失败')
                return self.target_dir_cid


    def save_by_sr(self,share_code, receive_code):
        # 检查数据库中是否存在share_code, receive_code
        if self.db.check_shared_link(share_code, receive_code):
            print('[x]已转存过 %s:%s ' % (share_code,receive_code))
            return
        # 获取data_list
        share_info,data_list = self.request_datalist(share_code, receive_code)
        # 总数0就存share_code, receive_code到数据库 非0发送转存请求
        if len(data_list) == 0:
            self.db.insert_shared_link(share_code, receive_code,share_info,0)
            return
        else:
            self.db.insert_shared_link(share_code, receive_code,share_info,1)
            file_ids = []
            for data in data_list:
                n = data['n']
                cid = data['cid']
                fid = data.get('fid')
                if fid:
                    cid = fid
                # 检查数据库中是否存在n值
                if self.db.check_saved_data(n):
                    print('[x]转存 %s:%s 中的 %s 已存在' % (share_code,receive_code, n))
                    continue
                file_ids.append(cid)
            # 发送转存请求
            if len(data_list) == 1:
                pid = ''
            else:
                pid = self.create_dir(share_info['share_title'])
            if self.post_save(share_code, receive_code, file_ids,pid):
                self.db.insert_saved_data(data_list)

    
    def save_link(self,link):
        match = re.search(r's/(\w+)\?password=(\w+)', link)
        if match:
            share_code=match.group(1)
            receive_code=match.group(2)
            self.save_by_sr(share_code,receive_code)

    def save_link_from_file(self,filepath):
        with open(filepath, 'r',encoding='utf-8') as f:
            links = f.readlines()
        share_codes = []
        receive_codes = []
        for link in links:
            match = re.search(r's/(\w+)\?password=(\w+)', link)
            if match:
                share_codes.append(match.group(1))
                receive_codes.append(match.group(2))
        for share_code, receive_code in zip(share_codes, receive_codes):
            self.save_by_sr(share_code, receive_code)
    
    # 115分享链接批量转存

    def save_link_from_rawfile(self,filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if 'https://115.com/s/' in line:
                    if '?password=' in line:
                        start_index = line.find('https://115.com/s/')
                        end_index = line.find('?password=') + 14
                        link = line[start_index:end_index]
                        self.save_link(link)
                    else:
                        found = False
                        start_index = line.find('https://115.com/s/')
                        end_index = start_index + 29
                        link = line[start_index:end_index]
                        
                        for j in range(i, min(i + 6, len(lines))):
                            if '访问码：' in lines[j]:
                                password = re.search(r'访问码：([\d\w]{4})', lines[j]).group(1)
                                self.save_link(link + '?password=' + password)
                                found = True
                                break
                        if not found:
                            backward = False
                            for j in range(max(0, i - 5), i):
                                if '访问码：' in lines[j]:
                                    password = re.search(r'访问码：([\d\w]{4})', lines[j]).group(1)
                                    new_link = link + '?password=' + password
                                    if self.save_link(new_link):
                                        break
                                    else:
                                        backward = True
                            if backward:
                                for j in range(max(0, i - 5), i):
                                    if '访问码：' in lines[j]:
                                        password = re.search(r'访问码：([\d\w]{4})', lines[j]).group(1)
                                        new_link = link + '?password=' + password
                                        if self.save_link(new_link):
                                            break
    def save_link_from_rawfiles(self,folder_path):
        txt_files = []
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.txt'):
                txt_files.append(os.path.join(folder_path, file_name))
        for file_path in txt_files:
            self.save_link_from_rawfile(file_path)



if __name__ == '__main__':
    # 获取cookie.txt下的COOKIE
    if os.path.exists('./cookie.txt'):
        with open('./cookie.txt', 'r') as f:
            COOKIE = f.read()
    else:
        print('[x]请在当前目录下创建cookie.txt文件,并将115网页版的cookie粘贴进去')
    # 获取要转存到的文件夹的cid
    if os.path.exists('./cid.txt'):
        with open('./cid.txt', 'r') as f:
            TARGETDIRCID = f.read()
    else:
        print('[x]请在当前目录下创建cid.txt文件,并将要转存到的文件夹的cid粘贴进去')
    
    
    if os.path.exists('./links'):
        if COOKIE and TARGETDIRCID:
            cli = Fake115Client(COOKIE)
            cli.save_link_from_rawfiles('./links/')
        else:
            print('[x]请检查cookie.txt和cid.txt文件')
    else:
        print('[x]已在当前目录下创建links文件夹,请将115网页版的分享链接粘贴进去，注意用utf-8编码')
        os.makedirs('./links')
        
    
